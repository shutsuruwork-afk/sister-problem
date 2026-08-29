/* Minimal linear dimension of the width-W strip transfer operator.
 *
 * c_W(h) = number of self-avoiding (0,0)->(h-1,W-1) paths on an h x W vertex
 * grid.  Writing c_W(h) = <u, T^(h-2) v> for the row transfer T, the sequence
 * obeys a linear recurrence whose MINIMAL order r_W is the Hankel rank.  No
 * linear method whatsoever -- no quotient, no change of basis -- can carry the
 * whole family in fewer than r_W coordinates, so r_W is the hard floor for the
 * frontier state space.
 *
 * Everything is dense and rank-indexed:
 *   row-boundary vector : dim  = M_{W+1} - M_W  entries
 *   mid-row vector      : 2*dim entries
 * and the per-vertex transitions are precomputed once as index tables, so a
 * row transfer is pure gather/scatter with no ranking in the inner loop.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint32_t u32;
typedef uint64_t u64;

#define EMPTY 0
#define OPEN  1
#define CLOSE 2
#define MARK  3
#define NONE  0xffffffffu

static int W;                 /* strip width, in vertices per row */
static u64 MZ[64];            /* Motzkin numbers */
static u64 *BAL[64];          /* BAL[k][i*(k+2)+h] = completions of a length-k
                                 Motzkin word from position i at height h */
static u64 DIM;               /* M_{W+1} - M_W */
static u64 MOD;

static void build_tables(int maxlen) {
    MZ[0] = MZ[1] = 1;
    for (int n = 1; n + 1 < 64; n++)
        MZ[n + 1] = ((2 * n + 3) * MZ[n] + 3ULL * n * MZ[n - 1]) / (n + 3);
    for (int k = 0; k <= maxlen; k++) {
        BAL[k] = calloc((size_t)(k + 1) * (k + 2), sizeof(u64));
        BAL[k][(size_t)k * (k + 2) + 0] = 1;
        for (int i = k - 1; i >= 0; i--)
            for (int h = 0; h <= k; h++) {
                u64 v = BAL[k][(size_t)(i + 1) * (k + 2) + h]
                      + BAL[k][(size_t)(i + 1) * (k + 2) + h + 1];
                if (h) v += BAL[k][(size_t)(i + 1) * (k + 2) + h - 1];
                BAL[k][(size_t)i * (k + 2) + h] = v;
            }
    }
}

static u64 rankM(const unsigned char *w, int k) {
    u64 r = 0; int h = 0;
    for (int i = 0; i < k; i++) {
        const u64 *row = BAL[k] + (size_t)(i + 1) * (k + 2);
        if (w[i] == OPEN)       { r += row[h]; h++; }
        else if (w[i] == CLOSE) { r += row[h] + row[h + 1]; h--; }
    }
    return r;
}

static void unrankM(int k, u64 r, unsigned char *out) {
    int h = 0;
    for (int i = 0; i < k; i++) {
        const u64 *row = BAL[k] + (size_t)(i + 1) * (k + 2);
        if (r < row[h]) out[i] = EMPTY;
        else {
            r -= row[h];
            if (r < row[h + 1]) { out[i] = OPEN; h++; }
            else { r -= row[h + 1]; out[i] = CLOSE; h--; }
        }
    }
}

/* valid word: length L, exactly one MARK, balanced, no arc straddling the MARK */
static u64 rank_valid(const unsigned char *w, int L) {
    int m = L - 1, a = 0;
    while (w[a] != MARK) a++;
    int b = m - a;
    u64 off = 0;
    for (int x = 0; x < a; x++) off += MZ[x] * MZ[m - x];
    return off + rankM(w, a) * MZ[b] + rankM(w + a + 1, b);
}

static void unrank_valid(int L, u64 r, unsigned char *w) {
    int m = L - 1;
    for (int a = 0; a <= m; a++) {
        u64 blk = MZ[a] * MZ[m - a];
        if (r < blk) {
            int b = m - a;
            unrankM(a, r / MZ[b], w);
            w[a] = MARK;
            unrankM(b, r % MZ[b], w + a + 1);
            return;
        }
        r -= blk;
    }
    fprintf(stderr, "unrank_valid out of range\n"); exit(1);
}

