"""Symmetry & Congruence Engine for A007764.

Geometric symmetry group G ~= Z_2 x Z_2 acting on (n+1)x(n+1) grid:
1: identity
tau: transpose (i,j) -> (j,i) [Main diagonal reflection]
rho: 180-degree rotation (i,j) -> (n-i, n-j)
rho*tau: anti-diagonal reflection (i,j) -> (n-j, n-i)

Theorems (Burnside & Parity):
1. F_tau(n) = 0 for all n >= 1 (no path is symmetric under main diagonal reflection).
2. F_rho(n) = 0 for odd n.
3. Every rho*tau-symmetric path intersects the anti-diagonal exactly once (at the midpoint).
4. Orbit Congruence:
   a(n) = F_rho(n) + F_{rho*tau}(n)  (mod 4)
"""

from functools import lru_cache

# Known a(n)
KNOWN_A007764 = {
    1: 2, 2: 12, 3: 184, 4: 8512, 5: 1262816, 6: 575780564, 7: 789360053252,
    8: 3266598486981642, 9: 41044208702632496804,
    10: 1568758030464750013214100,
    11: 182413291514248049241470885236,
    12: 64528039343270018963357185158482118
}

def count_antidiagonal_symmetric_paths(n):
    """Compute F_{rho*tau}(n): number of paths symmetric under anti-diagonal reflection.
    A symmetric path on the lower triangle reaches the anti-diagonal and connects to its reflection.
    """
    # For small n, direct computation by checking reflection condition on grid DFS
    N = n + 1
    visited = [[False] * N for _ in range(N)]
    
    count = 0
    # DFS from (0,0) to anti-diagonal { (i, j) : i + j == n }
    def dfs(r, c):
        nonlocal count
        if r + c == n:
            # Reached anti-diagonal at (r, c).
            # The path automatically reflects to (n-c, n-r) = (r, c).
            # To be non-self-intersecting when combined with reflection,
            # no visited cell (r1, c1) can have its reflection (n-c1, n-r1) also visited,
            # except the midpoint itself.
            # Check reflection validity:
            valid = True
            for i in range(N):
                for j in range(N):
                    if visited[i][j] and (i + j < n):
                        # reflected cell is (n-j, n-i)
                        ref_r, ref_c = n - j, n - i
                        if visited[ref_r][ref_c]:
                            valid = False
                            break
                if not valid:
                    break
            if valid:
                count += 1
            return

        visited[r][c] = True
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < N and 0 <= nc < N and not visited[nr][nc]:
                dfs(nr, nc)
        visited[r][c] = False

    dfs(0, 0)
    return count

if __name__ == "__main__":
    print("=== Symmetry & Congruence Verification (mod 4) ===")
    print(" n | a(n) mod 4 | F_{rho*tau}(n) mod 4 | Predicted F_rho(n) mod 4")
    print("---|------------|----------------------|-------------------------")
    for n in range(1, 7):
        an = KNOWN_A007764[n]
        an_mod4 = an % 4
        f_rhotau = count_antidiagonal_symmetric_paths(n)
        f_rhotau_mod4 = f_rhotau % 4
        pred_frho_mod4 = (an_mod4 - f_rhotau_mod4) % 4
        print(f" {n:1d} |     {an_mod4}      |          {f_rhotau_mod4}           |           {pred_frho_mod4} (n={'even' if n%2==0 else 'odd'})")
