import sys; import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kaggle'))
from a007764_core import *

SW={EMPTY:EMPTY,OPEN:CLOSE,CLOSE:OPEN,MARK:MARK}
def mirror_w(s,W):   # mirror a profile word (length W slots, packed)
    xs=word_to_list(s,W); return list_to_word([SW[c] for c in reversed(xs)])

def run_row(vec,i,n,track):
    """vec: {packed profile u (len n+1): value}. returns next-row vec, or scalar at last row."""
    W=n+2; full=(1<<2*W)-1
    layer={ (u<<2):v for u,v in vec.items() }       # prepend EMPTY left plug
    for j in range(n+1):
        nx={}
        for s,v in layer.items():
            for t in successors(s,i,j,n):
                nx[t]=nx.get(t,0)+v
        layer={k:v for k,v in nx.items() if v}
        track.append(len(layer))
    if i==n: return layer.get(0,0)
    out={}
    for s,v in layer.items():
        if get_slot(s,n+1): continue
        u=s & ((1<<2*(n+1))-1)                       # slots 0..n = next profile
        out[u]=out.get(u,0)+v
    return {k:v for k,v in out.items() if v}

def first_row(n):
    layer={0:1}; W=n+2
    for j in range(n+1):
        nx={}
        for s,v in layer.items():
            for t in successors(s,0,j,n): nx[t]=nx.get(t,0)+v
        layer=nx
    return {s & ((1<<2*(n+1))-1):v for s,v in layer.items() if not get_slot(s,n+1)}

for n in range(3,10):
    L=n+1
    v0=first_row(n)
    keys=set(v0)|{mirror_w(u,L) for u in v0}
    vp={u: v0.get(u,0)+v0.get(mirror_w(u,L),0) for u in keys}   # 2 v+
    vm={u: v0.get(u,0)-v0.get(mirror_w(u,L),0) for u in keys}   # 2 v-
    res=[]; peaks=[]; bmax=[]; symok=True
    for vec,sign in ((vp,1),(vm,-1)):
        tr=[]; bm=0
        for i in range(1,n+1):
            vec=run_row(vec,i,n,tr)
            if i<n:
                bm=max(bm,len(vec))
                for u,v in vec.items():                    # boundary must stay (anti)symmetric
                    if vec.get(mirror_w(u,L),0)!=sign*v: symok=False
        res.append(vec); peaks.append(max(tr)); bmax.append(bm)
    a=(res[0]+res[1])//2
    trf=[]; vec=v0
    for i in range(1,n+1): vec=run_row(vec,i,n,trf)
    B=ProfileRanker(n).size
    print(f"n={n}: a+ + a- = a(n) {'OK' if a==KNOWN_A007764[n] else 'NG'} | boundary symmetry kept: {symok} | "
          f"B={B:6d}  boundary live(+run)={bmax[0]:6d}  "
          f"mid-row peak: full={max(trf):6d}  +run={peaks[0]:6d}  -run={peaks[1]:6d}")