static int partner(const unsigned char *w, int k, int len) {
    int d = 0;
    if (w[k] == OPEN) {
        for (int t = k + 1; t < len; t++) {
            if (w[t] == OPEN) d++;
            else if (w[t] == CLOSE) { if (!d) return t; d--; }
        }
    } else {
        for (int t = k - 1; t >= 0; t--) {
            if (w[t] == CLOSE) d++;
            else if (w[t] == OPEN) { if (!d) return t; d--; }
        }
    }
    fprintf(stderr, "unbalanced\n"); exit(1);
}

/* mid-row profile (length W+1) after vertex j  <->  dense index in [0,2*DIM) */
static u64 contract(const unsigned char *w, int j) {
    unsigned char u[64];
    int L = w[j], U = w[j + 1], c, b;
    int has_mark = 0;
    for (int t = 0; t <= W; t++) if (w[t] == MARK) { has_mark = 1; break; }
    if (!has_mark) return 2 * DIM;                 /* reserved accept slot */
    if (L == EMPTY && U == EMPTY)      { c = EMPTY; b = 0; }
    else if (U == EMPTY)               { c = L;     b = 0; }
    else if (L == EMPTY)               { c = U;     b = 1; }
    else                               { c = EMPTY; b = 1; }   /* matched arc */
    memcpy(u, w, j);
    u[j] = (unsigned char)c;
    memcpy(u + j + 1, w + j + 2, W - j - 1);
    return 2 * rank_valid(u, W) + b;
}

static void expand(u64 idx, int j, unsigned char *w) {
    unsigned char u[64];
    unrank_valid(W, idx >> 1, u);
    int b = (int)(idx & 1), c = u[j];
    memcpy(w, u, j);
    if (c == EMPTY) { w[j] = b ? OPEN : EMPTY; w[j + 1] = b ? CLOSE : EMPTY; }
    else            { w[j] = b ? EMPTY : c;    w[j + 1] = b ? c : EMPTY; }
    memcpy(w + j + 2, u + j + 1, W - j - 1);
}

/* successors of the profile w at vertex j; writes at most 2 profiles */
static int step_vertex(const unsigned char *w, int j, int is_start, int is_end,
                       int can_down, unsigned char out[2][64]) {
    int len = W + 1, L = w[j], U = w[j + 1], k = 0;
    unsigned char base[64];
    memcpy(base, w, len);
    base[j] = base[j + 1] = EMPTY;
    int can_right = (j < W - 1);

    if (is_start) {
        if (can_down) { memcpy(out[k], base, len); out[k][j] = MARK; k++; }
        if (can_right) { memcpy(out[k], base, len); out[k][j + 1] = MARK; k++; }
    } else if (is_end) {
        if (((L == MARK) != (U == MARK)) && (L == EMPTY || U == EMPTY)) {
            memcpy(out[k], base, len); k++;
        }
    } else if (L == EMPTY && U == EMPTY) {
        memcpy(out[k], base, len); k++;
        if (can_down && can_right) {
            memcpy(out[k], base, len);
            out[k][j] = OPEN; out[k][j + 1] = CLOSE; k++;
        }
    } else if (U == EMPTY) {
        if (can_down) { memcpy(out[k], base, len); out[k][j] = (unsigned char)L; k++; }
        if (can_right) { memcpy(out[k], base, len); out[k][j + 1] = (unsigned char)L; k++; }
    } else if (L == EMPTY) {
        if (can_down) { memcpy(out[k], base, len); out[k][j] = (unsigned char)U; k++; }
        if (can_right) { memcpy(out[k], base, len); out[k][j + 1] = (unsigned char)U; k++; }
    } else if (L == OPEN && U == CLOSE) {
        /* closes a cycle */
    } else if (L == MARK) {
        int q = partner(w, j + 1, len);
        memcpy(out[k], base, len); out[k][q] = MARK; k++;
    } else if (U == MARK) {
        int q = partner(w, j, len);
        memcpy(out[k], base, len); out[k][q] = MARK; k++;
    } else {
        int a = partner(w, j, len), b2 = partner(w, j + 1, len);
        int lo = a < b2 ? a : b2, hi = a < b2 ? b2 : a;
        memcpy(out[k], base, len); out[k][lo] = OPEN; out[k][hi] = CLOSE; k++;
    }
    return k;
}

/* ---- precomputed transition tables for one row ----------------------------
 * tab[j] maps the layer index before vertex j to at most two indices after it.
 * j = 0 reads a row-boundary index (size DIM); j > 0 reads a mid-row index
 * (size 2*DIM).  Row kind: 0 = generic, 1 = first row (holds the start),
 * 2 = last row (holds the terminal).                                        */
