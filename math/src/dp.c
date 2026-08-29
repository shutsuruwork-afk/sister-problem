/* Broken-profile frontier DP for A007764, modular arithmetic, open-addressing
 * hash table.  Computes a(n) mod p and reports the number of reachable states
 * in every DP layer (the memory profile of the sweep).
 *
 * State encoding: 2 bits per profile slot, W = n + 2 slots, so W <= 32.
 *   0 = no plug, 1 = '(' , 2 = ')' , 3 = free end of the start fragment.
 * The 1/2 symbols form a balanced bracket word, so partners are recovered by
 * bracket matching and never stored.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;

#define EMPTY 0u
#define OPEN  1u
#define CLOSE 2u
#define MARK  3u

static inline unsigned getsym(u64 s, int k) { return (unsigned)((s >> (2 * k)) & 3u); }
static inline u64 setsym(u64 s, int k, unsigned v) {
    return (s & ~(3ULL << (2 * k))) | ((u64)v << (2 * k));
}

static int partner(u64 s, int k, int W) {
    unsigned sym = getsym(s, k);
    int depth = 0;
    if (sym == OPEN) {
        for (int t = k + 1; t < W; t++) {
            unsigned c = getsym(s, t);
            if (c == OPEN) depth++;
            else if (c == CLOSE) { if (depth == 0) return t; depth--; }
        }
    } else {
        for (int t = k - 1; t >= 0; t--) {
            unsigned c = getsym(s, t);
            if (c == CLOSE) depth++;
            else if (c == OPEN) { if (depth == 0) return t; depth--; }
        }
    }
    fprintf(stderr, "unbalanced state\n");
    exit(1);
}

/* ---- open addressing hash table: u64 key -> u64 value (mod p) ---- */
typedef struct { u64 *key; u64 *val; size_t cap, size; } Table;

static const u64 EMPTY_KEY = ~0ULL;

static void tab_init(Table *t, size_t cap) {
    t->cap = cap; t->size = 0;
    t->key = malloc(cap * sizeof(u64));
    t->val = malloc(cap * sizeof(u64));
    if (!t->key || !t->val) { fprintf(stderr, "OOM (cap=%zu)\n", cap); exit(1); }
    memset(t->key, 0xff, cap * sizeof(u64));
}
static void tab_free(Table *t) { free(t->key); free(t->val); t->key = t->val = NULL; }

static inline u64 mix(u64 x) {
    x ^= x >> 33; x *= 0xff51afd7ed558ccdULL;
    x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL;
    x ^= x >> 33; return x;
}

static void tab_grow(Table *t);

static inline void tab_add(Table *t, u64 k, u64 v, u64 p) {
    if ((t->size + 1) * 10 >= t->cap * 7) tab_grow(t);
    size_t m = t->cap - 1, i = mix(k) & m;
    while (t->key[i] != EMPTY_KEY) {
        if (t->key[i] == k) {
            u64 s = t->val[i] + v; if (s >= p) s -= p;
            t->val[i] = s; return;
        }
        i = (i + 1) & m;
    }
    t->key[i] = k; t->val[i] = v; t->size++;
}

