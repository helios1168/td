"""Small fixed-evidence specifications, not territory optimizers.

F9.I / F11.G / F11.R / F11.W / F142.P: certificate acceptance is the
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
              districts=(), rate=1.2519681558, mass_provenance=True):
    """items: (kind, side) where kind is piece/proved/unresolved/other/mass.

    Monetary comparison is exact real dollars, edges included (no rounding: $999,999,999.75
    is under the $1B floor). districts: (current mass, recorded_window); mass_provenance is
    the index's check that the saved masses match the ledger joined to the full extract.
    """
    q = dict(verified=verified, nondiagnostic=not diagnostic, explained=not unexplained_failure,
             mass_provenance=bool(mass_provenance))
    for i, (kind, side) in enumerate(items):
        q[f'item_{i}'] = kind == 'mass' or (kind in ('piece', 'proved') and bool(set(side) & set(manhattan)))
    for j, (mass, window) in enumerate(districts):
        dollars = mass * rate * 1e6
        q[f'window_{j}'] = 1_000_000_000 <= dollars <= 1_437_500_000 and window not in ('under', 'over')
    return build_model('F9.I', q)


def glue_model(*, zero_path, donor_nonempty, piece_containment, neck_containment,
               donor_resolved, recipient_fewer_pieces, recipient_neck_count):
    """A candidate path's acceptance after search; containment uses returned witnesses.

    This is not a specification of shortest-path search or all possible necks.
    """
    return build_model('F11.G', dict(zero_path=zero_path, donor_nonempty=donor_nonempty,
        piece_containment=piece_containment, neck_containment=neck_containment,
        donor_resolved=donor_resolved, recipient_fewer_pieces=recipient_fewer_pieces,
        recipient_neck_count=recipient_neck_count))


def assembly_model(*, gate_rc, m1_pass, windows, eligible, hard, breaches, warm=False, manhattan_pass=False):
    """The final label: a completed gate (exit 0, or 1 for a failed M1), M1 accepted (raw pass on exit 0, or on
    exit 1 the item-side Manhattan adjudication `manhattan_pass`), every window, eligibility, shape."""
    return build_model('F11.W' if warm else 'F11.R', dict(gate_completed=gate_rc in (0, 1),
        m1=(gate_rc == 0 and bool(m1_pass)) or (gate_rc == 1 and bool(manhattan_pass)),
        windows=all(windows), eligible=eligible, shape=not hard or not breaches))


def provenance_model(*, source, campaign_source, same_metadata, same_settings, instance_matches):
    return build_model('F142.P', dict(source_present=bool(source), source_matches=source == campaign_source,
        metadata=same_metadata, settings=same_settings, instance=instance_matches))
