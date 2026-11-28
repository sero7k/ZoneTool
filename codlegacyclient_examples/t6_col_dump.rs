//! bo2mp: a Black Ops II map's own collision as a triangle soup for the H1 importer. Writes `<out>/<stem>.col`:
//! "BO2COL01", u32 material count, per material (u16 name length, name bytes, i32 surface flags, i32 content flags),
//! u32 triangle count, per triangle 9 f32 (three corners) + u16 material + u16 source (0 mesh, 1 brush, 2 static model box).
//! Sources: the clip map's collision partitions (material from the aabb leaf that owns each partition), the world
//! brushes (cmodel 0's brushes, made into triangles by clipping each side plane by the others; only solid or
//! player-clip contents) and the clip static models (an oriented box per model collision surface); brush and box triangles are wound like the clip map's own
//! (geometric normal pointing into the solid, as Black Ops II's floor triangles face down), (their world boxes, as "clip_smodel_box").
//!
//! `cargo run --release -p asset_t6 --example t6_col_dump -- <mp_map.ff> <out dir> <stem>`
type V = [f64; 3];
fn sub(a: V, b: V) -> V { [a[0] - b[0], a[1] - b[1], a[2] - b[2]] }
fn add(a: V, b: V) -> V { [a[0] + b[0], a[1] + b[1], a[2] + b[2]] }
fn mul(a: V, s: f64) -> V { [a[0] * s, a[1] * s, a[2] * s] }
fn dot(a: V, b: V) -> f64 { a[0] * b[0] + a[1] * b[1] + a[2] * b[2] }
fn cross(a: V, b: V) -> V { [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]] }
fn norm(a: V) -> V { let l = dot(a, a).sqrt(); if l > 0.0 { mul(a, 1.0 / l) } else { a } }

