"""Swap Black Ops II static models for stock MWR models where MWR has the same (or a listed) asset.
Matches: exact name (also with an h1_ prefix) in the dumped retail zones' model lists, then bo2_prop_map.tsv rules.
Only upright, unscaled placements are swapped (H1 script models take a yaw only). The BO2 copy's triangles are made
degenerate in the .h1map (so vertex-indexed side files stay valid) and the MWR model is spawned in its place.
usage: bo2_props.py <smodels.tsv> <h1map> <lmuv> <prop map tsv> <out h1map> <out h1_models lines> <out h1_imports lines>
       zone model lists: env BO2_PROP_ZONES="zone=listfile;zone=listfile" (list files: one model name per line)"""
import sys, os, re, struct, numpy as np
sys.path.insert(0, '/home/claude/carrier_look'); from h1map import H1Map
smf, hp, lp, mapf, outh, outm, outi = sys.argv[1:8]
zones = []
for z in os.environ.get('BO2_PROP_ZONES', '').split(';'):
    if '=' in z:
        zn, lf = z.split('=', 1); zones.append((zn, {l.strip() for l in open(lf) if l.strip()}))
rules = [(re.compile(p[0]), p[1], p[2]) for p in (l.rstrip('\n').split('\t') for l in open(mapf) if l.strip() and not l.startswith('#')) if len(p) >= 3]
sm = [l.rstrip('\n').split('\t') for l in open(smf)]
swap = {}; lines = []; imports = set()
for r in sm:
    i = int(r[0]); n = r[1].split('/')[-1]; x, y, z, yaw, pitch, roll, sc = map(float, r[2:9])
    if abs(pitch) > 1 or abs(roll) > 1 or abs(sc - 1) > 0.02: continue
    tgt = None
    for zn, names in zones:
        for c in (n, 'h1_' + n):
            if c in names: tgt = (c, zn); break
        if tgt: break
    if not tgt:
        rr = next((q for q in rules if q[0].search(n)), None)
        if rr: tgt = (rr[1], rr[2])
    if not tgt: continue
    swap[i] = tgt; lines.append(f"{tgt[0]} {x:.2f} {y:.2f} {z:.2f} {yaw:.2f}"); imports.add(f"xmodel {tgt[1]} {tgt[0]}")
m = H1Map(hp)
lb = np.fromfile(lp, np.uint8); uv = np.frombuffer(lb[4:], np.float32).reshape(-1, 2)
sidx = np.where(uv[:, 0] <= -1.5, np.round(-uv[:, 0] - 2).astype(np.int64), -1)
gone = np.zeros(len(sidx), bool)
for i in swap: gone |= sidx == i
I = np.frombuffer(m.b, '<u2', m.nidx, m.idx_off).copy(); ndeg = 0
for s in m.surfs:
    mat, vb, nv, ib, nt = s[:5]
    t = I[ib:ib + nt * 3].reshape(-1, 3)
    kill = gone[t.astype(np.int64) + vb].any(1)
    if kill.any(): t[kill] = t[kill][:, :1]; ndeg += int(kill.sum())
b = bytearray(m.b); b[m.idx_off:m.idx_off + m.nidx * 2] = I.tobytes(); open(outh, 'wb').write(bytes(b))
open(outm, 'w').write('\n'.join(['# MWR stock props in place of the same Black Ops II models (bo2_props.py)'] + lines) + '\n')
open(outi, 'w').write('\n'.join(sorted(imports)) + '\n')
print(f"{len(swap)} placements swapped ({len(imports)} models), {ndeg} triangles hidden")
