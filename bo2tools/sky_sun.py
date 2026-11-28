"""Paint a sun disc, halo, lit cloud edges and a warm horizon band into an H1 sky cube (RGBA8 DX10 cube dds, faces
+X -X +Y -Y +Z -Z, world Z up: verified against an in-game screenshot).
usage: sky_sun.py <in.dds> <out.dds> sx sy sz [band strength] [halo strength]"""
import sys, numpy as np, math
from scipy import ndimage
src, dst = sys.argv[1:3]; S = np.array([float(x) for x in sys.argv[3:6]]); S /= np.linalg.norm(S)
K = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0          # horizon band strength
KH = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5        # sun halo strength
d = open(src, 'rb').read(); hdr = d[:148]
F = np.frombuffer(d[148:], np.uint8).reshape(6, 512, 512, 4).astype(np.float32) / 255
N = 512; c = (np.arange(N) + 0.5) / N * 2 - 1
tc, sc = np.meshgrid(c, c, indexing='ij')
def dirs(f):
    one = np.ones_like(sc)
    if f == 0: x, y, z = one, -tc, -sc
    if f == 1: x, y, z = -one, -tc, sc
    if f == 2: x, y, z = sc, one, tc
    if f == 3: x, y, z = sc, -one, -tc
    if f == 4: x, y, z = sc, -tc, one
    if f == 5: x, y, z = -sc, -tc, -one
    # (x,y,z) here are D3D cube coordinates; the game samples with world (x,y,z) directly
    v = np.stack([x, y, z], -1); return v / np.linalg.norm(v, axis=-1, keepdims=True)
warm = np.array([1.0, 0.62, 0.32]); hot = np.array([1.0, 0.99, 0.95])
for f in range(6):
    D = dirs(f)
    # fix face orientation mapping: face f, texel (row=t, col=s) -> direction, consistent with the sampler used to fit
    th = np.degrees(np.arccos(np.clip((D * S).sum(-1), -1, 1)))
    el = np.degrees(np.arcsin(np.clip(D[..., 2], -1, 1)))
    rgb = F[f, ..., :3].copy()
    lum = rgb.mean(-1, keepdims=True)
    thin = np.clip(1.4 - lum * 2.2, 0, 1)                       # cloud gaps let more glow through
    halo = (np.exp(-th / 2.5) * 0.9 + np.exp(-th / 9.0) * 0.45 + np.exp(-th / 30.0) * 0.18)[..., None] * KH
    rgb = rgb * (1 + halo * warm * 1.6) + halo * warm * 0.35 * (0.4 + 0.6 * thin)
    az = np.clip(((D[..., :2] * S[:2]).sum(-1) / max(np.linalg.norm(S[:2]), 1e-6) + 1) / 2, 0, 1)
    band = (np.exp(-np.clip(el, 0, None) / 4.0) * (el > -3))[..., None] * (0.25 + 0.75 * az[..., None] ** 2) * K
    rgb = rgb * (1 - band * 0.25) + band * warm * 0.32
    disc = np.clip((0.9 - th) / 0.3, 0, 1)[..., None]
    rgb = np.maximum(rgb * (1 - disc) + hot * disc, rgb)
    for ch in range(3): rgb[..., ch] = ndimage.gaussian_filter(rgb[..., ch], 0.7)
    F[f, ..., :3] = np.clip(rgb, 0, 1)
open(dst, 'wb').write(hdr + (F * 255 + 0.5).astype(np.uint8).tobytes())
print('written', dst)
