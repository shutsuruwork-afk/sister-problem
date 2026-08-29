/* Independent brute-force: DFS enumeration of self-avoiding corner-to-corner
 * paths on the (n+1)x(n+1) vertex grid.  O(a(n)) time, so only useful for
 * n <= 6, but it depends on none of the DP machinery and therefore serves as
 * a genuinely independent oracle. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int N;              /* vertices per side = n+1 */
static unsigned char vis[32][32];
static unsigned long long cnt;

static void dfs(int r, int c) {
    if (r == N - 1 && c == N - 1) { cnt++; return; }
    static const int dr[4] = {-1, 1, 0, 0}, dc[4] = {0, 0, -1, 1};
    for (int d = 0; d < 4; d++) {
        int nr = r + dr[d], nc = c + dc[d];
        if (nr < 0 || nc < 0 || nr >= N || nc >= N || vis[nr][nc]) continue;
        vis[nr][nc] = 1;
        dfs(nr, nc);
        vis[nr][nc] = 0;
    }
}

int main(int argc, char **argv) {
    int nmax = argc > 1 ? atoi(argv[1]) : 6;
    for (int n = 1; n <= nmax; n++) {
        N = n + 1;
        memset(vis, 0, sizeof vis);
        vis[0][0] = 1;
        cnt = 0;
        dfs(0, 0);
        printf("%d %llu\n", n, cnt);
        fflush(stdout);
    }
    return 0;
}
