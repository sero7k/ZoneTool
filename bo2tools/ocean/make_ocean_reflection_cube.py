import numpy as np, subprocess, sys, texture2ddecoder as t
from PIL import Image
N=1024
a=np.load('ldr_faces.npy')[...,:3].astype(np.float32)/255
F=np.stack([np.asarray(Image.fromarray((f*255).astype(np.uint8)).resize((N,N),Image.BICUBIC)).astype(np.float32)/255 for f in a])
u=(np.arange(N)+0.5)/N*2-1; U,V=np.meshgrid(u,u); one=np.ones_like(U)
D=np.stack([np.stack([one,-V,-U],-1),np.stack([-one,-V,U],-1),np.stack([U,one,V],-1),np.stack([U,-one,-V],-1),np.stack([U,-V,one],-1),np.stack([-U,-V,-one],-1)])
D/=np.linalg.norm(D,axis=-1,keepdims=True)
lin=np.clip(F/0.52,0,1)**2.2
warm=(lin[...,0]-lin[...,2])*lin.mean(-1)*(D[...,2]>0)*(D[...,2]<0.3)
sun=np.array([0.40213463,0.8244982,0.39810872]); sun/=np.linalg.norm(sun)
g=lin.mean(-1,keepdims=True); lin=g+(lin-g)*0.45          # desaturate (the in-game sky is fog-tinted)
lin*=float(sys.argv[1]) if len(sys.argv)>1 else 1.0
z=D[...,2:3]; w=np.where(z>=-0.02,np.exp(-np.clip(z,0,1)/0.08),0)*0.6
lin=lin*(1-w)+np.array([0.62,0.55,0.50])*w
c=np.clip((D*sun).sum(-1),0,1)
lobe=(c**250*25+c**24*1.5)[...,None]*np.array([1.0,0.72,0.45])
lin=lin+lobe*(D[...,2:3]>-0.05)
print('mean',lin.mean(),'max',lin.max())
lin.astype('<f4').tofile('faces.f32')
subprocess.run(['bc6enc/target/release/bc6enc','faces.f32','faces.bc6',str(N)],check=True)
b=open('faces.bc6','rb').read()
fs=[np.frombuffer(t.decode_bc6(b[k*N*N:(k+1)*N*N],N,N),np.uint8).reshape(N,N,4)[:,:,[2,1,0]] for k in range(6)]
Image.fromarray(np.concatenate([f[::4,::4] for f in fs],1)).save('new_cube.png')
h=open('/mnt/user-data/uploads/mwr_game_files/dump/mp_cargoship/images/hdr_h1_sky_cargoshipocean_ft.h1Image','rb').read()
open('/mnt/user-data/outputs/hdr_h1_sky_cargoshipocean_ft.h1Image','wb').write(h[:-6291456]+b)
