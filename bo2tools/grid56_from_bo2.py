# Black Ops II light grid (SH, from codlegacyclient t6_grid_dump: grid_coeffs.bin 27 x u16 per set = 9 SH coeffs x RGB,
# value (v - 32768) / 32768; grid_entries.bin u16 pairs, the first the set index) -> <stem>.grid56: the light in H1's 56
# light-grid directions (4x4x4 lattice shell, x fastest), averaged over the brighter 40% of entries (outdoors),
# scaled per channel so the mean matches the flat <stem>.grid colour. usage: grid56_from_bo2.py <dump dir> <out> r g b
import numpy as np, sys
d = sys.argv[1]; tgt = np.array([float(x) for x in sys.argv[3:6]])
c = (np.fromfile(d + '/grid_coeffs.bin', '<u2').reshape(-1, 9, 3).astype(np.float32) - 32768) / 32768
e = np.fromfile(d + '/grid_entries.bin', '<u2').reshape(-1, 2)
sets = c[e[:, 0]]; dc = sets[:, 0].mean(1)
sh = sets[dc > np.percentile(dc, 60)].mean(0)
dirs = []
for k in range(4):
    for j in range(4):
        for i in range(4):
            if 1 <= i <= 2 and 1 <= j <= 2 and 1 <= k <= 2: continue
            v = np.array([i, j, k]) * 2 / 3 - 1; dirs.append(v / np.linalg.norm(v))
x, y, z = np.array(dirs).T
B = np.stack([np.ones_like(x), x, y, z, z * x, z * y, y * x, 3 * z * z - 1, x * x - y * y], 1)
L = np.maximum(B @ sh, 0.02)
np.savetxt(sys.argv[2], L / L.mean(0) * tgt, fmt='%.4f')
