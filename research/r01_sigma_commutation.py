import sys; import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kaggle'))
from a007764_core import *
import numpy as np

def profiles(n):
    P=ProfileRanker(n); return P,[P.unrank(r) for r in range(P.size)]

def mirror(u):
    sw={EMPTY:EMPTY,OPEN:CLOSE,CLOSE:OPEN,MARK:MARK}
    return [sw[c] for c in reversed(u)]

def row_transfer(n,i):
    """Matrix T[r',r]: profile r before row i -> profile r' before row i+1."""
    P,U=profiles(n); W=n+2; full=(1<<2*W)-1
    T=np.zeros((P.size,P.size),dtype=object)
    for r,u in enumerate(U):
        layer={list_to_word([EMPTY]+u):1}
        for j in range(n+1):
            nx={}
            for s,v in layer.items():
                for t in successors(s,i,j,n): nx[t]=nx.get(t,0)+v
            layer=nx
        for s,v in layer.items():
            if get_slot(s,n+1)!=EMPTY: continue
            t=(s<<2)&full
            w=word_to_list(t,W)[1:]       # profile before next row
            if MARK not in w: continue
            T[P.rank(w),r]+=v
    return P,U,T

for n in range(2,8):
    P,U,T=row_transfer(n,1)            # generic middle row
    S=np.zeros_like(T)
    for r,u in enumerate(U): S[P.rank(mirror(u)),r]=1
    comm = (T.dot(S)-S.dot(T))
    fixed=sum(1 for r,u in enumerate(U) if mirror(u)==u)
    dplus=(P.size+fixed)//2
    print(f"n={n}: B={P.size:5d}  ||TS-ST||max={max(abs(x) for x in comm.flat)}  "
          f"Sigma-fixed profiles={fixed:4d}  dim V+={dplus:5d} dim V-={P.size-dplus:5d}")
