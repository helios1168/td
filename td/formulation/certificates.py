"""Small fixed-evidence specifications, not territory optimizers.

F9.I / F9.S / F11.G / F11.R / F11.W / F142.P: certificate acceptance is the
conjunction of named evidence predicates. No predicate establishes evidence
that its caller did not supply. Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import pyomo.environ as pyo


def build_model(formulation, predicates):
    """Exact truth table for fixed evidence: accept iff every q[p] is true.

    The maximization objective is a test oracle only, not a map objective.
    Both accept=0 and accept=1 can be checked as fixed points.
    """
    m = pyo.ConcreteModel(name=formulation)
    m.P = pyo.Set(initialize=sorted(predicates))
    m.q = pyo.Param(m.P, initialize={k: int(v) for k, v in predicates.items()}, within=pyo.Binary)
    m.accept = pyo.Var(domain=pyo.Binary)
    m.necessary = pyo.Constraint(m.P, rule=lambda m, p: m.accept <= m.q[p])
    m.sufficient = pyo.Constraint(expr=m.accept >= sum(m.q[p] for p in m.P) - len(m.P) + 1)
    m.objective = pyo.Objective(expr=m.accept, sense=pyo.maximize)
    return m


def ifa_model(*, items, manhattan, verified=True, diagnostic=False, unexplained_failure=False,
              districts=(), rate=1.2519681558, mass_provenance=True, necks_measured=True):
    """items: (kind, side) where kind is piece/proved/unresolved/other/mass.

    Monetary comparison is exact real dollars, edges included (no rounding: $999,999,999.75
    is under the $1B floor). districts: (current mass, recorded_window); mass_provenance is
    the index's check that the saved masses match the ledger joined to the full extract.
    """
    q = dict(verified=verified, necks_measured=bool(necks_measured), nondiagnostic=not diagnostic,
             explained=not unexplained_failure, mass_provenance=bool(mass_provenance))
    for i, (kind, side) in enumerate(items):
        q[f'item_{i}'] = kind == 'mass' or (kind in ('piece', 'proved') and bool(set(side) & set(manhattan)))
    for j, (mass, window) in enumerate(districts):
        dollars = mass * rate * 1e6
        q[f'window_{j}'] = 1_000_000_000 <= dollars <= 1_437_500_000 and window not in ('under', 'over')
    return build_model('F9.I', q)


def ifa_ledger_model(*, owned_cells, extract_mass, saved, no_cell=(), **gate):
    """F9.I from cell-level evidence, independently of the production mass join.

    owned_cells: (ZIP, fine channel, district); extract_mass: (ZIP, fine) -> mass;
    saved: district -> (saved mass, window flag). A cell the extract lacks fails provenance unless it is
    a validated zero-mass NO_CELL territory cell (`no_cell`, ledger rows the extract lacks, mass 0);
    a NO_CELL cell the extract holds fails it too.
    """
    districts = {j for _, _, j in owned_cells if j}
    current = {j: sum(extract_mass.get((z, f), 0.0) for z, f, d in owned_cells if d == j)
               for j in districts}
    no_cell = set(no_cell)
    covered = all(((z, f) in extract_mass) != ((z, f) in no_cell) for z, f, j in owned_cells if j)
    matches = districts == set(saved) and all(
        abs(saved[j][0] - current[j]) <= max(1e-12, 1e-9 * max(abs(saved[j][0]), abs(current[j])))
        for j in districts)
    return ifa_model(**gate, mass_provenance=covered and matches,
                     districts=[(current[j], saved.get(j, (0.0, 'in'))[1]) for j in sorted(districts)])


def glue_model(*, zero_path, donor_nonempty, piece_containment, neck_containment,
               donor_resolved, recipient_fewer_pieces, recipient_neck_count):
    """A candidate path's acceptance after search; containment uses returned witnesses.

    This is not a specification of shortest-path search or all possible necks.
    """
    return build_model('F11.G', dict(zero_path=zero_path, donor_nonempty=donor_nonempty,
        piece_containment=piece_containment, neck_containment=neck_containment,
        donor_resolved=donor_resolved, recipient_fewer_pieces=recipient_fewer_pieces,
        recipient_neck_count=recipient_neck_count))


def assembly_model(*, gate_rc, m1_pass, windows, eligible, hard, breaches, warm=False, manhattan_pass=False,
                   reasons=None):
    """The final label: a completed gate (exit 0, or 1 for a failed M1), M1 accepted (raw pass on exit 0, or on
    exit 1 the item-side Manhattan adjudication `manhattan_pass`), every window, eligibility, shape.
    `windows` are exact (unrounded dollars, edges in). `eligible` is the scorer's flag and `reasons` its
    reasons (None: the flag stands alone). The adjudicated M1 replaces the scorer's raw-M1 reasons (`M1: ...`,
    not `M1: not checked`) and only those: any other reason, or a flag with no reason, still vetoes."""
    waived = reasons is not None and gate_rc == 1 and bool(manhattan_pass)
    if waived:
        rest = [r for r in reasons if not r.startswith('M1: ') or r.startswith('M1: not checked')]
        eligible = bool(eligible) or (bool(reasons) and not rest)
    return build_model('F11.W' if warm else 'F11.R', dict(gate_completed=gate_rc in (0, 1),
        m1=(gate_rc == 0 and bool(m1_pass)) or (gate_rc == 1 and bool(manhattan_pass)),
        windows=all(windows), eligible=eligible, shape=not hard or not breaches))


def provenance_model(*, source, campaign_source, same_metadata, same_settings, instance_matches):
    return build_model('F142.P', dict(source_present=bool(source), source_matches=source == campaign_source,
        metadata=same_metadata, settings=same_settings, instance=instance_matches))


def assembly_ledger_model(*, owned_cells, extract_mass, rates, bounds, no_cell=(), listed_districts=None, **gate):
    """F11.R/W with independently computed dollars, never production window flags.

    owned_cells: (ZIP, fine channel, district); bounds: district -> (lower, effective upper)
    in dollars, including an applicable whole-state cap supplied as the upper bound.
    no_cell contains validated zero-mass territory cells absent from the extract.
    Bounds and routing/whole-state classification are fixed evidence, not inferred here.
    listed_districts is the separately recorded district set; None uses the bounds' keys.
    District IDs are channel-qualified when multiple channels are present.
    """
    no_cell = set(no_cell)
    districts = {j for _, _, j in owned_cells if j}
    covered = all(((z, f) in extract_mass) != ((z, f) in no_cell)
                  for z, f, j in owned_cells if j)
    dollars = {j: sum(rates[f] * extract_mass.get((z, f), 0.0)
                      for z, f, d in owned_cells if d == j) for j in districts}
    listed = set(bounds) if listed_districts is None else set(listed_districts)
    windows = [covered, districts == set(bounds), districts == listed]
    windows += [bounds[j][0] is not None and bounds[j][0] <= dollars[j] <= bounds[j][1]
                for j in districts if j in bounds]
    model = assembly_model(windows=windows, **gate)
    model.J = pyo.Set(initialize=sorted(districts))
    model.D = pyo.Param(model.J, initialize=dollars)
    return model


def scorer_ifa_model(*, cells, districts, average, audit_ok=True, m1_pass=True,
                     rate=1.2519681558e6):
    """F9.S: fixed IFA ledger cells (ZIP, state, district, mass), independent dollar gate.

    `audit_ok` excludes the informational band row; raw M1 and the whole-extract
    average remain separate eligibility predicates. This is not an M1 solver.
    `districts` is the scorer's supplied district table (not inferred coverage).
    """
    states = {j: {s for z, s, d, mass in cells if d == j} for j in districts}
    owners = {s: {d for z, st, d, mass in cells if st == s and d}
              for z, s, d, mass in cells}
    dollars = {j: sum(mass * rate for z, s, d, mass in cells if d == j) for j in districts}
    whole = {j: bool(states[j]) and all(owners[s] == {j} for s in states[j]) for j in districts}
    q = dict(audit=bool(audit_ok), m1=bool(m1_pass), average=1_125_000_000 <= round(average) <= 1_375_000_000)
    for j in districts:
        upper_exempt = whole[j] and states[j] == {'MD', 'DE', 'WV'}
        q[f'window_{j}'] = dollars[j] >= 1e9 and (dollars[j] <= 1.4375e9 or upper_exempt)
    model = build_model('F9.S', q)
    model.J = pyo.Set(initialize=sorted(districts))
    model.D = pyo.Param(model.J, initialize=dollars)
    model.whole = pyo.Param(model.J, initialize={j: int(whole[j]) for j in districts})
    return model
