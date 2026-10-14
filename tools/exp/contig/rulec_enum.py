# Rule-C cluster enumeration at state grain (divisible pieces): which partitions of a state set into
# districts are arithmetically possible inside the IFA window [L, U] m_rel.
import json, itertools, sys, collections
L, U, F = 798.74, 1148.19, 1.2519681558
S = json.load(open('/tmp/iss/ifa/midwest/state_mrel.json'))
ADJ = json.load(open('/tmp/iss/ifa/midwest/state_adj.json'))
ADJ = {k: set(v) for k, v in ADJ.items()}
def connected(states):
    states = set(states); 
    if not states: return False
    seen = {next(iter(states))}; q = list(seen)
    while q:
        x = q.pop()
        for y in ADJ.get(x, ()):
            if y in states and y not in seen: seen.add(y); q.append(y)
    return seen == states
def cluster_options(sub):
    """(splits, K, description) for one cluster: whole district, or one split state + whole attachments."""
    out = []
    if connected(sub) and L <= sum(S[s] for s in sub) <= U:
        out.append((0, 1, '+'.join(sorted(sub))))
    for s in sub:
        rest = [x for x in sub if x != s]
        if not connected(sub): continue
        # components of rest that hang off s; each district = piece of s + a union of components
        comps = []; left = set(rest)
        while left:
            c = {left.pop()}; q = list(c)
            while q:
                x = q.pop()
                for y in ADJ.get(x, ()):
                    if y in left: left.discard(y); c.add(y); q.append(y)
            if not (ADJ.get(s, set()) & c): break
            comps.append(c)
        else:
            Ms = S[s]
            for n in range(2, 8):
                # assign comps to n districts (some districts may have none)
                found = None
                for assign in itertools.product(range(n), repeat=len(comps)):
                    W = [sum(S[x] for i, c in enumerate(comps) if assign[i] == d for x in c) for d in range(n)]
                    if any(w >= U for w in W): continue
                    lo = sum(max(L - w, 1e-6) for w in W); hi = sum(U - w for w in W)
                    if lo <= Ms <= hi:
                        groups = ['+'.join(sorted(x for i, c in enumerate(comps) if assign[i] == d for x in c)) for d in range(n)]
                        found = (1, n, f"{s}/{n}[" + ' | '.join(g or '-' for g in groups) + f"] slack {Ms-lo:.1f}/{hi-Ms:.1f}")
                        break
                if found: out.append(found)
    return out
def solve(states, top=8):
    states = sorted(states); idx = {s: i for i, s in enumerate(states)}
    opts = {}
    for r in range(1, len(states) + 1):
        for sub in itertools.combinations(states, r):
            o = cluster_options(sub)
            if o: opts[frozenset(sub)] = o
    res = []
    def rec(left, acc):
        if not left: res.append(list(acc)); return
        first = min(left, key=lambda s: idx[s])
        for sub, o in opts.items():
            if first in sub and sub <= left:
                for opt in o:
                    acc.append(opt); rec(left - sub, acc); acc.pop()
    rec(frozenset(states), [])
    res.sort(key=lambda p: (sum(x[0] for x in p), sum(x[1] - 1 for x in p if x[0]), -sum(x[1] for x in p)))
    return res
if __name__ == '__main__':
    states = sys.argv[1].split(',')
    res = solve(states)
    print(len(res), 'partitions for', ','.join(states))
    seen = set()
    for p in res[:int(sys.argv[2]) if len(sys.argv) > 2 else 12]:
        print(f"splits {sum(x[0] for x in p)} cuts {sum(x[1]-1 for x in p if x[0])} K {sum(x[1] for x in p)}: " + '; '.join(x[2] for x in p))
