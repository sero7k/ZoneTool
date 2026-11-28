"""Add a macro grime decal over a BO2 map's hull surfaces (world-projected UVs) to an exported .h1map, and extend
the per-vertex side files (BO2 lmuv, H1 h1lmuv, vertex colour bake) to match.
usage: add_grime.py <in.h1map> <in.lmuv> <in.h1lmuv> <in vcol.bin> <out dir> <mat substrings,comma> [top_z] [height] [tile]"""
import sys, struct, numpy as np, os
sys.path.insert(0, '/home/claude/carrier_look'); from h1map import H1Map
hp, lp, hlp, vp, out = sys.argv[1:6]
subs = sys.argv[6].split(',')
TOP = float(sys.argv[7]) if len(sys.argv) > 7 else 540.0
HT = float(sys.argv[8]) if len(sys.argv) > 8 else 1400.0
TILE = float(sys.argv[9]) if len(sys.argv) > 9 else 2048.0
MAT = 'wpc/hull_grime_macro_bo2layer'
m = H1Map(hp)
V = np.frombuffer(m.b, np.uint8, m.nverts * 52, m.vert_off).reshape(-1, 52)
I = np.frombuffer(m.b, '<u2', m.nidx, m.idx_off)
P = V[:, :12].copy().view('<f4').reshape(-1, 3)
lb = np.fromfile(lp, np.uint8); lmuv = np.frombuffer(lb[4:], np.float32).reshape(-1, 2)
hb = open(hlp, 'rb').read(); assert hb[:8] == b'H1LMUV01'; h1uv = np.frombuffer(hb[12:], np.float32).reshape(-1, 2)
vc = np.fromfile(vp, np.uint8).reshape(-1, 4)
assert len(lmuv) == len(h1uv) == len(vc) == m.nverts
mi = len(m.mats); m.mats.append([MAT, 2])
nv_new = []; idx_new = bytearray(); src = []; new_surfs = []
vbase = m.nverts; ibase = m.nidx; tris_total = 0
for s in list(m.surfs):
    name = m.mats[s[0]][0]
    if not any(x in name for x in subs) or name == MAT: continue
    mat, vb, nvv, ib, nt = s[:5]
    t = (I[ib:ib + nt * 3].astype(np.int64) + vb).reshape(-1, 3)
    p = P[t]; g = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]); gl = np.linalg.norm(g, axis=1)
    ok = gl > 1e-3; n = np.zeros_like(g); n[ok] = g[ok] / gl[ok, None]
    keep = np.where(ok & (n[:, 2] < 0.6))[0]        # walls and undersides (bow flare, overhangs)
    for c0 in range(0, len(keep), 20000):
        ch = keep[c0:c0 + 20000]
        if len(ch) == 0: continue
        sv = len(src)
        for k in ch:
            nn = n[k]
            if nn[2] > -0.6:
                tan = np.array([-nn[1], nn[0], 0.0]); tan /= np.linalg.norm(tan) + 1e-9
                for j in range(3):
                    vi = t[k, j]; q = P[vi]
                    src.append((vi, float(q @ tan) / TILE, (TOP - float(q[2])) / HT))
            else:   # underside: planar xy, kept in the streak/blotch part of the texture
                for j in range(3):
                    vi = t[k, j]; q = P[vi]
                    src.append((vi, float(q[0]) / TILE, 0.25 + float(q[1]) / (TILE * 6)))
        lo = P[t[ch]].reshape(-1, 3).min(0); hi = P[t[ch]].reshape(-1, 3).max(0)
        cnt = len(ch)
        for j in range(cnt * 3): idx_new += struct.pack('<H', j)
        new_surfs.append([mi, vbase + sv, cnt * 3, ibase + tris_total * 3, cnt, *lo.tolist(), *hi.tolist()])
        tris_total += cnt
src_vi = np.array([x[0] for x in src]); uu = np.array([x[1] for x in src], np.float32); vv = np.array([x[2] for x in src], np.float32)
NV = V[src_vi].copy()
NV[:, 40:48] = np.stack([uu, vv], 1).astype('<f4').view(np.uint8).reshape(-1, 8)
NV[:, 48:52] = 255
m.surfs += new_surfs
os.makedirs(out, exist_ok=True)
stem = os.path.basename(hp)
m.write(os.path.join(out, stem), NV.tobytes(), bytes(idx_new), len(NV), tris_total * 3)
n2 = m.nverts + len(NV)
with open(os.path.join(out, os.path.basename(lp)), 'wb') as f:
    f.write(struct.pack('<I', n2)); f.write(lmuv.tobytes()); f.write(lmuv[src_vi].tobytes())
with open(os.path.join(out, os.path.basename(hlp)), 'wb') as f:
    f.write(b'H1LMUV01'); f.write(struct.pack('<I', n2)); f.write(h1uv.tobytes()); f.write(h1uv[src_vi].tobytes())
nvc = vc[src_vi].copy(); nvc[:, 3] = 255
np.concatenate([vc, nvc]).tofile(os.path.join(out, os.path.basename(vp)))
print(f"grime: {tris_total} triangles, {len(NV)} vertices on {len(new_surfs)} surfaces; vertices {m.nverts} -> {n2}")
