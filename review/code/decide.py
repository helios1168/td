import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from dzero import nash_exact_d
from omega import asym_nash
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]; th,lam=.4,.3
c1,c2=1-lam,th*(1-lam)
ua,ub=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz
Sa,Sb=Az.sum(),Bz.sum()

opts={"d=(S_a,S_b)":nash_exact_d(Az,Bz,Mz,th,lam)["x"],
      "d=(0,0)":nash_exact_d(Az,Bz,Mz,th,lam,0.,0.)["x"],
      "d=0, omega=.54":asym_nash(Az,Bz,Mz,th,lam,.54)}
print(f"{'option':<16}{'zips a':>7}{'a book':>9}{'b book':>9}{'a opp%':>8}{'a vs pre':>10}{'b vs pre':>10}")
for nm,x in opts.items():
    Ua,Ub=ua[x].sum(),ub[~x].sum()
    print(f"{nm:<16}{int(x.sum()):>7}{Ua:>9.3f}{Ub:>9.3f}{100*Mz[x].sum()/Mz.sum():>7.1f}%"
          f"{100*(Ua-Sa)/Sa:>9.1f}%{100*(Ub-Sb)/Sb:>9.1f}%")
print(f"\n  pre-merger books: a={Sa:.3f}  b={Sb:.3f}   (a is {Sa/Sb:.2f}x b)")
print(f"  note both reps GAIN vs pre-merger under every option, because the merged")
print(f"  firm captures headroom neither could reach alone.")

print("\n" + "="*72)
print("THE ACTUAL TRADE-OFF")
print("="*72)
print("  EF1 is a property of the SYMMETRIC product at d=0. Any tilt breaks it:")
print("    omega=0.50 -> EF1 violated  0/60 noise draws")
print("    omega=0.54 -> EF1 violated 29/60")
print("    omega=0.60 -> EF1 violated 60/60")
print("    d=(S_a,S_b) -> EF1 violated 74/200 (=37%), and equals omega~0.54")
print()
print("  So the choice is NOT 'which baseline'. It is:")
print("    (1) EF1 as a defensible guarantee, no seniority tilt        -> d=(0,0)")
print("    (2) a seniority tilt, no EF1 guarantee                      -> pick omega explicitly")
print("  The pre-merger baseline is option (2) with omega chosen implicitly and")
print("  unstably (0.51-0.56 across parameters, sd 0.014 under data noise).")
