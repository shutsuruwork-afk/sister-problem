/* Optimised broken-profile frontier DP for A007764.
 *
 * Same state encoding as dp.c, but the hash tables keep an explicit list of
 * occupied slots, so every vertex step costs O(#states) rather than O(table
 * capacity).  Tables are allocated once and ping-ponged.
 *
 * Reports a(n) mod p and the number of reachable states in each DP layer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;
typedef uint32_t u32;

#define EMPTY 0u
#define OPEN  1u
#define CLOSE 2u
#define MARK  3u

static inline unsigned getsym(u64 s, int k) { return (unsigned)((s >> (2 * k)) & 3u); }
static inline u64 setsym(u64 s, int k, unsigned v) {
    return (s & ~(3ULL << (2 * k))) | ((u64)v << (2 * k));
}

/* Partner of slot k under bracket matching.  Branch-free-ish scans over the
 * packed word; W <= 32 so these are short. */
static inline int partner_open(u64 s, int k, int W) {
    int depth = 0;
    for (int t = k + 1; t < W; t++) {
        unsigned c = getsym(s, t);
        if (c == OPEN) depth++;
        else if (c == CLOSE) { if (!depth) return t; depth--; }
    }
    return -1;
}
static inline int partner_close(u64 s, int k) {
    int depth = 0;
    for (int t = k - 1; t >= 0; t--) {
        unsigned c = getsym(s, t);
        if (c == CLOSE) depth++;
        else if (c == OPEN) { if (!depth) return t; depth--; }
    }
    return -1;
}
static inline int partner(u64 s, int k, int W) {
    return getsym(s, k) == OPEN ? partner_open(s, k, W) : partner_close(s, k);
}

static const u64 EMPTY_KEY = ~0ULL;

typedef struct { u64 key, val; } Ent;

typedef struct {
    Ent *e;        /* capacity-sized, key == EMPTY_KEY when free */
    u32 *occ;      /* indices of the occupied slots, length size */
    size_t cap, mask, size;
} Table;

static void tab_alloc(Table *t, size_t cap) {
    t->cap = cap; t->mask = cap - 1; t->size = 0;
    t->e = malloc(cap * sizeof(Ent));
    t->occ = malloc((cap * 6 / 10 + 8) * sizeof(u32));
    if (!t->e || !t->occ) { fprintf(stderr, "OOM (cap=%zu)\n", cap); exit(1); }
    for (size_t i = 0; i < cap; i++) t->e[i].key = EMPTY_KEY;
}
static inline void tab_clear(Table *t) {
    for (size_t i = 0; i < t->size; i++) t->e[t->occ[i]].key = EMPTY_KEY;
    t->size = 0;
}

static inline u64 mix(u64 x) {
    x ^= x >> 33; x *= 0xff51afd7ed558ccdULL;
    x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL;
    x ^= x >> 33; return x;
}

static void tab_grow(Table *t) {
    Table nt; tab_alloc(&nt, t->cap * 2);
    for (size_t e = 0; e < t->size; e++) {
        Ent it = t->e[t->occ[e]];
        size_t i = mix(it.key) & nt.mask;
        while (nt.e[i].key != EMPTY_KEY) i = (i + 1) & nt.mask;
        nt.e[i] = it; nt.occ[nt.size++] = (u32)i;
    }
    free(t->e); free(t->occ);
    *t = nt;
}

