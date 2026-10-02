/* r06: incremental ranking.
 *  - automaton lexicographic ranking (r05) instead of the MARK-split formula
 *  - input side: walk indices in rank order, advance the word like an odometer
 *  - output side: O(1) local rank delta unless the vertex rewrites a partner
 * Validated against the known OEIS residues; timed against r04's baseline. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../kaggle/a007764_kernel.h"

static int n, L; static u64 *Ca;                        /* Ca[(rem*(L+2)+d)*2+m] */
#define CA(rem,d,m) Ca[((size_t)(rem)*(L+2)+(d))*2+(m)]

static inline int step(u32 c, int d, int m, int *nd, int *nm){
    if (c == A_EMPTY) { *nd=d; *nm=m; return 1; }
    if (c == A_OPEN)  { *nd=d+1; *nm=m; return d+1 <= L; }
    if (c == A_CLOSE) { if (!d) return 0; *nd=d-1; *nm=m; return 1; }
    if (m || d) return 0; *nd=0; *nm=1; return 1;
}
static inline u64 contrib(u32 c, int d, int m, int rem){
    u64 t = 0; int nd, nm;
    for (u32 c2 = 0; c2 < c; c2++) if (step(c2,d,m,&nd,&nm)) t += CA(rem,nd,nm);
    return t;
}
static u64 rank_full(u64 w){
    int d=0,m=0,nd,nm; u64 r=0;
    for (int k=0;k<L;k++){ u32 c=slot_get(w,k); r+=contrib(c,d,m,L-k-1); step(c,d,m,&nd,&nm); d=nd; m=nm; }
    return r;
}
typedef struct { u64 w; int D[34], Mk[34]; u64 r; } Odo;   /* D/Mk[k] = state before pos k */
static void odo_set(Odo *o, u64 r){
    int d=0,m=0,nd,nm; o->w=0; o->r=r;
    for (int k=0;k<L;k++){
        o->D[k]=d; o->Mk[k]=m; int rem=L-k-1;
        for (u32 c=0;c<4;c++){ if(!step(c,d,m,&nd,&nm)) continue; u64 cnt=CA(rem,nd,nm);
            if (r<cnt){ o->w|=(u64)c<<(2*k); d=nd; m=nm; break; } r-=cnt; }
    }
    o->D[L]=d; o->Mk[L]=m;
}
static u64 odo_moves;
static void odo_next(Odo *o){
    int nd,nm;
    for (int k=L-1;k>=0;k--){
        u32 c=slot_get(o->w,k);
        for (u32 c2=c+1;c2<4;c2++){
            if(!step(c2,o->D[k],o->Mk[k],&nd,&nm) || !CA(L-k-1,nd,nm)) continue;
            o->w=slot_set(o->w,k,c2); int d=nd,m=nm;
            for (int q=k+1;q<L;q++){
                o->D[q]=d; o->Mk[q]=m;
                for (u32 c3=0;c3<4;c3++) if(step(c3,d,m,&nd,&nm) && CA(L-q-1,nd,nm)){ o->w=slot_set(o->w,q,c3); d=nd; m=nm; break; }
            }
            o->D[L]=d; o->Mk[L]=m; o->r++; odo_moves += L-k; return;
        }
    }
}
static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+1e-9*t.tv_nsec;}

int main(int argc, char **argv){
    n=atoi(argv[1]); L=n+1; u32 p=2147483629u;
    Ca=calloc((size_t)(L+1)*(L+2)*2,8); CA(0,0,1)=1;
    for(int rem=1;rem<=L;rem++) for(int d=0;d<=L;d++) for(int m=0;m<2;m++){
        int nd,nm; u64 v=0; for(u32 c=0;c<4;c++) if(d+1<=L+1 && step(c,d,m,&nd,&nm) && nd<=L) v+=CA(rem-1,nd,nm); CA(rem,d,m)=v; }
    u64 B=CA(L,0,0), S=2*B;
    u32 *cur=calloc(S,4), *nxt=calloc(S,4); u64 out[2], u2; u32 b2;
    u64 updates=0, joins=0; double t0=now(); Odo o; u64 answer=0;
    /* seed: (0,0) emits MARK down / right; contracted profile = M then EMPTYs */
    u64 r0 = rank_full((u64)A_MARK); cur[2*r0]=1; cur[2*r0+1]=1;
    for (int i=0;i<=n;i++){
        for (int j=(i?0:1); j<=n; j++){
            int fb=(j==0); int term=(i==n&&j==n);
            if(!term) memset(nxt,0,S*4);
            odo_set(&o,0);
            u64 nr = fb ? B : B;                         /* profiles to walk */
            for (u64 r=0; r<nr; r++, (r<nr ? odo_next(&o) : (void)0)){
                for (u32 b=0;b<(fb?1u:2u);b++){
                    u64 idx = fb ? r : 2*r+b; u32 val=cur[idx]; if(!val) continue; updates++;
                    u64 s = fb ? (o.w<<2) : word_expand(o.w,b,j-1);
                    u32 Lp=slot_get(s,j), Up=slot_get(s,j+1);
                    int isjoin = Lp && Up && !(Lp==A_OPEN && Up==A_CLOSE);
                    int k=cell_successors(s,i,j,n,out);
                    for(int t=0;t<k;t++){
                        if(term){ if(out[t]==0ull) answer=(answer+val)%p; continue; }
                        word_contract(out[t],j,&u2,&b2); u64 ro;
                        if (isjoin){ joins++; ro=rank_full(u2); }
                        else if (fb) ro=r;                    /* j=0: profile unchanged */
                        else {
                            int lo=j-1,d=o.D[lo],m=o.Mk[lo],nd,nm,rem=L-lo-1;
                            u64 pa=contrib(slot_get(o.w,lo),d,m,rem); step(slot_get(o.w,lo),d,m,&nd,&nm);
                            pa+=contrib(slot_get(o.w,j),nd,nm,rem-1);
                            u64 pb=contrib(slot_get(u2,lo),d,m,rem); step(slot_get(u2,lo),d,m,&nd,&nm);
                            pb+=contrib(slot_get(u2,j),nd,nm,rem-1);
                            ro=r-pa+pb;
                        }
                        u64 y=2*ro+b2; u32 z=nxt[y]+val; if(z>=p) z-=p; nxt[y]=z;
                    }
                }
            }
            if (term) goto done;
            u32*q=cur;cur=nxt;nxt=q;
        }
        memset(nxt,0,S*4); for(u64 r=0;r<B;r++) nxt[r]=cur[2*r]; u32*q=cur;cur=nxt;nxt=q;
    }
done:;
    double el=now()-t0;
    printf("n=%2d  a(n) mod p = %10llu  sweep %7.2fs  %6.1f ns/update  joins %.3f  odometer avg move %.2f slots\n",
        n,(unsigned long long)answer,el,1e9*el/updates,(double)joins/updates,(double)odo_moves/((double)B*(n+1)*(n+1)));
    return 0;
}
