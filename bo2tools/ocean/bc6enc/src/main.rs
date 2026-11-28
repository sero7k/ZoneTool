// raw f32 RGB faces (6 x N x N x 3, little endian) -> BC6H UF16 blocks, face after face
use intel_tex_2::bc6h;
fn main(){
  let a:Vec<String>=std::env::args().collect();
  let n:u32=a[3].parse().unwrap();
  let raw=std::fs::read(&a[1]).unwrap();
  let f:Vec<f32>=raw.chunks(4).map(|c|f32::from_le_bytes([c[0],c[1],c[2],c[3]])).collect();
  let mut out=Vec::new();
  let face=(n*n*3) as usize;
  for i in 0..6 {
    let mut rgba=Vec::with_capacity((n*n*4) as usize*2);
    for p in 0..(n*n) as usize { for c in 0..3 { rgba.extend_from_slice(&half::f16::from_f32(f[i*face+p*3+c]).to_le_bytes()); } rgba.extend_from_slice(&half::f16::from_f32(1.0).to_le_bytes()); }
    let s=intel_tex_2::RgbaSurface{data:&rgba,width:n,height:n,stride:n*8};
    out.extend(bc6h::compress_blocks(&bc6h::very_fast_settings(),&s));
  }
  std::fs::write(&a[2],out).unwrap();
}
