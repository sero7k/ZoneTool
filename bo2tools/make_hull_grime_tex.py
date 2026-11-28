# Macro hull grime for BO2 ship hulls (alpha-blended decal over the hull): rust streaks hanging from the deck edge,
# soft grime blotches, horizontal weld lines and a dark boot-top band at the waterline.
# Texture: u tiles along the hull (2048 units), v = 0 at the deck edge (z=TOP) .. 1 at TOP-1400.
import numpy as np, sys
from scipy import ndimage
from PIL import Image
rng = np.random.default_rng(7)
W, H = 1024, 1024
def noise(scale, seed):
    r = np.random.default_rng(seed).random((H // scale + 3, W // scale + 3))
    r = np.concatenate([r, r[:, :3]], 1)[:, :W // scale + 3]
    z = ndimage.zoom(r, scale, order=3)[:H, :W]
    return (z - z.min()) / (z.max() - z.min() + 1e-9)
v = (np.arange(H) / H)[:, None] * np.ones((1, W))
col = np.zeros((H, W, 3)); a = np.zeros((H, W))
def over(c, al):
    global col, a
    al = np.clip(al, 0, 1)
    col = col * (a * (1 - al))[..., None] + np.array(c)[None, None] * al[..., None]
    na = a + al * (1 - a)
    col = col / np.maximum(na, 1e-6)[..., None] * (a * (1 - al) + al)[..., None] if False else col
    a = na
# soft grime blotches (low frequency), stronger lower down
n1 = noise(128, 1) * 0.6 + noise(48, 2) * 0.3 + noise(16, 3) * 0.1
blot = np.clip((n1 - 0.40) * 1.8, 0, 1) * (0.35 + 0.35 * v) + np.exp(-v / 0.06) * 0.6
# rust streaks: thin vertical runs from the top and from weld lines, fading downward
streak = np.zeros((H, W))
for i in range(340):
    x = rng.integers(0, W); y0 = int(rng.choice([0, 0, 0.08, 0.22, 0.36, 0.5, 0.64]) * H)
    L = rng.integers(60, 520); w = rng.uniform(2.5, 9.0); s = rng.uniform(0.55, 1.0)
    ys = np.arange(y0, min(H, y0 + L))
    fade = (1 - (ys - y0) / L) ** 1.5 * s
    for dx in range(-12, 13):
        xx = (x + dx + (np.sin(ys / rng.uniform(40, 120)) * 1.5).astype(int)) % W
        streak[ys, xx] = np.maximum(streak[ys, xx], fade * np.exp(-(dx / w) ** 2))
streak = ndimage.gaussian_filter(streak, (6.0, 1.2)) * (0.55 + 0.45 * noise(32, 4))
# weld lines (horizontal) every ~ 1/7 of the height, faint
weld = np.zeros((H, W))
for yl in [0.08, 0.22, 0.36, 0.5, 0.64]:
    y = int(yl * H); weld[y - 2:y + 3] = 0.45
weld = ndimage.gaussian_filter(weld, (1.0, 0)) * (0.6 + 0.4 * noise(64, 5))
# waterline: sea at z=-716, deck edge TOP=540 -> v_sea = 1256/1400 = 0.897; boot-top band from 0.835 to below
vs = 0.897
band = np.clip((v - 0.815) / 0.01, 0, 1)
band_edge = np.exp(-((v - 0.835) / 0.02) ** 2) * 0.4 * noise(24, 6)
# compose (colours in sRGB)
grime_c = np.array([0.09, 0.09, 0.10]); rust_c = np.array([0.50, 0.26, 0.11]); band_c = np.array([0.05, 0.045, 0.045])
# (pass 11) hull plating: vertical seams every 128 px (256 units) between the weld lines, staggered per strake,
# and a faint per-plate tone, so the big hull sides read as welded plates instead of flat grey
plate = np.zeros((H, W)); seam = np.zeros((H, W))
rows = [0.0, 0.08, 0.22, 0.36, 0.5, 0.64, 0.80, 1.0]
for r in range(len(rows) - 1):
    y0, y1 = int(rows[r] * H), int(rows[r + 1] * H); off = (r * 53) % 128
    for xs in range(-128, W, 128):
        x0 = xs + off; tone = np.random.default_rng(1000 + r * 31 + xs).uniform(0.0, 0.16)
        plate[y0:y1, max(0, x0):max(0, min(W, x0 + 128))] = tone
        if 0 <= x0 < W: seam[y0:y1, x0:x0 + 2] = 0.40
plate = ndimage.gaussian_filter(plate, 1.5); seam = ndimage.gaussian_filter(seam, (0, 0.8)) * (0.6 + 0.4 * noise(40, 9))
A = np.clip(blot * 2.2 + weld * 0.9 + plate + seam, 0, 1)
C = np.ones((H, W, 3)) * grime_c
rA = np.clip(streak, 0, 1) * 1.0 * np.clip((v - 0.07) / 0.13, 0, 1) ** 1.5   # (pass 9) no rust right at the deck edge: it smeared along the lip
C = C * (1 - rA[..., None]) + rust_c * rA[..., None]; A = A + rA * (1 - A)
bA = np.clip(band * 0.97 + band_edge, 0, 1)
C = C * (1 - bA[..., None]) + band_c * bA[..., None]; A = A + bA * (1 - A)
# rust tide marks just above the band
tide = np.exp(-((v - 0.80) / 0.02) ** 2) * 0.6 * noise(20, 8)
C = C * (1 - tide[..., None]) + rust_c * tide[..., None]; A = A + tide * (1 - A)
img = np.dstack([np.clip(C, 0, 1) * 255, np.clip(A, 0, 1) * 255]).astype(np.uint8)
Image.fromarray(img, 'RGBA').save('hull_grime_v2.png')
# preview over a grey hull
base = np.ones((H, W, 3)) * 0.42
prev = base * (1 - A[..., None]) + C * A[..., None]
Image.fromarray((prev * 255).astype(np.uint8)).resize((512, 512)).save('hull_grime_v2_prev.png')
print('alpha mean', A.mean())