static inline void tab_add(Table *t, u64 k, u64 v, u64 p) {
    size_t i = mix(k) & t->mask;
    for (;;) {
        u64 cur = t->e[i].key;
        if (cur == k) { u64 s = t->e[i].val + v; if (s >= p) s -= p; t->e[i].val = s; return; }
        if (cur == EMPTY_KEY) break;
        i = (i + 1) & t->mask;
    }
    t->e[i].key = k; t->e[i].val = v; t->occ[t->size++] = (u32)i;
    if ((t->size + 1) * 10 >= t->cap * 6) tab_grow(t);
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: dp2 n prime [init_cap_log2] [--layers]\n"); return 1; }
    int n = atoi(argv[1]);
    u64 p = strtoull(argv[2], NULL, 10);
    int caplog = argc > 3 ? atoi(argv[3]) : 16;
    int show_layers = (argc > 4);

    int C = n + 1, W = C + 1;
    if (W > 32) { fprintf(stderr, "n too large for a 64-bit state word\n"); return 1; }
    u64 fullmask = (W == 32) ? ~0ULL : ((1ULL << (2 * W)) - 1);

    size_t cap = (size_t)1 << caplog;
    Table A, B, *cur = &A, *nxt = &B;
    tab_alloc(&A, cap);
    tab_alloc(&B, cap);
    tab_add(cur, 0ULL, 1ULL, p);
    size_t peak = 0;

    for (int i = 0; i < C; i++) {
        for (int j = 0; j < C; j++) {
            int is_start = (i == 0 && j == 0);
            int is_end   = (i == C - 1 && j == C - 1);
            int can_down = (i < C - 1), can_right = (j < C - 1);
            tab_clear(nxt);
            size_t m = cur->size;
            for (size_t e = 0; e < m; e++) {
                size_t idx = cur->occ[e];
                u64 st = cur->e[idx].key, v = cur->e[idx].val;
                unsigned L = getsym(st, j), U = getsym(st, j + 1);
                u64 base = st & ~(15ULL << (2 * j));

                if (is_start) {
                    if (can_down)  tab_add(nxt, base | ((u64)MARK << (2 * j)), v, p);
                    if (can_right) tab_add(nxt, base | ((u64)MARK << (2 * j + 2)), v, p);
                } else if (is_end) {
                    if ((L == MARK && U == EMPTY) || (U == MARK && L == EMPTY))
                        tab_add(nxt, base, v, p);
                } else if (L == EMPTY && U == EMPTY) {
                    tab_add(nxt, base, v, p);
                    if (can_down && can_right)
                        tab_add(nxt, base | ((u64)OPEN << (2 * j)) | ((u64)CLOSE << (2 * j + 2)), v, p);
                } else if (U == EMPTY) {
                    if (can_down)  tab_add(nxt, base | ((u64)L << (2 * j)), v, p);
                    if (can_right) tab_add(nxt, base | ((u64)L << (2 * j + 2)), v, p);
                } else if (L == EMPTY) {
                    if (can_down)  tab_add(nxt, base | ((u64)U << (2 * j)), v, p);
                    if (can_right) tab_add(nxt, base | ((u64)U << (2 * j + 2)), v, p);
                } else if (L == OPEN && U == CLOSE) {
                    /* joining these two ends would close a cycle: discard */
                } else if (L == MARK) {
                    int q = partner(st, j + 1, W);
                    tab_add(nxt, setsym(base, q, MARK), v, p);
                } else if (U == MARK) {
                    int a = partner(st, j, W);
                    tab_add(nxt, setsym(base, a, MARK), v, p);
                } else {
                    int a = partner(st, j, W), b = partner(st, j + 1, W);
                    int lo = a < b ? a : b, hi = a < b ? b : a;
                    tab_add(nxt, setsym(setsym(base, lo, OPEN), hi, CLOSE), v, p);
                }
            }
            Table *t = cur; cur = nxt; nxt = t;
            if (cur->size > peak) peak = cur->size;
            if (show_layers) printf("layer %d %d %zu\n", i, j, cur->size);
        }
        tab_clear(nxt);
        size_t m = cur->size;
        for (size_t e = 0; e < m; e++) {
            size_t idx = cur->occ[e];
            u64 st = cur->e[idx].key;
            if (getsym(st, C) != EMPTY) continue;
            tab_add(nxt, (st << 2) & fullmask, cur->e[idx].val, p);
        }
        { Table *t = cur; cur = nxt; nxt = t; }
    }

    u64 ans = 0;
    for (size_t e = 0; e < cur->size; e++)
        if (cur->e[cur->occ[e]].key == 0ULL) { ans = cur->e[cur->occ[e]].val; break; }
    printf("n=%d p=%llu a=%llu peak=%zu\n", n, (unsigned long long)p,
           (unsigned long long)ans, peak);
    return 0;
}
