/* The symmetry group of the problem and the paths it fixes.
 *
 * The grid together with the ordered pair of terminals {s,t} is preserved by
 *   1                       identity
 *   tau  (i,j) -> (j,i)     main-diagonal reflection   (fixes s and t)
 *   rho  (i,j) -> (n-i,n-j) 180-degree rotation        (swaps s and t)
 *   rho*tau (i,j) -> (n-j,n-i) anti-diagonal reflection (swaps s and t)
 * so G = Z2 x Z2 acts on the set of s-t paths.  This enumerates the fixed sets
 * by brute force so the structural claims can be checked directly.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int N, n;
static unsigned char vis[16][16];
static int pr[300], pc[300], plen;
static long long total, fix_tau, fix_rho, fix_rt;

static void record(void) {
    total++;
    int L = plen - 1, ok;
    ok = 1; for (int k = 0; k <= L; k++) if (pr[k] != pc[k]) { ok = 0; break; }
    if (ok) fix_tau++;
    ok = 1; for (int k = 0; k <= L; k++)
        if (n - pr[k] != pr[L - k] || n - pc[k] != pc[L - k]) { ok = 0; break; }
    if (ok) fix_rho++;
    ok = 1; for (int k = 0; k <= L; k++)
        if (n - pc[k] != pr[L - k] || n - pr[k] != pc[L - k]) { ok = 0; break; }
    if (ok) fix_rt++;
}

static void dfs(int r, int c) {
    pr[plen] = r; pc[plen] = c; plen++;
    if (r == N - 1 && c == N - 1) { record(); plen--; return; }
    static const int dr[4] = {-1, 1, 0, 0}, dc[4] = {0, 0, -1, 1};
    for (int d = 0; d < 4; d++) {
        int nr = r + dr[d], nc = c + dc[d];
        if (nr < 0 || nc < 0 || nr >= N || nc >= N || vis[nr][nc]) continue;
        vis[nr][nc] = 1; dfs(nr, nc); vis[nr][nc] = 0;
    }
    plen--;
}

int main(int argc, char **argv) {
    int hi = argc > 1 ? atoi(argv[1]) : 5;
    printf("  n        a(n)   fix(tau)   fix(rho)  fix(rho*tau)   orbits   a(n) mod 4   "
           "fix_rho+fix_rt mod 4\n");
    for (n = 1; n <= hi; n++) {
        N = n + 1;
        memset(vis, 0, sizeof vis);
        vis[0][0] = 1; plen = 0;
        total = fix_tau = fix_rho = fix_rt = 0;
        dfs(0, 0);
        long long orb4 = total + fix_tau + fix_rho + fix_rt;
        printf("%3d %11lld %10lld %10lld %13lld %8s %11lld %20lld\n",
               n, total, fix_tau, fix_rho, fix_rt,
               (orb4 % 4 == 0) ? "exact" : "BAD",
               total % 4, (fix_rho + fix_rt) % 4);
        printf("      orbits = %lld\n", orb4 / 4);
    }
    return 0;
}
