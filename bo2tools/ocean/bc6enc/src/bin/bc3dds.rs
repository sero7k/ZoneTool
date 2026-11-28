// RGBA8 png-raw (w h rgba bytes file) -> DX10 DDS BC3_UNORM_SRGB with full mip chain (box filter)
use intel_tex_2::bc3;
fn main(){
  let a:Vec<String>=std::env::args().collect();
  let w:u32=a[3].parse().unwrap(); let h:u32=a[4].parse().unwrap();
  let mut img=std::fs::read(&a[1]).unwrap();
  let (mut cw,mut ch)=(w,h); let mut data=Vec::new(); let mut levels=0u32;
  loop {
    let s=intel_tex_2::RgbaSurface{data:&img,width:cw,height:ch,stride:cw*4};
    if cw>=4 && ch>=4 { data.extend(bc3::compress_blocks(&s)); } else {
      let mut pad=vec![0u8;16*4]; for y in 0..4 { for x in 0..4 { let sx=x.min(cw-1); let sy=y.min(ch-1); for c in 0..4 { pad[((y*4+x)*4+c) as usize]=img[((sy*cw+sx)*4+c) as usize]; } } }
      data.extend(bc3::compress_blocks(&intel_tex_2::RgbaSurface{data:&pad,width:4,height:4,stride:16})); }
    levels+=1;
    if cw==1 && ch==1 { break; }
    let nw=(cw/2).max(1); let nh=(ch/2).max(1); let mut n=vec![0u8;(nw*nh*4) as usize];
    for y in 0..nh { for x in 0..nw { for c in 0..4 { let mut s=0u32; for dy in 0..2 { for dx in 0..2 { let sx=(x*2+dx).min(cw-1); let sy=(y*2+dy).min(ch-1); s+=img[((sy*cw+sx)*4+c) as usize] as u32; } } n[((y*nw+x)*4+c) as usize]=((s+2)/4) as u8; } } }
    img=n; cw=nw; ch=nh;
  }
  let mut o=Vec::new(); o.extend(b"DDS ");
  let hd:[u32;31]=[124,0x1|0x2|0x4|0x1000|0x20000|0x80000,h,w,(w/4).max(1)*16*(h/4).max(1),0,levels,0,0,0,0,0,0,0,0,0,0,0,32,4,u32::from_le_bytes(*b"DX10"),0,0,0,0,0,0x1000|0x400000|0x8,0,0,0,0];
  for v in hd { o.extend(v.to_le_bytes()); }
  for v in [78u32,3,0,1,0] { o.extend(v.to_le_bytes()); }
  o.extend(data); std::fs::write(&a[2],o).unwrap();
}