typedef struct { u32 *to; int nin; } Tab;

static Tab *build_row(int kind) {
    Tab *tab = malloc(sizeof(Tab) * W);
    unsigned char w[64], u[64], outs[2][64];
    for (int j = 0; j < W; j++) {
        int nin = (j == 0) ? (int)DIM : (int)(2 * DIM + 1);
        tab[j].nin = nin;
        tab[j].to = malloc(sizeof(u32) * 2 * nin);
        for (int i = 0; i < nin; i++) {
            if (j == 0) { unrank_valid(W, (u64)i, u); w[0] = EMPTY; memcpy(w + 1, u, W); }
            else if ((u64)i == 2 * DIM) {          /* accept: no successors */
                tab[j].to[2 * i] = tab[j].to[2 * i + 1] = NONE; continue;
            } else expand((u64)i, j - 1, w);
            int is_start = (kind == 1 && j == 0);
            int is_end   = (kind == 2 && j == W - 1);
            int k = step_vertex(w, j, is_start, is_end, kind != 2, outs);
            for (int t = 0; t < 2; t++)
                tab[j].to[2 * i + t] = (t < k) ? (u32)contract(outs[t], j) : NONE;
        }
    }
    return tab;
}

static void apply_row(const Tab *tab, const u64 *in, u64 *out, u64 *scratch) {
    u64 *a = scratch, *b = scratch + (2 * DIM + 1);
    /* j = 0: boundary -> mid-row */
    memset(a, 0, sizeof(u64) * (2 * DIM + 1));
    for (u64 i = 0; i < DIM; i++) {
        u64 v = in[i]; if (!v) continue;
        for (int t = 0; t < 2; t++) {
            u32 o = tab[0].to[2 * i + t];
            if (o != NONE) { a[o] += v; if (a[o] >= MOD) a[o] -= MOD; }
        }
    }
    for (int j = 1; j < W; j++) {
        memset(b, 0, sizeof(u64) * (2 * DIM + 1));
        const u32 *to = tab[j].to;
        for (u64 i = 0; i <= 2 * DIM; i++) {
            u64 v = a[i]; if (!v) continue;
            u32 o0 = to[2 * i], o1 = to[2 * i + 1];
            if (o0 != NONE) { b[o0] += v; if (b[o0] >= MOD) b[o0] -= MOD; }
            if (o1 != NONE) { b[o1] += v; if (b[o1] >= MOD) b[o1] -= MOD; }
        }
        u64 *t = a; a = b; b = t;
    }
    /* end of row: even indices carry the next boundary word */
    for (u64 i = 0; i < DIM; i++) out[i] = a[2 * i];
}

/* transpose of the last row applied to the accepting functional */
static void build_covector(const Tab *tab, u64 *u_out, u64 *scratch) {
    u64 *a = scratch, *b = scratch + (2 * DIM + 1);
    memset(a, 0, sizeof(u64) * (2 * DIM + 1));
    unsigned char acc[64];
    for (int i = 0; i < W; i++) acc[i] = EMPTY;
    /* after the terminal the profile is empty, which carries no MARK, so the
     * accepting mid-row coordinate is recorded directly by step_vertex/contract
     * during the forward build; here we mark every index whose successor list
     * is the accept.  Simpler: run the transpose from the accept indicator. */
    (void)acc;
    /* accept = the unique index produced at j = W-1 by the terminal vertex */
    memset(b, 0, sizeof(u64) * (2 * DIM + 1));
    b[2 * DIM] = 1;                                /* the accept coordinate */
    for (int j = W - 1; j >= 1; j--) {
        memset(a, 0, sizeof(u64) * (2 * DIM + 1));
        const u32 *to = tab[j].to;
        for (u64 i = 0; i <= 2 * DIM; i++) {
            u64 s = 0;
            u32 o0 = to[2 * i], o1 = to[2 * i + 1];
            if (o0 != NONE) s += b[o0];
            if (o1 != NONE) s += b[o1];
            a[i] = s % MOD;
        }
        u64 *t = a; a = b; b = t;
    }
    for (u64 i = 0; i < DIM; i++) {
        u64 s = 0;
        u32 o0 = tab[0].to[2 * i], o1 = tab[0].to[2 * i + 1];
        if (o0 != NONE) s += b[o0];
        if (o1 != NONE) s += b[o1];
        u_out[i] = s % MOD;
    }
}

