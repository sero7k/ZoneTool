"""Give every opaque BO2 material that has no specular picture an H1 one (rgb = specular colour, alpha = gloss,
BC3 sRGB like the exporter's own `_s` pictures), so no surface is the dead-matte `$black` specular.
The level comes from the material's kind of surface (name keywords), the gloss varies with the colour picture
(darker, grimier texels are rougher). Writes <out dir>/<name>.dds and a new mats.tsv.
usage: make_default_specs.py <mats.tsv> <colour dds dir> <out dir> <out mats.tsv> [max side 512]"""
import sys, os, struct, re, numpy as np
sys.path.insert(0, '/home/claude/tools'); import dds, ddswrite
from PIL import Image
mats, cdir, odir, omats = sys.argv[1:5]; MAXS = int(sys.argv[5]) if len(sys.argv) > 5 else 512
os.makedirs(odir, exist_ok=True)
# (specular sRGB level, gloss 0-255), first match wins
CATS = [(r'glass|window', (150, 225)), (r'water', (120, 230)),
        (r'flightdeck|floor_.*deck|nonskid|asphalt|tarmac', (44, 38)),
        (r'hull|ship_wall|metal_wall|paint|painted|panel', (88, 100)),
        (r'chrome|steel|metal|pipe|rail|grate|iron|alum|tank|vent|duct|door|hatch|wire|cable', (96, 110)),
        (r'concrete|cement|stone|brick|plaster|rock|dirt|sand|ground', (48, 40)),
        (r'wood|fabric|cloth|rubber|tarp|rope|foam|carpet|paper|cardboard', (36, 30)),
        (r'plastic|vinyl|case', (70, 120)), (r'', (56, 55))]
rows = [l.rstrip('\n').split('\t') for l in open(mats)]
made = {}; n = 0
for r in rows:
    if len(r) < 6 or r[1] != '0' or r[4] != '-' or r[2] == '-': continue
    col = r[2]; name = r[0].lower()
    lvl, gl = next(v for k, v in CATS if re.search(k, name))
    key = (col, lvl, gl)
    if key not in made:
        p = os.path.join(cdir, col + '.dds')
        if not os.path.exists(p): continue
        try: a, fm, _ = dds.read(p)
        except Exception as e: print('skip', col, e); continue
        h, w = a.shape[:2]; s = min(MAXS, max(w, h)) / max(w, h)
        im = Image.fromarray(a[..., :3]).resize((max(4, int(w * s)), max(4, int(h * s))), Image.LANCZOS)
        c = np.asarray(im, np.float32) / 255
        lum = c @ np.array([0.3, 0.59, 0.11], np.float32)
        z = (lum - lum.mean()) / (lum.std() + 1e-3)
        g = np.clip(gl * (1 + 0.22 * np.clip(z, -2.5, 2.5)), 8, 250)
        sp = np.clip(lvl * (0.85 + 0.3 * np.clip(lum / (lum.mean() + 1e-3), 0, 2) * 0.5), 10, 250)
        img = np.dstack([sp, sp, sp, g]).astype(np.uint8)
        out = 'gdef_spec_' + col[:40] + '_%d_%d' % (lvl, gl)
        fp = os.path.join(odir, out + '.dds')
        ddswrite.write(fp, Image.fromarray(img, 'RGBA'), 'bc3')
        d = bytearray(open(fp, 'rb').read()); struct.pack_into('<I', d, 128, 78); open(fp, 'wb').write(d)
        made[key] = out
    r[4] = made[key]; n += 1
open(omats, 'w').write('\n'.join('\t'.join(r) for r in rows) + '\n')
print(f'{n} materials got a default specular, {len(made)} pictures')
