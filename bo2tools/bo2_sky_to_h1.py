"""A Black Ops II sky cube (DXT5 RGBM 512^2 faces, stored bytes as pulled from the ipak, level 0 of 6 faces) as the
H1 sky: RGBA8 DX10 cube dds, same face order and orientation (verified), rgb x alpha x scale, a light blur against
the BC3/RGBM blocking, and the lower half filled with the horizon colour fading into haze (H1's sea does not cover
the whole lower half, and BO2's painted-ocean band would show above the water edge).
usage: bo2_sky_to_h1.py <raw> <header-template.dds> <out.dds> [scale 0.62]"""
import sys, numpy as np, texture2ddecoder as t2d
from scipy import ndimage
sys.path.insert(0, '/tmp'); from skylib import dirs, load
raw = open(sys.argv[1], 'rb').read(); hdr, _ = load(sys.argv[2]); out = sys.argv[3]
K = float(sys.argv[4]) if len(sys.argv) > 4 else 0.62
N = 512; fs = len(raw) // 6
F = np.zeros((6, N, N, 4), np.float32)
for f in range(6):
    a = np.frombuffer(t2d.decode_bc3(raw[f * fs:f * fs + N * N], N, N), np.uint8).reshape(N, N, 4)[..., [2, 1, 0, 3]].astype(np.float32) / 255
    rgb = a[..., :3] * a[..., 3:4] * K
    for c in range(3): rgb[..., c] = ndimage.gaussian_filter(rgb[..., c], 0.8)
    F[f, ..., :3] = rgb; F[f, ..., 3] = 1
# horizon colour per azimuth: mean over elevation 0.5..2.5 deg, 360 bins
D = np.stack([dirs(f) for f in range(6)]); el = np.degrees(np.arcsin(np.clip(D[..., 2], -1, 1)))
az = (np.degrees(np.arctan2(D[..., 1], D[..., 0])) + 360) % 360
band = (el > 0.5) & (el < 2.5); hb = np.zeros((360, 3)); cnt = np.zeros(360)
ib = az[band].astype(int) % 360
for c in range(3): np.add.at(hb[:, c], ib, F[..., c][band])
np.add.at(cnt, ib, 1); hb /= np.maximum(cnt, 1)[:, None]
for c in range(3): hb[:, c] = ndimage.gaussian_filter1d(hb[:, c], 6, mode='wrap')
haze = hb.mean(0) * 0.7
low = el < 0.5
w = np.clip((0.5 - el) / 12.0, 0, 1)[..., None]
hc = hb[az.astype(int) % 360]
fill = hc * (1 - w) + haze * w
t = np.clip((el - (-0.5)) / 1.0, 0, 1)[..., None]       # 1 deg seam blend
F[..., :3] = np.where(low[..., None], fill * (1 - t) + F[..., :3] * t, F[..., :3])
open(out, 'wb').write(hdr + (np.clip(F, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
print('written', out)