static u64 pw(u64 a, u64 e, u64 m) {
    u64 r = 1; a %= m;
    while (e) { if (e & 1) r = (unsigned __int128)r * a % m; a = (unsigned __int128)a * a % m; e >>= 1; }
    return r;
}

static int berlekamp_massey(const u64 *s, int n, u64 p) {
    u64 *C = calloc(n + 2, sizeof(u64)), *B = calloc(n + 2, sizeof(u64)), *T = calloc(n + 2, sizeof(u64));
    C[0] = B[0] = 1;
    int L = 0, m = 1, lc = 1, lb = 1;
    u64 b = 1;
    for (int i = 0; i < n; i++) {
        u64 d = s[i];
        for (int j = 1; j <= L; j++) d = (d + (unsigned __int128)C[j] * s[i - j]) % p;
        if (d == 0) { m++; continue; }
        u64 coef = (unsigned __int128)d * pw(b, p - 2, p) % p;
        memcpy(T, C, sizeof(u64) * (lc + 1)); int lt = lc;
        if (lb + m > lc) { memset(C + lc + 1, 0, sizeof(u64) * (lb + m - lc)); lc = lb + m; }
        for (int j = 0; j <= lb; j++)
            C[j + m] = (C[j + m] + p - (unsigned __int128)coef * B[j] % p) % p;
        if (2 * L <= i) { L = i + 1 - L; memcpy(B, T, sizeof(u64) * (lt + 1)); lb = lt; b = d; m = 1; }
        else m++;
    }
    free(C); free(B); free(T);
    return L;
}

int main(int argc, char **argv) {
    W = argc > 1 ? atoi(argv[1]) : 6;
    MOD = argc > 2 ? strtoull(argv[2], NULL, 10) : 2305843009213693951ULL;
    build_tables(W + 2);
    DIM = MZ[W + 1] - MZ[W];

    Tab *gen = build_row(0), *first = build_row(1), *last = build_row(2);
    u64 *scratch = malloc(sizeof(u64) * 2 * (2 * DIM + 1));
    u64 *vec = calloc(DIM, sizeof(u64)), *tmp = calloc(DIM, sizeof(u64));
    u64 *cov = calloc(DIM, sizeof(u64));
    build_covector(last, cov, scratch);

    /* v = state after row 0 (which contains the start vertex) */
    u64 *seed = calloc(DIM, sizeof(u64));
    {   /* the empty profile is not a valid word, so run row 0 by hand */
        u64 *a = scratch, *b = scratch + (2 * DIM + 1);
        memset(a, 0, sizeof(u64) * (2 * DIM + 1));
        unsigned char w[64], outs[2][64];
        for (int i = 0; i <= W; i++) w[i] = EMPTY;
        int k = step_vertex(w, 0, 1, 0, 1, outs);
        for (int t = 0; t < k; t++) a[contract(outs[t], 0)] = 1;
        for (int j = 1; j < W; j++) {
            memset(b, 0, sizeof(u64) * (2 * DIM + 1));
            for (u64 i = 0; i <= 2 * DIM; i++) {
                u64 v = a[i]; if (!v) continue;
                for (int t = 0; t < 2; t++) {
                    u32 o = first[j].to[2 * i + t];
                    if (o != NONE) { b[o] += v; if (b[o] >= MOD) b[o] -= MOD; }
                }
            }
            u64 *t = a; a = b; b = t;
        }
        for (u64 i = 0; i < DIM; i++) seed[i] = a[2 * i];
    }
    memcpy(vec, seed, sizeof(u64) * DIM);

    int need = (int)(2 * DIM + 8);
    u64 *seq = malloc(sizeof(u64) * need);
    u64 square = 0;
    for (int h = 2; h < need + 2; h++) {
        unsigned __int128 acc = 0;
        for (u64 i = 0; i < DIM; i++) acc += (unsigned __int128)cov[i] * vec[i] % MOD;
        seq[h - 2] = (u64)(acc % MOD);
        if (h == W) square = seq[h - 2];
        apply_row(gen, vec, tmp, scratch);
        memcpy(vec, tmp, sizeof(u64) * DIM);
    }
    int r = berlekamp_massey(seq, need, MOD);
    printf("W=%d dim=%llu rank=%d ratio=%.4f a(%d)=%llu\n",
           W, (unsigned long long)DIM, r, (double)r / (double)DIM, W - 1,
           (unsigned long long)square);
    return 0;
}
