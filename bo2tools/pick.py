import sys, numpy as np, math, struct
sys.path.insert(0,'/home/claude/carrier_look'); from h1map import H1Map
m=H1Map(sys.argv[1]); cam=np.array([float(x) for x in sys.argv[2:5]])
rays=[(float(a),float(b)) for a,b in zip(sys.argv[5::2],sys.argv[6::2])]
b=m.b; V=np.frombuffer(b,dtype=np.uint8,count=m.nverts*52,offset=m.vert_off).reshape(-1,52)
P=V[:,:12].copy().view('<f4').reshape(-1,3)
I=np.frombuffer(b,dtype='<u2',count=m.nidx,offset=m.idx_off)
for yaw,pitch in rays:
  d=np.array([math.cos(math.radians(pitch))*math.cos(math.radians(yaw)),math.cos(math.radians(pitch))*math.sin(math.radians(yaw)),-math.sin(math.radians(pitch))])
  best=(1e9,None)
  for si,s in enumerate(m.surfs):
    mat,vb,nvv,ib,nt=s[:5]
    lo=np.array(s[5:8]);hi=np.array(s[8:11])
    if np.any(lo-cam>30000) or np.any(cam-hi>30000): continue
    idx=I[ib:ib+nt*3].astype(np.int64)+vb
    if len(idx)==0 or idx.max()>=len(P): continue
    t=P[idx].reshape(-1,3,3); e1=t[:,1]-t[:,0]; e2=t[:,2]-t[:,0]
    h=np.cross(d,e2); a=(e1*h).sum(1); ok=np.abs(a)>1e-8; f=np.where(ok,1/np.where(ok,a,1),0)
    sv=cam-t[:,0]; u=f*(sv*h).sum(1); q=np.cross(sv,e1); v=f*(q*d).sum(1); tt=f*(e2*q).sum(1)
    hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(tt>1)
    if hit.any():
      k=tt[hit].min()
      if k<best[0]: best=(k,(si,m.mats[mat],(cam+d*k).round(0).tolist()))
  print(yaw,pitch,best)
