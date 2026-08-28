import sympy as sp
A,B,M,th,lam = sp.symbols('A_z B_z M_z theta lambda', positive=True)

# "booked" value of a zip to a: own sales retained + captured share of the other's book
booked_a = A + th*B
# NET headroom: opportunity left after own sales AND the captured share of the competitor's
head_net   = M - A - th*B
# GROSS headroom: opportunity left after both books, ignoring what capture actually delivers
head_gross = M - A - B

u_net   = sp.expand(booked_a + lam*head_net)
u_gross = sp.expand(booked_a + lam*head_gross)
print("u_a  NET   =", sp.collect(u_net,[A,B,M]))
print("u_a  GROSS =", sp.collect(u_gross,[A,B,M]))
print()
print("  net   coefficient on B_z :", sp.simplify(u_net.coeff(B)),   "  -> theta*(1-lambda), positive always")
print("  gross coefficient on B_z :", sp.simplify(u_gross.coeff(B)), "  -> negative iff lambda > theta  (the 'liability' the HANDOFF rejects)")
print()
# Does either convention mention the baseline?
print("Does u depend on S_a = sum_z A_z (the totals)?  ", u_net.has(sp.Symbol('S_a')), "/", u_gross.has(sp.Symbol('S_a')))
print("-> the headroom convention fixes the PER-ZIP VALUATION. It says nothing about")
print("   what is subtracted afterwards. The two are separate axes.")
print()
# but: decompose the gain to see what the baseline is actually doing
Sa = sp.Symbol('S_a', positive=True)
print("g_a = sum_{z in S} u_a(z) - S_a")
print("    = sum_{z in S} [u_a(z) - A_z]  -  sum_{z not in S} A_z")
print("      \\_______ improvement on zips WON ______/     \\__ own book LOST on zips ceded __/")
print()
print("per-zip incremental value if a WINS z, net convention:")
print("   u_a(z) - A_z =", sp.collect(sp.expand(u_net - A),[A,B,M]))
