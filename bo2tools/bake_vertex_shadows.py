"""Per-vertex sun shadow + ambient occlusion for a BO2 map exported as .h1map (H1 port).
Writes <out>: RGBA8 per vertex = the original vertex colour x shade (alpha kept).
usage: bake.py <map.h1map> <map.lmuv> <out.bin> [sunx suny sunz]"""
import sys, struct, numpy as np, time
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh
h1, lmuv, out = sys.argv[1:4]
SUN = np.array([float(x) for x in sys.argv[4:7]] if len(sys.argv) >= 7 else [0.40213463, 0.8244982, 0.39810872]); SUN /= np.linalg.norm(SUN)
b = open(h1, 'rb').read(); o = 8
def u():
    global o; v = struct.unpack_from('<I', b, o)[0]; o += 4; return v
def st():
    global o; n = u(); v = b[o:o+n]; o += n; return v
st(); o += 60
nm = u(); kinds = []
for i in range(nm): st(); kinds.append(u())
nv = u(); vo = o
V = np.frombuffer(b, np.uint8, nv * 52, o).reshape(nv, 52); o += nv * 52
P = V[:, 0:12].copy().view(np.float32).reshape(nv, 3)
N = V[:, 12:24].copy().view(np.float32).reshape(nv, 3)
C = V[:, 48:52].copy()
ni = u(); I = np.frombuffer(b, np.uint16, ni, o).astype(np.int64); o += ni * 2
ns = u(); S = np.frombuffer(b, np.uint32, ns * 11, o).reshape(ns, 11)
occ = []; used = np.zeros(nv, bool)
for s in S:
    mat, base, vc, first, tc = (int(x) for x in s[:5])
    if mat >= nm: continue
    k = kinds[mat]
    t = I[first:first + tc * 3].reshape(-1, 3) + base
    if k in (5, 6): continue
    used[base:base + vc] = True
    if k in (0, 1): occ.append(t)
T = np.concatenate(occ)
ext = np.abs(P[T].reshape(-1, 3)).max()
print(f"{nv} vertices, {len(T)} occluder triangles, extent {ext:.0f}", flush=True)
scene = rtcs.EmbreeScene()
TriangleMesh(scene, P[T].astype(np.float32))
Nn = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
idx = np.where(used)[0]
org = (P[idx] + Nn[idx] * 2.0).astype(np.float32)
t0 = time.time()
def hits(orig, dirs, far):
    res = scene.run(orig, dirs.astype(np.float32), query='DISTANCE')
    return res < far
vis = np.zeros(nv, np.float32)
B = 400000
for a in range(0, len(idx), B):
    sl = slice(a, a + B)
    d = np.repeat(SUN[None].astype(np.float32), len(org[sl]), 0)
    vis[idx[sl]] = ~hits(org[sl], d, 1e9)
print("sun rays", time.time() - t0, "lit fraction", vis[idx].mean(), flush=True)
# ambient occlusion: K cosine-weighted rays to 300 units
K = 6; rng = np.random.default_rng(1)
ao = np.zeros(nv, np.float32)
for a in range(0, len(idx), B):
    sl = slice(a, a + B); n = Nn[idx[sl]]; m = len(n)
    t1 = np.cross(n, np.where(np.abs(n[:, 2:3]) < 0.9, [0, 0, 1], [1, 0, 0])); t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), 1e-6)
    t2 = np.cross(n, t1)
    free = np.zeros(m, np.float32)
    for k in range(K):
        r1, r2 = rng.random(m), rng.random(m)
        rr = np.sqrt(r1)[:, None]; ph = 2 * np.pi * r2[:, None]
        d = t1 * (rr * np.cos(ph)) + t2 * (rr * np.sin(ph)) + n * np.sqrt(1 - r1)[:, None]
        free += ~hits(org[sl], d, 200.0)
    ao[idx[sl]] = free / K
print("ao rays", time.time() - t0, "mean ao", ao[idx].mean(), flush=True)
# sky visibility: K cosine-weighted rays around straight up, 4000 units (interiors see none: no sun darkening there)
sky = np.zeros(nv, np.float32)
up = np.array([0, 0, 1.0])
for a in range(0, len(idx), B):
    sl = slice(a, a + B); m = len(org[sl])
    free = np.zeros(m, np.float32)
    for k in range(K):
        r1, r2 = rng.random(m), rng.random(m)
        rr = np.sqrt(r1); ph = 2 * np.pi * r2
        d = np.stack([rr * np.cos(ph), rr * np.sin(ph), np.sqrt(1 - r1)], 1)
        free += ~hits(org[sl], d, 4000.0)
    sky[idx[sl]] = free / K
print("sky rays", time.time() - t0, "mean sky", sky[idx].mean(), flush=True)
ndl = np.clip(Nn @ SUN, 0, 1)
direct = vis * np.clip(ndl * 1.6, 0, 1)
outdoor = np.clip(sky * 3.0, 0, 1)                       # 1 once a third of the sky rays get out
sunterm = 1.0 - outdoor * (1.0 - (0.45 + 0.55 * direct))  # shadowed outdoor faces down to 0.45
shade = sunterm * (0.68 + 0.32 * ao)
shade = np.where(used, shade, 1.0)
outc = C.astype(np.float32)
outc[:, :3] *= shade[:, None]
np.clip(outc, 0, 255).astype(np.uint8).tofile(out)
np.save(out + '.stats.npy', np.stack([vis, ao, shade, sky], 1))
print("shade mean", shade[idx].mean(), "written", out)
