//! bo2mp: a Black Ops II map's light grid colours. Writes `<out>/grid_colors.bin` (every colour set: 56 directions
//! of RGB8), `<out>/grid_entries.bin` (4 bytes each: colour index u16, primary light u8, needs-trace u8) and
//! `<out>/grid56.txt`: the 56-direction average over all grid entries ("r g b" 0..1 per line), the input for a
//! directional H1 light grid.
//!
//! `cargo run --release -p asset_t6 --example t6_grid_dump -- <mp_map.ff> <out dir>`
fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let zone = std::path::Path::new(&a[0]);
    let out = std::path::Path::new(&a[1]);
    std::fs::create_dir_all(out).ok();
    let cap = asset_t6::capture_zone(zone).expect("capture");
    let w = cap.world.as_ref().expect("world");
    let g = w.light_grid.as_ref().expect("light grid");
    std::fs::write(out.join("grid_colors.bin"), &g.colors).ok();
    std::fs::write(out.join("grid_entries.bin"), &g.entries).ok();
    std::fs::write(out.join("grid_coeffs.bin"), &g.coeffs).ok();
    let mut sv = String::new(); for v in &g.sky_volumes { sv += &format!("{:?} {:?} {:?} {} {} {}\n", v.mins, v.maxs, v.lighting_origin, v.colors_index, v.primary_light_index, v.visibility); } std::fs::write(out.join("sky_volumes.txt"), sv).ok();
    let sets = g.color_count as usize;
    let stride = g.colors.len() / sets.max(1);
    println!("grid mins {:?} maxs {:?} entries {} colour sets {} ({} bytes each) coeffs {}", g.mins, g.maxs, g.entries.len() / 4, sets, stride, g.coeff_count);
    let mut sum = vec![[0f64; 3]; 56];
    let mut n = 0f64;
    for e in g.entries.chunks_exact(4) {
        let ci = u16::from_le_bytes([e[0], e[1]]) as usize;
        if ci >= sets { continue; }
        let c = &g.colors[ci * stride..ci * stride + 168];
        for d in 0..56 {
            for k in 0..3 { sum[d][k] += c[d * 3 + k] as f64 / 255.0; }
        }
        n += 1.0;
    }
    let mut txt = String::new();
    for d in 0..56 {
        txt += &format!("{:.4} {:.4} {:.4}\n", sum[d][0] / n.max(1.0), sum[d][1] / n.max(1.0), sum[d][2] / n.max(1.0));
    }
    std::fs::write(out.join("grid56.txt"), &txt).ok();
    print!("{txt}");
}
