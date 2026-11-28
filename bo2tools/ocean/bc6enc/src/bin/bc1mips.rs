// RGBA8 raw (w h) -> BC1 blocks for the full mip chain down to 1x1 (raw, no header)
use intel_tex_2::bc1;
fn main(){
  let a:Vec<String>=std::env::args().collect();
  let w:u32=a[3].parse().unwrap(); let h:u32=a[4].parse().unwrap(); let maxl:u32=a[5].parse().unwrap();
  let mut img=std::fs::read(&a[1]).unwrap(); let (mut cw,mut ch)=(w,h); let mut data=Vec::new();
  for _ in 0..maxl {
    if cw>=4 && ch>=4 { data.extend(bc1::compress_blocks(&intel_tex_2::RgbaSurface{data:&img,width:cw,height:ch,stride:cw*4})); } else {
      let mut pad=vec![0u8;64]; for y in 0..4u32 { for x in 0..4u32 { let sx=x.min(cw-1); let sy=y.min(ch-1); for c in 0..4 { pad[((y*4+x)*4+c) as usize]=img[((sy*cw+sx)*4+c) as usize]; } } }
      data.extend(bc1::compress_blocks(&intel_tex_2::RgbaSurface{data:&pad,width:4,height:4,stride:16})); }
    if cw==1 && ch==1 { break; }
    let nw=(cw/2).max(1); let nh=(ch/2).max(1); let mut n=vec![0u8;(nw*nh*4) as usize];
    for y in 0..nh { for x in 0..nw { for c in 0..4 { let mut s=0u32; for dy in 0..2 { for dx in 0..2 { s+=img[(((y*2+dy).min(ch-1)*cw+(x*2+dx).min(cw-1))*4+c) as usize] as u32; } } n[((y*nw+x)*4+c) as usize]=((s+2)/4) as u8; } } }
    img=n; cw=nw; ch=nh;
  }
  std::fs::write(&a[2],data).unwrap();
}
