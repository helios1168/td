import sys, itertools, math
from fractions import Fraction
sys.path.insert(0,"/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import maxweight, blocking_pairs
import numpy as np
from scipy.optimize import linear_sum_assignment
PH={"raw":lambda x:Fraction(x),"log":lambda x:math.log(x)}
res={w:[0,0,0] for w in PH}   # [all-block, any-block, scipy-block]
tot=0
for cells in itertools.product(range(1,7),repeat=6):
    g=[list(cells[r*2:(r+1)*2]) for r in range(3)]
    tot+=1
    a=np.array(g,float)
    for w,phi in PH.items():
        R,_=maxweight(g,phi)
        bl=[bool(blocking_pairs(g,s)) for s in R]
        res[w][0]+=all(bl); res[w][1]+=any(bl)
        C = a if w=="raw" else np.log(a)
        r,c=linear_sum_assignment(C.T,maximize=True)   # rows=districts
        s=[0,0]
        for rr,cc in zip(r,c): s[rr]=cc
        res[w][2]+=bool(blocking_pairs(g,tuple(s)))
print("total",tot)
for w in PH: print(w,"all-argmax-block=%d  any-argmax-block=%d  scipy-tiebreak=%d"%tuple(res[w]))
