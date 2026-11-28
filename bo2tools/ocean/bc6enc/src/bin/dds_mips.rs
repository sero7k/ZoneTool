// RGBA8 raw (w h) -> DX10 DDS with full mip chain (box filter): format 72 BC1_UNORM_SRGB, 78 BC3_UNORM_SRGB, 83 BC5_UNORM (R,G), 61 R8_UNORM (R, uncompressed)
use intel_tex_2::{bc1, bc3, bc5};
fn enc(fmt: u32, img: &[u8], w: u32, h: u32) -> Vec<u8> {
    if fmt == 61 { return img.chunks(4).map(|p| p[0]).collect(); }
    let (mut buf, cw, ch) = if w >= 4 && h >= 4 { (img.to_vec(), w, h) } else {
        let mut pad = vec![0u8; 64]; for y in 0..4u32 { for x in 0..4u32 { let sx = x.min(w - 1); let sy = y.min(h - 1); for c in 0..4 { pad[((y * 4 + x) * 4 + c) as usize] = img[((sy * w + sx) * 4 + c) as usize]; } } } (pad, 4, 4) };
    match fmt {
        72 => bc1::compress_blocks(&intel_tex_2::RgbaSurface { data: &buf, width: cw, height: ch, stride: cw * 4 }),
        78 => bc3::compress_blocks(&intel_tex_2::RgbaSurface { data: &buf, width: cw, height: ch, stride: cw * 4 }),
        _ => { let rg: Vec<u8> = buf.chunks(4).flat_map(|p| [p[0], p[1]]).collect(); buf.clear(); bc5::compress_blocks(&intel_tex_2::RgSurface { data: &rg, width: cw, height: ch, stride: cw * 2 }) }
    }
}
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let w: u32 = a[3].parse().unwrap(); let h: u32 = a[4].parse().unwrap(); let fmt: u32 = a[5].parse().unwrap();
    let mut img = std::fs::read(&a[1]).unwrap(); let (mut cw, mut ch) = (w, h); let mut data = Vec::new(); let mut levels = 0u32;
    loop {
        data.extend(enc(fmt, &img, cw, ch)); levels += 1;
        if cw == 1 && ch == 1 { break; }
        let nw = (cw / 2).max(1); let nh = (ch / 2).max(1); let mut n = vec![0u8; (nw * nh * 4) as usize];
        for y in 0..nh { for x in 0..nw { for c in 0..4 { let mut s = 0u32; for dy in 0..2 { for dx in 0..2 { s += img[((((y * 2 + dy).min(ch - 1)) * cw + (x * 2 + dx).min(cw - 1)) * 4 + c) as usize] as u32; } } n[((y * nw + x) * 4 + c) as usize] = ((s + 2) / 4) as u8; } } }
        img = n; cw = nw; ch = nh;
    }
    let bs = if fmt == 72 { 8 } else { 16 };
    let pitch = if fmt == 61 { w } else { (w / 4).max(1) * bs * (h / 4).max(1) };
    let flags = if fmt == 61 { 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000 } else { 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000 };
    let mut o = Vec::new(); o.extend(b"DDS ");
    let hd: [u32; 31] = [124, flags, h, w, pitch, 0, levels, 0,0,0,0,0,0,0,0,0,0,0, 32, 4, u32::from_le_bytes(*b"DX10"), 0,0,0,0,0, 0x1000 | 0x400000 | 0x8, 0,0,0,0];
    for v in hd { o.extend(v.to_le_bytes()); }
    for v in [fmt, 3, 0, 1, 0] { o.extend(v.to_le_bytes()); }
    o.extend(data); std::fs::write(&a[2], o).unwrap();
}
