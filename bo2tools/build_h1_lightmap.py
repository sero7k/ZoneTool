"""Black Ops II Carrier's own lightmap as H1's lightmap pair, and the H1 lightmap coordinate of every vertex.

Inputs: the Rust exporter's <map>.h1map and <map>.lmuv (per vertex the BO2 lightmap coordinate, or -1 none, or
-(i+2) for static model i), the BO2 lightmap (lm0_s.raw, 512x3072 RGBA8: three 512x1024 pages, page 0 base light
and page 1 directional light as rgb / a, page 2 the light direction rgb * 2 - 1 with the sun's baked visibility in
alpha), props.tsv (per static model: sun visibility, primary light, baked vertex light mean, light grid colour), and
the H1 placeholder images' headers.

H1's pair: the secondary is R16G16B16A16_FLOAT 1024x4096, two 1024x2048 pages stacked (A over B, light = A + B * f,
f = 1 on a flat surface, alpha 0); the primary is BC4 2048x4096, the sun's visibility at twice a page's size.
The BO2 page goes into the top 1920 rows of a page; the 128 rows under it hold one 4x4 cell per static model (its
own light) and cell 0 for surfaces without a lightmap.

usage: build_h1_lightmap.py <h1map> <lmuv> <lm0_s.raw> <props.tsv> <primary.h1Image> <secondary.h1Image> <out dir>
"""
import struct, sys, os
import numpy as np
from scipy import ndimage

h1map, lmuv, lmraw, props_tsv, prim_in, sec_in, out = sys.argv[1:8]
GAIN = float(os.environ.get("LM_GAIN", "0.52"))     # BO2 light -> H1 indirect (H1 sun 7.0 against BO2's 13.5)
PW, PH = 1024, 2048        # an H1 secondary page
BO_ROWS = 1920             # rows of the page the BO2 page fills
CELL = 4

# ---- the map: vertices' normals, surfaces, indices ----
b = open(h1map, 'rb').read()
o = 8
def u():
    global o; v = struct.unpack_from('<I', b, o)[0]; o += 4; return v
def st():
    global o; n = u(); v = b[o:o+n]; o += n; return v
st(); o += 4 * 15
nm = u()
kinds = []
for i in range(nm):
    st(); kinds.append(u())
nv = u()
verts = np.frombuffer(b, np.uint8, nv * 52, o).reshape(nv, 52); o += nv * 52
normals = verts[:, 12:24].copy().view(np.float32).reshape(nv, 3)
ni = u(); idx = np.frombuffer(b, np.uint16, ni, o).astype(np.int64); o += ni * 2
ns = u(); surfs = np.frombuffer(b, np.uint32, ns * 11, o).reshape(ns, 11)

lb = np.fromfile(lmuv, np.uint8)
n = int(np.frombuffer(lb[:4], np.uint32)[0]); assert n == nv, (n, nv)
uv = np.frombuffer(lb[4:], np.float32).reshape(n, 2).astype(np.float64)

# ---- the BO2 lightmap ----
lm = np.fromfile(lmraw, np.uint8).reshape(3, 1024, 512, 4).astype(np.float32) / 255.0
amb = lm[0, :, :, :3] / (lm[0, :, :, 3:] + 1e-6)
dirl = lm[1, :, :, :3] / (lm[1, :, :, 3:] + 1e-6)
ldir = lm[2, :, :, :3] * 2.0 - 1.0
vis = lm[2, :, :, 3].copy()

