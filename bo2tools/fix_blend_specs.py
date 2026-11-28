# Blend-layer materials ("*<ids>(base:layer:...)") in <stem>.mats.tsv sometimes carry a decal layer's spec/gloss
# (oil stain, trim paint, hatch...) for the whole surface: e.g. the flight deck under me_oilstain rendered as a glossy
# charcoal block. Give every such row the spec/gloss most used by rows of the same base colour that carry the base's own spec.
# usage: fix_blend_specs.py <in mats.tsv> <out mats.tsv>
import collections, sys
L = [l.rstrip('\n').split('\t') for l in open(sys.argv[1])]
grp = collections.defaultdict(list)
for r in L:
    if len(r) >= 6 and r[0].startswith('*'): grp[r[2]].append(r)
def stem(s): return s[1:].split('_c_')[0].split('_col')[0][:18] if s.startswith('g') else s[:18]
ch = 0
for col, rows in grp.items():
    good = [r for r in rows if r[4].startswith('gdef_spec_' + col[:20]) or (r[4] != '-' and stem(col)[:12] in r[4])]
    if not good: continue
    best = collections.Counter((r[4], r[5]) for r in good).most_common(1)[0][0]
    for r in rows:
        if (r[4], r[5]) != best and r not in good: r[4], r[5] = best; ch += 1
open(sys.argv[2], 'w').write(''.join('\t'.join(r) + '\n' for r in L))
print('rows changed', ch)
