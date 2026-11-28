"""Give BO2 materials that have no normal map one made from their colour picture (luminance as height), so flat
vehicle bodies (jets, VTOLs, helicopters) pick up panel and rivet detail in the H1 lighting.
usage: make_default_normals.py <mats.tsv> <images dir> <out dir> [name substrings, comma; default vehicle bodies] [strength 3.0]
Writes <colour>_gen_n.dds (BC5, DXGI 83, full mips) into <out dir> and <out dir>/<mats.tsv name> with the normal column set."""
import sys, os, struct, numpy as np, texture2ddecoder as t2d, etcpak
from scipy import ndimage
from PIL import Image
tsv, imgdir, out = sys.argv[1:4]
subs = (sys.argv[4] if len(sys.argv) > 4 else 'veh_t6_air,vtol,pegasus,blackhawk,veh_').split(',')
K = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
os.makedirs(out, exist_ok=True)
DEC = {71: t2d.decode_bc1, 72: t2d.decode_bc1, 77: t2d.decode_bc3, 78: t2d.decode_bc3, 98: t2d.decode_bc7, 99: t2d.decode_bc7}
def load(path):
    b = open(path, 'rb').read(); h, w = struct.unpack_from('<II', b, 12); fmt = struct.unpack_from('<I', b, 128)[0]
    a = np.frombuffer(DEC[fmt](b[148:], w, h), np.uint8).reshape(h, w, 4)[..., [2, 1, 0]].astype(np.float32) / 255
    return a
def write_bc5(path, n):
    h, w = n.shape[:2]; body = bytearray(); levels = 0; cur = n
    while True:
        rg = np.zeros((cur.shape[0], cur.shape[1], 4), np.uint8); rg[..., 0] = cur[..., 0]; rg[..., 1] = cur[..., 1]; rg[..., 3] = 255
        body += etcpak.compress_bc5(rg.tobytes(), cur.shape[1], cur.shape[0]); levels += 1
        if cur.shape[0] <= 4 or cur.shape[1] <= 4: break
        cur = np.array(Image.fromarray(cur).resize((cur.shape[1] // 2, cur.shape[0] // 2), Image.LANCZOS))
    hd = bytearray(b'DDS '); p = lambda v: hd.extend(struct.pack('<I', v))
    p(124); p(0x000A1007); p(h); p(w); p((w // 4) * (h // 4) * 16); p(0); p(levels)
    for _ in range(11): p(0)
    p(32); p(4); hd.extend(b'DX10')
    for _ in range(5): p(0)
    p(0x00401008)
    for _ in range(4): p(0)
    p(83); p(3); p(0); p(1); p(0)
    open(path, 'wb').write(bytes(hd) + bytes(body))
rows = [l.rstrip('\n').split('\t') for l in open(tsv)]; made = {}
for r in rows:
    if len(r) < 4 or r[1] != '0' or r[3] != '-' or not any(s in r[0] or s in r[2] for s in subs): continue
    col = r[2]; src = os.path.join(imgdir, col + '.dds')
    if not os.path.exists(src): continue
    if col not in made:
        c = load(src); L = c @ np.array([0.299, 0.587, 0.114], np.float32)
        hgt = L - ndimage.gaussian_filter(L, 24)          # high-pass: panel lines and rivets, not the paint scheme
        hgt = ndimage.gaussian_filter(hgt, 0.7)
        dx = ndimage.sobel(hgt, 1) * K; dy = ndimage.sobel(hgt, 0) * K
        nz = 1.0 / np.sqrt(dx * dx + dy * dy + 1)
        n = np.zeros(hgt.shape + (2,), np.uint8)
        n[..., 0] = np.clip((-dx * nz * 0.5 + 0.5) * 255, 0, 255); n[..., 1] = np.clip((dy * nz * 0.5 + 0.5) * 255, 0, 255)
        name = col + '_gen_n'; write_bc5(os.path.join(out, name + '.dds'), n); made[col] = name
        print('normal', name, c.shape[:2])
    r[3] = made[col]
open(os.path.join(out, os.path.basename(tsv)), 'w').write('\n'.join('\t'.join(r) for r in rows) + '\n')
print('materials given a normal:', sum(1 for r in rows if len(r) > 3 and r[3].endswith('_gen_n')), 'pictures', len(made))