# Each texel's surface normal: the lightmapped triangles rasterised at the BO2 page's size (512x1024).
BW, BH = 512, 1024
nrm = np.zeros((BH, BW, 3), np.float32)
wpos = np.zeros((BH, BW, 3), np.float32)
verts_p = verts[:, 0:12].copy().view(np.float32).reshape(nv, 3)
cov = np.zeros((BH, BW), bool)
tris = 0
for s in surfs:
    mat, base, vc, first, tc = (int(x) for x in s[:5])
    if mat >= len(kinds) or kinds[mat] == 6:
        continue
    t = idx[first:first + tc * 3].reshape(-1, 3) + base
    l = uv[t]                                   # (tc, 3, 2)
    ok = (l[:, :, 0] >= 0).all(1)
    for tri, q in zip(t[ok], l[ok]):
        p = q * [BW, BH] - 0.5
        x0, y0 = np.floor(p.min(0)).astype(int); x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, BW - 1), min(y1, BH - 1)
        if x1 < x0 or y1 < y0:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        a, bb, c = p
        d = (bb[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (bb[1] - a[1])
        if abs(d) < 1e-12:
            continue
        w1 = ((xs - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (ys - a[1])) / d
        w2 = ((bb[0] - a[0]) * (ys - a[1]) - (xs - a[0]) * (bb[1] - a[1])) / d
        w0 = 1 - w1 - w2
        e = -0.6 / max(abs(d) ** 0.5, 1e-3)     # a little outside the edges (conservative)
        m = (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not m.any():
            continue
        nn = normals[tri]
        v = w0[m, None] * nn[0] + w1[m, None] * nn[1] + w2[m, None] * nn[2]
        nrm[ys[m], xs[m]] = v
        pp = verts_p[tri]
        wpos[ys[m], xs[m]] = w0[m, None] * pp[0] + w1[m, None] * pp[1] + w2[m, None] * pp[2]
        cov[ys[m], xs[m]] = True
        tris += 1
ln = np.linalg.norm(nrm, axis=2, keepdims=True)
nrm = np.where(ln > 1e-6, nrm / np.maximum(ln, 1e-6), [0, 0, 1])
cosf = np.clip((ldir * nrm).sum(2), 0, 1)
cosf = np.where(cov, cosf, 0.5)
print(f"rasterised {tris} triangles, {cov.mean() * 100:.1f}% of the page covered")

# Black Ops II bakes the sun into these pages (a sunlit flight deck holds about sun x N.L); H1 adds its sun itself
# by the primary's visibility, so the sun's direct share comes out: what is left is the bounced and sky light.
SUN = np.array([13.505618, 11.856234, 7.2939463], np.float32)
TOWARD = np.array([0.40213463, 0.8244982, 0.39810872], np.float32)
# LM_SHADOWS=1: also shadow the sun by everything in the map, static models included (BO2 cast those at run time,
# so its baked visibility misses e.g. the jets' shadows on the deck): one Embree ray per texel toward the sun.
if os.environ.get("LM_SHADOWS", "0") == "1":
    from embreex import rtcore_scene as rtcs
    from embreex.mesh_construction import TriangleMesh
    occ = []
    for s_ in surfs:
        mat, base, vc, first, tc = (int(x) for x in s_[:5])
        if mat < len(kinds) and kinds[mat] in (0, 1):
            occ.append(idx[first:first + tc * 3].reshape(-1, 3) + base)
    scene = rtcs.EmbreeScene(); TriangleMesh(scene, verts_p[np.concatenate(occ)].astype(np.float32))
    nn_ = np.where(cov[:, :, None], nrm, 0)
    o_ = (wpos + nn_ * 3.0 + TOWARD * 2.0)[cov].astype(np.float32)
    d_ = np.repeat(TOWARD[None], len(o_), 0).astype(np.float32)
    lit_ = scene.run(o_, d_, query='DISTANCE') >= 1e9
    ours = np.ones((BH, BW), np.float32); ours[cov] = lit_.astype(np.float32)
    ours = ndimage.uniform_filter(ours, 2)
    print(f"our sun shadows: {(1 - ours[cov]).mean() * 100:.1f}% of covered texels shaded (BO2's baked: {(1 - vis[cov]).mean() * 100:.1f}%)")
    vis_bo2 = vis.copy()
    vis = np.minimum(vis, ours)
ndl = np.clip((nrm * TOWARD).sum(2), 0, 1)
direct = SUN * (vis * ndl)[:, :, None]
total = amb + dirl * cosf[:, :, None]
direct_bo2 = SUN * (vis_bo2 * ndl)[:, :, None] if 'vis_bo2' in globals() else direct
rest = np.maximum(total - direct_bo2, total * 0.15)
print("sunlit texels: total", np.median(total[cov & (vis > 0.9)], 0).round(2).tolist(), "sun direct", np.median(direct[cov & (vis > 0.9)], 0).round(2).tolist(), "rest", np.median(rest[cov & (vis > 0.9)], 0).round(2).tolist())
# the left-over sky light is strongly blue; keep only part of its tint so shaded walls read grey, not navy
SAT = float(os.environ.get("LM_SAT", "0.35"))
def desat(c):
    l = (c * np.array([0.30, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    return l + (c - l) * SAT
rest = desat(rest)
share = np.clip(amb / np.maximum(total, 1e-6), 0, 1)
# LM_KEEPSUN=1: keep Black Ops II's baked sun (with its shadows) in the lightmap instead of H1's unshadowed dynamic sun
# (then run the map with a small LOOK_SUN). LM_SUNK scales it, LM_SUNSAT keeps that much of its warm tint.
KEEPSUN = os.environ.get("LM_KEEPSUN", "0") == "1"
SUNK = float(os.environ.get("LM_SUNK", "1.0"))
SUNSAT = float(os.environ.get("LM_SUNSAT", "0.6"))
def sat_k(c, k):
    l = (c * np.array([0.30, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    return l + (c - l) * k
A = rest * share * GAIN
B = rest * (1 - share) * GAIN
if KEEPSUN:
    A = A + sat_k(direct, SUNSAT) * SUNK * GAIN
    print("keeping the baked sun: sunlit median A", np.median(A[cov & (vis > 0.9)], 0).round(3).tolist(), "shaded median A", np.median(A[cov & (vis < 0.1)], 0).round(3).tolist())
print("BO2 base light (covered) 10/50/90%:", np.percentile(amb[cov], [10, 50, 90], axis=0).round(3).tolist())
print("BO2 directional * cos (covered) 50%:", np.median((dirl * cosf[:, :, None])[cov], axis=0).round(3).tolist())
print("sun visibility (covered) mean:", float(vis[cov].mean()))

# Spread every chart's edge texels outward (a few texels) so bilinear reads past the charts find the chart's light.
def dilate(img, mask, steps=4):
    img = img.copy(); m = mask.copy()
    for _ in range(steps):
        ind = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
        grow = ndimage.binary_dilation(m) & ~m
        img[grow] = img[ind[0][grow], ind[1][grow]]
        m |= grow
    return img
A = dilate(A, cov); B = dilate(B, cov); vis_d = dilate(vis, cov)

def resize(img, w, h):
    sy, sx = h / img.shape[0], w / img.shape[1]
    if img.ndim == 3:
        return np.stack([ndimage.zoom(img[:, :, c], (sy, sx), order=1, mode='nearest', grid_mode=True) for c in range(img.shape[2])], 2)
    return ndimage.zoom(img, (sy, sx), order=1, mode='nearest', grid_mode=True)

pageA = np.zeros((PH, PW, 3), np.float32); pageB = np.zeros((PH, PW, 3), np.float32)
pageA[:BO_ROWS] = resize(A, PW, BO_ROWS); pageB[:BO_ROWS] = resize(B, PW, BO_ROWS)
# empty texels (no light, under 1.5% of the median: gutters and faces BO2 never baked, e.g. backs of walls) take the nearest baked texel,
# so a face mapped onto them is not drawn black (LM_NOFILL=1 turns this off)
if os.environ.get("LM_NOFILL", "0") != "1":
    tot = (pageA[:BO_ROWS] + pageB[:BO_ROWS]).sum(2)
    nzt = tot[tot > 1e-6]
    empty = tot <= (0.015 * np.median(nzt) if nzt.size else 1e-6)
    if empty.any() and (~empty).any():
        _, (iy, ix) = ndimage.distance_transform_edt(empty, return_indices=True)
        pageA[:BO_ROWS] = pageA[:BO_ROWS][iy, ix]; pageB[:BO_ROWS] = pageB[:BO_ROWS][iy, ix]
        print(f"filled {empty.sum()} empty lightmap texels of {empty.size}")
# LM_FLOOR=f: no baked texel darker than f x the median (BO2 lit dark corners with probes H1 lacks; pure-black
# lightmap texels render as solid black faces). The lift is neutral-cool sky light.
FLOOR = float(os.environ.get("LM_FLOOR", "0"))
if FLOOR > 0:
    tot = (pageA[:BO_ROWS] + pageB[:BO_ROWS]).sum(2)
    fl = FLOOR * np.median(tot[tot > 1e-6])
    low = tot < fl
    add = np.clip(fl - tot, 0, None)[..., None] * np.array([float(x) for x in os.environ.get('LM_FLOORCOL', '0.31 0.33 0.36').split()], np.float32)   # LM_FLOORCOL: the lift's colour (sums to ~1)
    pageA[:BO_ROWS] += np.where(low[..., None], add, 0)
    print(f"floor: {low.sum()} texels lifted to {fl:.3f} ({FLOOR} x median)")
prim = np.zeros((PH * 2, PW * 2), np.float32)
prim[:BO_ROWS * 2] = resize(vis_d, PW * 2, BO_ROWS * 2)

# ---- the cells: 0 for surfaces without a lightmap, i + 1 for static model i ----
props = np.loadtxt(props_tsv, ndmin=2)
nprops = len(props)
cols = PW // CELL
cells_needed = nprops + 1
assert cells_needed <= cols * ((PH - BO_ROWS) // CELL), cells_needed
cov_amb = amb[cov]; cov_dir = (dirl * cosf[:, :, None])[cov]
def put_cell(j, a, bl, sv):
    cx, cy = j % cols, j // cols
    x, y = cx * CELL, BO_ROWS + cy * CELL
    pageA[y:y + CELL, x:x + CELL] = a; pageB[y:y + CELL, x:x + CELL] = bl
    prim[2 * y:2 * (y + CELL), 2 * x:2 * (x + CELL)] = sv
    return ((x + CELL / 2) / PW, (y + CELL / 2) / PH)
cell_uv = np.zeros((cells_needed, 2))
cell_uv[0] = put_cell(0, np.median((rest * share)[cov], 0) * GAIN, np.median((rest * (1 - share))[cov], 0) * GAIN, 1.0)
for i, row in enumerate(props):
    sv = row[1] if int(row[2]) == 1 else 0.0
    light = row[3:6] if row[3] >= 0 else row[6:9]
    light = np.clip(light, 0, 16)
    light = np.maximum(light, float(os.environ.get('LM_CELLFLOOR', '0')))   # static models: no crushed-black backlit props
    if row[3] >= 0:
        # (baked vertex light holds the sun too: take out its share at an upward-facing N.L)
        if not KEEPSUN:
            light = np.maximum(light - SUN * sv * TOWARD[2], light * 0.15)
    # (its light half in each page: A + B on a flat surface)
    light = desat(light.astype(np.float32))
    cell_uv[i + 1] = put_cell(i + 1, light * 0.5 * GAIN, light * 0.5 * GAIN, sv)

# ---- every vertex's H1 coordinate ----
h1uv = np.zeros((nv, 2), np.float32)
lit = uv[:, 0] >= 0
h1uv[lit, 0] = uv[lit, 0]
h1uv[lit, 1] = uv[lit, 1] * (BO_ROWS / PH)
none = (uv[:, 0] < 0) & (uv[:, 0] > -1.5)
h1uv[none] = cell_uv[0]
pm = uv[:, 0] <= -1.5
pi = np.clip((-uv[pm, 0] - 2).round().astype(int), 0, nprops - 1)
h1uv[pm] = cell_uv[pi + 1]
print(f"vertices: {lit.sum()} lightmapped, {none.sum()} without, {pm.sum()} on {nprops} static models")

os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "mp_carrier.h1lmuv"), "wb") as f:
    f.write(b"H1LMUV01"); f.write(struct.pack("<I", nv)); f.write(h1uv.tobytes())

# ---- the images ----
def header_and_size(path):
    d = open(path, 'rb').read()
    l1 = struct.unpack_from('<I', d, 42)[0]
    return d[:len(d) - l1], l1
sh, sl = header_and_size(sec_in)
sec = np.zeros((PH * 2, PW, 4), np.float16)
sec[:PH, :, :3] = pageA; sec[PH:, :, :3] = pageB
assert sec.nbytes == sl, (sec.nbytes, sl)
open(os.path.join(out, "_lightmap0_secondary.h1Image"), "wb").write(sh + sec.tobytes())

def bc4(img):
    h, w = img.shape
    blk = img.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3).reshape(-1, 16)
    q = np.clip(np.round(blk * 255), 0, 255)
    lo = q.min(1); hi = q.max(1)
    same = hi == lo
    hi = np.where(same, np.minimum(lo + 1, 255), hi); lo = np.where(same & (hi == lo), lo - 1, lo)
    # 8-value mode (red0 > red1): code 0 = red0 (hi), 1 = red1 (lo), 2..7 = (8-k)/7 red0 + (k-1)/7 red1
    t = (q - lo[:, None]) / np.maximum(hi - lo, 1)[:, None]          # 0 at lo, 1 at hi
    step = np.clip(np.round((1 - t) * 7), 0, 7).astype(np.int64)     # 0 = hi .. 7 = lo
    code = np.where(step == 0, 0, np.where(step == 7, 1, step + 1))
    bits = np.zeros(len(blk), np.uint64)
    for k in range(16):
        bits |= code[:, k].astype(np.uint64) << np.uint64(3 * k)
    outb = np.zeros((len(blk), 8), np.uint8)
    outb[:, 0] = hi.astype(np.uint8); outb[:, 1] = lo.astype(np.uint8)
    for k in range(6):
        outb[:, 2 + k] = ((bits >> np.uint64(8 * k)) & np.uint64(0xff)).astype(np.uint8)
    return outb.tobytes()
ph, pl = header_and_size(prim_in)
pb = bc4(np.clip(prim, 0, 1))
assert len(pb) == pl, (len(pb), pl)
open(os.path.join(out, "_lightmap0_primary.h1Image"), "wb").write(ph + pb)

# previews
from PIL import Image
def tone(x): return (np.clip(np.sqrt(np.clip(x / 2.0, 0, 1)), 0, 1) * 255).astype(np.uint8)
Image.fromarray(np.concatenate([tone(pageA + pageB), (np.repeat(prim[::2, ::2, None], 3, 2) * 255).astype(np.uint8)], 1)).resize((1024, 1024)).save(os.path.join(out, "preview.png"))
print("written", out)