/// Convex polygon of plane (n, d) clipped by every other plane (keep dot(n_j, p) <= d_j).
fn face(planes: &[(V, f64)], i: usize) -> Vec<V> {
    let (n, d) = planes[i];
    let a = if n[2].abs() < 0.9 { [0.0, 0.0, 1.0] } else { [1.0, 0.0, 0.0] };
    let u = norm(cross(n, a)); let v = cross(n, u);
    let c = mul(n, d); let s = 1e6;
    let mut poly = vec![add(c, add(mul(u, -s), mul(v, -s))), add(c, add(mul(u, s), mul(v, -s))), add(c, add(mul(u, s), mul(v, s))), add(c, add(mul(u, -s), mul(v, s)))];
    for (j, &(nj, dj)) in planes.iter().enumerate() {
        if j == i || poly.is_empty() { continue; }
        if dot(nj, n) > 0.9999 && (dj - d).abs() < 1e-3 { continue; }
        let mut out = Vec::new();
        for k in 0..poly.len() {
            let p = poly[k]; let q = poly[(k + 1) % poly.len()];
            let dp = dot(nj, p) - dj; let dq = dot(nj, q) - dj;
            if dp <= 0.01 { out.push(p); }
            if (dp > 0.01) != (dq > 0.01) { let t = dp / (dp - dq); out.push(add(p, mul(sub(q, p), t))); }
        }
        poly = out;
    }
    poly
}

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let zone = std::path::Path::new(&a[0]);
    let out = std::path::Path::new(&a[1]);
    let stem = a.get(2).cloned().unwrap_or_else(|| "map".into());
    std::fs::create_dir_all(out).ok();
    let cap = asset_t6::capture_zone(zone).expect("capture");
    let c = cap.clip.as_ref().expect("clip map");
    let mut mats: Vec<(String, i32, i32)> = c.materials.iter().map(|m| (m.name.clone(), m.surface_flags, m.content_flags)).collect();
    let mut tris: Vec<([f32; 9], u16, u16)> = Vec::new();
    // mesh: partition -> material from the leaf aabb trees
    let mut part_mat = vec![0u16; c.partitions.len()];
    for t in &c.aabb_trees { if t.child_count == 0 && (t.u as usize) < part_mat.len() { part_mat[t.u as usize] = t.material_index; } }
    let mut walk_skip = 0usize;
    for (pi, &(n, first)) in c.partitions.iter().enumerate() {
        for k in 0..n as usize {
            let ti = first as usize + k;
            if ti * 3 + 2 >= c.tri_indices.len() { walk_skip += 1; continue; }
            let mut t = [0f32; 9];
            for v in 0..3 { let p = c.verts[c.tri_indices[ti * 3 + v] as usize]; t[v * 3] = p[0]; t[v * 3 + 1] = p[1]; t[v * 3 + 2] = p[2]; }
            tris.push((t, part_mat[pi], 0));
        }
    }
    let mesh_n = tris.len();
    // brushes: every brush except those listed by entity brush models (cmodels 1..: doors, triggers, volumes).
    // (Walking only the world leaves' brush lists missed ~1100 brushes, the stern deck among them.)
    let gather = |root: i32, out: &mut std::collections::BTreeSet<usize>| {
        let mut stack = vec![root as usize]; let mut seen = std::collections::HashSet::new();
        while let Some(ni) = stack.pop() {
            if ni >= c.leafbrush_nodes.len() || !seen.insert(ni) { continue; }
            let node = &c.leafbrush_nodes[ni];
            if node.leaf_brush_count > 0 { for &b in &node.brushes { out.insert(b as usize); } }
            else { for &o in &node.child_offset { if o > 0 { stack.push(ni + o as usize); } } }
        }
    };
    let mut entity_brushes = std::collections::BTreeSet::new();
    for m in c.cmodels.iter().skip(1) { if m.shares_map_info && m.leaf.leaf_brush_node > 0 { gather(m.leaf.leaf_brush_node, &mut entity_brushes); } }
    let mut world_leaf = std::collections::BTreeSet::new();
    for leaf in &c.leaves { if leaf.leaf_brush_node > 0 { gather(leaf.leaf_brush_node, &mut world_leaf); } }
    let world_brushes: Vec<usize> = (0..c.brushes.len()).filter(|i| !entity_brushes.contains(i) || world_leaf.contains(i)).collect();
    println!("brushes: {} total, {} in world leaves, {} only in entity models (skipped)", c.brushes.len(), world_leaf.len(), c.brushes.len() - world_brushes.len());
    let solid_mat = mats.len() as u16; mats.push(("clip_brush_solid".into(), 0, 1));
    let clip_mat = mats.len() as u16; mats.push(("clip_brush_player".into(), 0, 0x10000));
    let mut brush_n = 0; let mut big_skipped = 0;
    // brushes bigger than this on any axis are the map's outer volumes (whole-map boxes far past the playable area);
    // as triangle shells their faces span the world and break the H1 collision tree
    let max_brush: f32 = std::env::var("COL_MAX_BRUSH").ok().and_then(|v| v.parse().ok()).unwrap_or(9000.0);
    for &bi in world_brushes.iter() {
        let Some(b) = c.brushes.get(bi) else { continue };
        let cont = c.brush_contents.get(bi).copied().unwrap_or(b.contents);
        let mat = if cont & 1 != 0 { solid_mat } else if cont & 0x10000 != 0 { clip_mat } else { continue };
        let ext = (0..3).map(|k| b.maxs[k] - b.mins[k]).fold(0f32, f32::max);
        if std::env::var("COL_SIZES").is_ok() { eprintln!("brush {bi} cont {cont:#x} ext {ext:.0} mins {:?} maxs {:?}", b.mins, b.maxs); }
        if ext > max_brush { big_skipped += 1; continue; }
        let mut planes: Vec<(V, f64)> = Vec::new();
        for k in 0..3 { let mut n = [0.0; 3]; n[k] = -1.0; planes.push((n, -(b.mins[k] as f64))); let mut n = [0.0; 3]; n[k] = 1.0; planes.push((n, b.maxs[k] as f64)); }
        for (n, d, _) in &b.sides { planes.push(([n[0] as f64, n[1] as f64, n[2] as f64], *d as f64)); }
        for i in 0..planes.len() {
            let poly = face(&planes, i);
            if poly.len() < 3 { continue; }
            for k in 1..poly.len() - 1 {
                let (p0, p1, p2) = (poly[0], poly[k], poly[k + 1]);
                if dot(cross(sub(p1, p0), sub(p2, p0)), cross(sub(p1, p0), sub(p2, p0))) < 1e-4 { continue; }
                let mut t = [0f32; 9];
                for (v, p) in [p0, p2, p1].iter().enumerate() { for q in 0..3 { t[v * 3 + q] = p[q] as f32; } }
                tris.push((t, mat, 1)); brush_n += 1;
            }
        }
    }
    // static models with collision: oriented boxes, one per model collision surface (its model-space bounds),
    // or the whole model's bounds when it has none; placed by the inverse of the static model's inv_scaled_axis
    let box_mat = mats.len() as u16; mats.push(("clip_smodel_box".into(), 0, 1));
    let mut sm_n = 0; let mut sm_used = 0; let mut worst = 0f32; let mut errs: Vec<f32> = Vec::new();
    let inv3 = |m: [[f32; 3]; 3]| -> Option<[[f64; 3]; 3]> {
        let a: [[f64; 3]; 3] = [[m[0][0] as f64, m[0][1] as f64, m[0][2] as f64], [m[1][0] as f64, m[1][1] as f64, m[1][2] as f64], [m[2][0] as f64, m[2][1] as f64, m[2][2] as f64]];
        let det = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
        if det.abs() < 1e-12 { return None; }
        let mut r = [[0.0; 3]; 3];
        for i in 0..3 { for j in 0..3 {
            let (i1, i2, j1, j2) = ((j + 1) % 3, (j + 2) % 3, (i + 1) % 3, (i + 2) % 3);
            r[i][j] = (a[i1][j1] * a[i2][j2] - a[i1][j2] * a[i2][j1]) / det;
        } }
        Some(r)
    };
    for sm in &c.static_models {
        if sm.contents == 0 { continue; }
        let Some(key) = sm.model else { continue };
        let Some(xm) = cap.xmodels.get(key.index) else { continue };
        let Some(mut minv) = inv3(sm.inv_scaled_axis) else { continue };
        if std::env::var("COL_NO_T").is_err() { let m = minv; for i in 0..3 { for j in 0..3 { minv[i][j] = m[j][i]; } } }
        let to_world = |p: [f32; 3]| -> [f32; 3] {
            let l = [p[0] as f64, p[1] as f64, p[2] as f64];
            let mut w = [0f32; 3];
            for i in 0..3 { w[i] = sm.origin[i] + (minv[i][0] * l[0] + minv[i][1] * l[1] + minv[i][2] * l[2]) as f32; }
            w
        };
        let boxes: Vec<([f32; 3], [f32; 3])> = if xm.coll_surfs.is_empty() { vec![(xm.mins, xm.maxs)] } else { xm.coll_surfs.iter().map(|cs| (cs.mins, cs.maxs)).collect() };
        // sanity: the model bounds placed this way should land inside the clip map's absmin/absmax
        let mut amn = [f32::MAX; 3]; let mut amx = [f32::MIN; 3];
        for i in 0..8 { let p = to_world([if i & 1 != 0 { xm.maxs[0] } else { xm.mins[0] }, if i & 2 != 0 { xm.maxs[1] } else { xm.mins[1] }, if i & 4 != 0 { xm.maxs[2] } else { xm.mins[2] }]); for k in 0..3 { amn[k] = amn[k].min(p[k]); amx[k] = amx[k].max(p[k]); } }
        let mut e = 0f32; for k in 0..3 { e = e.max((amn[k] - sm.absmin[k]).abs()).max((amx[k] - sm.absmax[k]).abs()); } worst = worst.max(e); errs.push(e);
        sm_used += 1;
        for (mn, mx) in boxes {
            let size = [mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]];
            if size.iter().any(|&s| s <= 0.0) || size.iter().any(|&s| s > 4000.0) { continue; }
            let corner = |i: usize| -> [f32; 3] { to_world([if i & 1 != 0 { mx[0] } else { mn[0] }, if i & 2 != 0 { mx[1] } else { mn[1] }, if i & 4 != 0 { mx[2] } else { mn[2] }]) };
            for q in [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]] {
                for tri in [[q[0], q[2], q[1]], [q[0], q[3], q[2]]] {
                    let mut t = [0f32; 9];
                    for v in 0..3 { let p = corner(tri[v]); t[v * 3] = p[0]; t[v * 3 + 1] = p[1]; t[v * 3 + 2] = p[2]; }
                    tris.push((t, box_mat, 2)); sm_n += 1;
                }
            }
        }
    }
    errs.sort_by(|a, b| a.partial_cmp(b).unwrap()); let pct = |p: f32| errs.get(((errs.len() as f32 - 1.0) * p) as usize).copied().unwrap_or(0.0);
    println!("static models placed {sm_used}, bounds mismatch median {:.1} p90 {:.1}", pct(0.5), pct(0.9));
    println!("static models placed {sm_used}, largest bounds mismatch vs absmin/absmax {worst:.1} units");
    // world-spanning triangles (the sea plane, the outer shells) break the H1 collision tree: drop edges over 16000
    let before = tris.len();
    tris.retain(|(t, _, _)| { let e = |i: usize, j: usize| ((t[i*3]-t[j*3]).powi(2) + (t[i*3+1]-t[j*3+1]).powi(2) + (t[i*3+2]-t[j*3+2]).powi(2)).sqrt(); e(0,1).max(e(1,2)).max(e(2,0)) <= 16000.0 });
    println!("dropped {} world-spanning triangles", before - tris.len());
    // Default (COL_FULL unset): players only care about solid and player clip; write every kept triangle as plain solid
    // (contents 1): with Black Ops II contents passed through (player clip 0x10000, bullet-only 0x2080, water...) H1
    // players fell through everything, solid included
    // and leave out bullet-only clip (0x2000 without 0x1/0x10000) and water/nodraw volumes without player bits
    if std::env::var("COL_FULL").is_err() {
        let keep: Vec<bool> = mats.iter().map(|m| m.2 & 0x10001 != 0).collect();
        let before = tris.len();
        tris.retain(|(_, m, _)| keep[*m as usize]);
        for m in mats.iter_mut() { m.2 = if m.2 & 0x10001 != 0 { 1 } else { 0 }; }
        println!("solid-only: kept {} of {} triangles as solid", tris.len(), before);
    }
    // degenerate triangles out
    tris.retain(|(t, _, _)| { let a = [t[3]-t[0], t[4]-t[1], t[5]-t[2]]; let b = [t[6]-t[0], t[7]-t[1], t[8]-t[2]]; let c = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]; c[0]*c[0]+c[1]*c[1]+c[2]*c[2] > 1e-3 });
    let mut b = b"BO2COL01".to_vec();
    b.extend((mats.len() as u32).to_le_bytes());
    for (n, sf, cf) in &mats { b.extend((n.len() as u16).to_le_bytes()); b.extend(n.as_bytes()); b.extend(sf.to_le_bytes()); b.extend(cf.to_le_bytes()); }
    b.extend((tris.len() as u32).to_le_bytes());
    for (t, m, src) in &tris { for f in t { b.extend(f.to_le_bytes()); } b.extend(m.to_le_bytes()); b.extend(src.to_le_bytes()); }
    std::fs::write(out.join(format!("{stem}.col")), &b).unwrap();
    println!("brushes over {max_brush} units skipped: {big_skipped}");
    println!("clip {}: verts {} tris {} partitions {} -> mesh tris {} (skipped {}), world brushes {} of {} -> {} tris, static models {} -> {} box tris, materials {}",
        c.name, c.verts.len(), c.tri_indices.len() / 3, c.partitions.len(), mesh_n, walk_skip, world_brushes.len(), c.brushes.len(), brush_n, c.static_models.len(), sm_n, mats.len());
}
