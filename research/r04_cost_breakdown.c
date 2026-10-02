/* r04: where does one state-update spend its time?
 * Full single-prime sweep with the validated kernel, plus isolated timing
 * of unrank / successors / rank over the same index range. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../kaggle/a007764_kernel.h"

static u64 *Tt, *Mm, *Off; static int Ts;
static void tables(int n){
    int kmax=n+4; Ts=n+6;
    Tt=calloc((size_t)(n+5)*Ts,8); Mm=calloc(n+5,8); Off=calloc(n+2,8);
    Tt[0]=1;
    for(int r=1;r<=kmax;r++) for(int d=0;d<=kmax;d++){
        u64 v=Tt[(r-1)*Ts+d]+Tt[(r-1)*Ts+d+1]; if(d) v+=Tt[(r-1)*Ts+d-1]; Tt[r*Ts+d]=v; }
    for(int k=0;k<=kmax;k++) Mm[k]=Tt[k*Ts];
    u64 a=0; for(int x=0;x<=n;x++){Off[x]=a;a+=Mm[x]*Mm[n-x];} Off[n+1]=a;
}
static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+1e-9*t.tv_nsec;}

int main(int c,char**v){
    int n=atoi(v[1]); u32 p=2147483629u; tables(n);
    Tables tb={Tt,Mm,Off,n,Ts}; u64 B=Off[n+1], S=2*B;
    u32 *cur=calloc(S,4),*nxt=calloc(S,4); u64 out[2],u; u32 b;
    double t0=now(); u64 updates=0;
    cur[0]=cur[1]=1;
    for(int i=0;i<=n;i++){
        for(int j=(i?0:1);j<=n;j++){
            int fb=(j==0); u64 sz=fb?B:S;
            if(i==n&&j==n) goto done;
            memset(nxt,0,S*4);
            for(u64 x=0;x<sz;x++){ u32 val=cur[x]; if(!val) continue; updates++;
                u64 s=word_before(x,j,fb,&tb); int k=cell_successors(s,i,j,n,out);
                for(int t=0;t<k;t++){ word_contract(out[t],j,&u,&b);
                    u64 y=2*profile_rank(u,&tb)+b; u32 z=nxt[y]+val; if(z>=p)z-=p; nxt[y]=z; } }
            u32*q=cur;cur=nxt;nxt=q;
        }
        memset(nxt,0,S*4); for(u64 r=0;r<B;r++) nxt[r]=cur[2*r]; u32*q=cur;cur=nxt;nxt=q;
    }
done:;
    double full=now()-t0;
    /* isolated components at a mid-row column */
    int j=n/2; volatile u64 sink=0; u64 *W=malloc(S*8);
    t0=now(); for(u64 x=0;x<S;x++) W[x]=word_before(x,j,0,&tb); double tu=now()-t0;
    t0=now(); u64 nout=0; for(u64 x=0;x<S;x++){int k=cell_successors(W[x],1,j+1,n,out); nout+=k; for(int t=0;t<k;t++) sink+=out[t];} double ts=now()-t0;
    t0=now(); for(u64 x=0;x<S;x++){ int k=cell_successors(W[x],1,j+1,n,out); for(int t=0;t<k;t++){ word_contract(out[t],j+1,&u,&b); sink+=profile_rank(u,&tb);} } double tr=now()-t0-ts;
    printf("n=%2d  2B=%11llu  sweep %8.2fs  %6.1f ns/update  | per state: unrank %5.1f ns  succ %5.1f ns  rank %5.1f ns  (%.2f outputs/state)\n",
        n,(unsigned long long)S,full,1e9*full/updates,1e9*tu/S,1e9*ts/S,1e9*tr/S,(double)nout/S);
    return 0;
}
