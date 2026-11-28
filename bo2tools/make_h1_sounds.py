"""Turn a t6_map_ambient_export folder into H1 sound aliases for waw_port.ps1.
usage: make_h1_sounds.py <export dir> <impact sounds dir (zonetool/mp_ca_impact/sounds)> <out dir> [prefix]
Writes <out>/sounds/<prefix><alias>.json, <out>/loaded_sound/<prefix>/*.wav and <out>/sound_place.txt."""
import json, copy, os, shutil, math, sys
src, T, out = sys.argv[1:4]
pre = sys.argv[4] if len(sys.argv) > 4 else 'bo2c_'
emt = json.load(open(os.path.join(T, 'emt_impact_dist_ocean_wind_lp.json')))
bed = json.load(open(os.path.join(T, 'ambient_mp_impact.json')))
os.makedirs(os.path.join(out, 'sounds'), exist_ok=True)
wdir = os.path.join(out, 'loaded_sound', pre.rstrip('_'))
os.makedirs(wdir, exist_ok=True)
place = [l.rstrip('\n').split('\t') for l in open(os.path.join(src, 'places.tsv'))]
lines = []
for l in open(os.path.join(src, 'sounds.tsv')):
    a, kind, loop, is3d, vmin, vmax, dmin, dmax, wmin, wmax, files = l.rstrip('\n').split('\t')
    if not files:
        continue
    files = [f.split(':')[0] for f in files.split(',')]
    name = pre + a
    v = float(vmax)
    tpl = bed if kind == 'tone' else emt
    vol = 0.55 if kind == 'tone' else max(0.25, min(0.9, 0.5 * math.sqrt(v / 0.018)))
    heads = []
    for f in files:
        shutil.copy(os.path.join(src, f), os.path.join(wdir, f))
        h = copy.deepcopy(tpl['head'][0])
        h['aliasName'] = name; h['secondaryAliasName'] = None
        h['soundfile'] = {'type': 1, 'exists': True, 'name': pre.rstrip('_') + '/' + f[:-4]}
        h['flags']['looping'] = int(loop)
        h['flags']['randomLooping'] = 1 if kind == 'tone' else 0
        h['volMin'] = vol; h['volMax'] = vol
        if kind != 'tone':
            h['distMin'] = float(dmin); h['distMax'] = max(float(dmax), float(dmin) + 50)
            h['volumeFalloffCurve'] = '$default'
        heads.append(h)
    json.dump({'aliasName': name, 'count': len(heads), 'head': heads}, open(os.path.join(out, 'sounds', name + '.json'), 'w'), indent=1)
    if kind == 'tone':
        lines.append('%s tone 0 0 0 0 0' % name)
    else:
        for p in place:
            if p[0] == a:
                lines.append('%s %s %s %s %s %s %s' % (name, kind, p[1], p[2], p[3], wmin, wmax))
open(os.path.join(out, 'sound_place.txt'), 'w').write('# alias kind x y z waitmin waitmax (the Black Ops II map ambience)\n' + '\n'.join(lines) + '\n')
print(len(lines), 'placements')
