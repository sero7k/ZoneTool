"""Add a horizontal 'sea haze' annulus just above the sea of an exported .h1map: a lit alpha-blended decal whose
alpha rises with distance, so the map's distance fog (applied to it) shows over a water shader that ignores fog.
usage: add_haze_ring.py <dir with h1map/lmuv/h1lmuv/vcol (edited in place)> <stem> cx cy z r0 r1 rmax"""
import sys, struct, numpy as np, os
sys.path.insert(0, '/home/claude/carrier_look'); from h1map import H1Map
d, stem = sys.argv[1:3]
cx, cy, z, r0, r1, rmax = map(float, sys.argv[3:9])
hp = os.path.join(d, stem + '.h1map'); lp = os.path.join(d, stem + '.lmuv'); hlp = os.path.join(d, stem + '.h1lmuv')
vp = [os.path.join(d, f) for f in os.listdir(d) if f.endswith('_vcol.bin')][0]
m = H1Map(hp)
lb = np.fromfile(lp, np.uint8); lmuv = np.frombuffer(lb[4:], np.float32).reshape(-1, 2)
hb = open(hlp, 'rb').read(); h1uv = np.frombuffer(hb[12:], np.float32).reshape(-1, 2)
vc = np.fromfile(vp, np.uint8).reshape(-1, 4)
none = np.where((lmuv[:, 0] < 0) & (lmuv[:, 0] > -1.5))[0]
cell0 = h1uv[none[0]] if len(none) else np.array([0.002, 0.94], np.float32)
MAT = 'wpc/sea_haze_ring_bo2layer'; mi = len(m.mats); m.mats.append([MAT, 2])
SEG = 128
radii = np.concatenate([np.linspace(r0, r1, 10), np.geomspace(r1 * 1.15, rmax, 8)])
def alpha(r):
    t = np.clip((r - r0) / (r1 - r0), 0, 1); return (t * t * (3 - 2 * t)) * 0.96
verts = bytearray(); cols = []; ang = np.linspace(0, 2 * np.pi, SEG + 1)[:-1]
for r in radii:
    for a in ang:
        x, y = cx + r * np.cos(a), cy + r * np.sin(a)
        verts += struct.pack('<3f3f4f2f4B', x, y, z, 0, 0, 1, 1, 0, 0, 1, x / 4096.0, y / 4096.0, 255, 255, 255, int(alpha(r) * 255))
        cols.append(int(alpha(r) * 255))
nv = len(radii) * SEG
idx = bytearray(); nt = 0
for i in range(len(radii) - 1):
    for j in range(SEG):
        a = i * SEG + j; b = i * SEG + (j + 1) % SEG; c = (i + 1) * SEG + j; e = (i + 1) * SEG + (j + 1) % SEG
        for t in ((a, c, b), (b, c, e)):        # winding as the map's up-facing floors (checked below)
            idx += struct.pack('<3H', *t); nt += 1
# match the map's winding convention: a deck triangle's geometric normal vs its vertex normal
V = np.frombuffer(m.b, np.uint8, m.nverts * 52, m.vert_off).reshape(-1, 52)
P = V[:, :12].copy().view('<f4').reshape(-1, 3); N = V[:, 12:24].copy().view('<f4').reshape(-1, 3)
I = np.frombuffer(m.b, '<u2', m.nidx, m.idx_off)
s = m.surfs[100]; t = (I[s[3]:s[3] + s[4] * 3].astype(np.int64) + s[1]).reshape(-1, 3)
g = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]]); sgn = np.sign(np.median((g * N[t].mean(1)).sum(1)))
p0 = np.array([cx + radii[0], cy, z]); p1 = np.array([cx + radii[1], cy, z]); p2 = np.array([cx + radii[0] * np.cos(ang[1]), cy + radii[0] * np.sin(ang[1]), z])
ours = np.sign(np.cross(p1 - p0, p2 - p0)[2])     # (a, c, b) with a=ring0/seg0, c=ring1/seg0, b=ring0/seg1
if ours != sgn:
    arr = np.frombuffer(bytes(idx), '<u2').reshape(-1, 3)[:, [0, 2, 1]].copy(); idx = bytearray(arr.tobytes())
print('winding: map', sgn, 'ring', ours, '-> flipped' if ours != sgn else '')
lo = [cx - rmax, cy - rmax, z]; hi = [cx + rmax, cy + rmax, z]
m.surfs.append([mi, m.nverts, nv, m.nidx, nt, *lo, *hi])
m.write(hp, bytes(verts), bytes(idx), nv, nt * 3)
n2 = m.nverts + nv
open(lp, 'wb').write(struct.pack('<I', n2) + lmuv.tobytes() + np.full((nv, 2), -1, np.float32).tobytes())
open(hlp, 'wb').write(b'H1LMUV01' + struct.pack('<I', n2) + h1uv.tobytes() + np.tile(cell0.astype(np.float32), (nv, 1)).tobytes())
nvc = np.full((nv, 4), 255, np.uint8); nvc[:, 3] = cols
np.concatenate([vc, nvc]).tofile(vp)
print(f'haze ring: {nv} vertices, {nt} triangles, radii {r0}..{r1}..{rmax}, cell0 {cell0}')