static void tab_grow(Table *t) {
    Table nt; tab_init(&nt, t->cap * 2);
    for (size_t i = 0; i < t->cap; i++) {
        if (t->key[i] == EMPTY_KEY) continue;
        size_t m = nt.cap - 1, j = mix(t->key[i]) & m;
        while (nt.key[j] != EMPTY_KEY) j = (j + 1) & m;
        nt.key[j] = t->key[i]; nt.val[j] = t->val[i]; nt.size++;
    }
    free(t->key); free(t->val);
    *t = nt;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: dp n prime [--layers]\n"); return 1; }
    int n = atoi(argv[1]);
    u64 p = strtoull(argv[2], NULL, 10);
    int show_layers = (argc > 3);

    int C = n + 1;        /* vertices per row */
    int W = C + 1;        /* profile slots, indices 0..C */
    if (W > 32) { fprintf(stderr, "n too large for 64-bit state\n"); return 1; }
    u64 fullmask = (W == 32) ? ~0ULL : ((1ULL << (2 * W)) - 1);

    Table cur, nxt;
    tab_init(&cur, 1024);
    tab_add(&cur, 0ULL, 1ULL, p);
    size_t peak = 0;

    for (int i = 0; i < C; i++) {
        for (int j = 0; j < C; j++) {
            int is_start = (i == 0 && j == 0);
            int is_end   = (i == C - 1 && j == C - 1);
            int can_down = (i < C - 1);
            int can_right = (j < C - 1);
            tab_init(&nxt, cur.cap);

            for (size_t idx = 0; idx < cur.cap; idx++) {
                if (cur.key[idx] == EMPTY_KEY) continue;
                u64 st = cur.key[idx], v = cur.val[idx];
                unsigned L = getsym(st, j), U = getsym(st, j + 1);
                u64 base = setsym(setsym(st, j, EMPTY), j + 1, EMPTY);

                if (is_start) {
                    if (can_down)  tab_add(&nxt, setsym(base, j, MARK), v, p);
                    if (can_right) tab_add(&nxt, setsym(base, j + 1, MARK), v, p);
                    continue;
                }
                if (is_end) {
                    if ((L == MARK && U == EMPTY) || (U == MARK && L == EMPTY))
                        tab_add(&nxt, base, v, p);
                    continue;
                }
                if (L == EMPTY && U == EMPTY) {
                    tab_add(&nxt, base, v, p);                      /* unused */
                    if (can_down && can_right)                      /* new arc */
                        tab_add(&nxt, setsym(setsym(base, j, OPEN), j + 1, CLOSE), v, p);
                    continue;
                }
                if (U == EMPTY) {            /* comes from the left */
                    if (can_down)  tab_add(&nxt, setsym(base, j, L), v, p);
                    if (can_right) tab_add(&nxt, setsym(base, j + 1, L), v, p);
                    continue;
                }
                if (L == EMPTY) {            /* comes from above */
                    if (can_down)  tab_add(&nxt, setsym(base, j, U), v, p);
                    if (can_right) tab_add(&nxt, setsym(base, j + 1, U), v, p);
                    continue;
                }
                /* both plugs arrive: degree 2, the two fragments merge */
                if (L == OPEN && U == CLOSE) continue;   /* closes a cycle */
                if (L == MARK) {
                    int q = partner(st, j + 1, W);
                    tab_add(&nxt, setsym(base, q, MARK), v, p);
                } else if (U == MARK) {
                    int pp = partner(st, j, W);
                    tab_add(&nxt, setsym(base, pp, MARK), v, p);
                } else {
                    int a = partner(st, j, W), b = partner(st, j + 1, W);
                    int lo = a < b ? a : b, hi = a < b ? b : a;
                    tab_add(&nxt, setsym(setsym(base, lo, OPEN), hi, CLOSE), v, p);
                }
            }
            tab_free(&cur);
            cur = nxt;
            if (cur.size > peak) peak = cur.size;
            if (show_layers) printf("layer %d %d %zu\n", i, j, cur.size);
        }
        /* end of row: shift the profile right by one slot */
        tab_init(&nxt, cur.cap);
        for (size_t idx = 0; idx < cur.cap; idx++) {
            if (cur.key[idx] == EMPTY_KEY) continue;
            u64 st = cur.key[idx];
            if (getsym(st, C) != EMPTY) continue;
            tab_add(&nxt, (st << 2) & fullmask, cur.val[idx], p);
        }
        tab_free(&cur);
        cur = nxt;
    }

    u64 ans = 0;
    for (size_t idx = 0; idx < cur.cap; idx++)
        if (cur.key[idx] == 0ULL) { ans = cur.val[idx]; break; }
    printf("n=%d p=%llu a=%llu peak=%zu\n", n, (unsigned long long)p,
           (unsigned long long)ans, peak);
    tab_free(&cur);
    return 0;
}
