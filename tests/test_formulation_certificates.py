"""Fixed-evidence specs versus production acceptance paths on 30-vertex maps.
Agent: modeler (openai-codex/gpt-6-astra).
"""
import json
import os
import tempfile

import pyomo.environ as pyo

from td import audit
from td.formulation import certificates as spec
from tests.test_contig_night import ifa_index
from tests.test_sealed import glue, sealed
from tests.test_bnc import bnc_report, _res, _gate, SRC


def _truth(model, expected):
    solver = pyo.SolverFactory('highs')
    solver.options.update({'mip_rel_gap': 0.0, 'mip_abs_gap': 0.0})
    result = solver.solve(model)
    assert result.solver.termination_condition == pyo.TerminationCondition.optimal
    assert pyo.value(model.objective) == int(expected)
    for value in (0, 1):
        model.accept.fix(value)
        result = solver.solve(model, load_solutions=False)
        want = pyo.TerminationCondition.optimal if value == int(expected) else pyo.TerminationCondition.infeasible
        assert result.solver.termination_condition == want


def _polygon():
    zs = [f'{10000+i}' for i in range(30)]
    edges = list(zip(zs, zs[1:]))
    return dict(vertices=zs, edges=edges, border=dict.fromkeys(edges, 30000.0),
                connectors=[], state=dict.fromkeys(zs, 'NY'), aland=dict.fromkeys(zs, 1e8))


def test_formulation_ifa_gate_items_and_windows_30():
    polygon = _polygon()
    zs = polygon['vertices']
    manhattan = {zs[0]}
    for variant in ('clean', 'manhattan', 'other_piece', 'coverage'):
        owner = {z: 'A' if i < 15 else 'B' for i, z in enumerate(zs)}
        if variant != 'clean':
            owner[zs[0]] = 'B'
        if variant == 'other_piece':
            owner[zs[2]] = 'B'
        cells = [audit.Cell(z, 'ifa', 'IFA', owner[z], 1.0) for z in zs
                 if not (variant == 'coverage' and z == zs[-1])]
        with ifa_index.recorded_sides() as sides:
            check = audit.check_m1(audit.Run(cells, {'IFA': audit.Channel(2)}, polygon=polygon, fine=('ifa',)))
        verdict = ifa_index.m1_verdict(check.status, check.summary, check.items, sides, manhattan)
        # Independently chosen piece sides, not derived from the production recorder.
        items = [] if variant == 'clean' else [('piece', {zs[0]})]
        if variant == 'other_piece':
            items.append(('piece', {zs[2]}))
        if variant == 'coverage':
            items.append(('other', set()))
        for mass in (900.0, 798.741, 1148.1922, (1000.0 - 0.25 / 1e6) / ifa_index.RATE):
            dist = {'A': {'m_rel': mass, 'window': 'in'}, 'B': {'m_rel': 900.0, 'window': 'in'}}
            over, under = ifa_index.window_verdict(dist)
            expected = verdict['passes'] and not (over or under)
            _truth(spec.ifa_model(items=items, manhattan=manhattan,
                                 districts=[(mass, 'in'), (900.0, 'in')]), expected)
    # Independently expected, not derived from production: $999,999,999.75 is under the $1B floor, and
    # $1,437,500,000.25 over the cap; neither is rounded into the window. Stale saved masses fail too.
    rate = ifa_index.RATE
    for dollars in (999_999_999.75, 1_437_500_000.25):
        mass = dollars / 1e6 / rate
        assert ifa_index.window_verdict({'A': {'m_rel': mass, 'window': 'in'}}) != ([], [])
        _truth(spec.ifa_model(items=[], manhattan=manhattan, districts=[(mass, 'in')]), False)
    _truth(spec.ifa_model(items=[], manhattan=manhattan, districts=[(900.0, 'in')]), True)
    _truth(spec.ifa_model(items=[], manhattan=manhattan, districts=[(900.0, 'in')], mass_provenance=False), False)
    # Unresolved Manhattan sides and diagnostics cannot be waived.
    for kind in ('proved', 'unresolved'):
        with ifa_index.recorded_sides() as sides:
            item = audit.neck_item('IFA', 'A', audit.Neck(1.0, (zs[0],), .1, .1, (), kind))
        for diagnostic in (None, {'label': 'diagnostic'}):
            actual = ifa_index.m1_verdict('fail', 'neck', [item], sides, manhattan, diagnostic)['passes']
            _truth(spec.ifa_model(items=[(kind, {zs[0]})], manhattan=manhattan,
                                 diagnostic=diagnostic is not None), actual)


def test_formulation_glue_resolved_donor_and_gap_adjacency_30():
    polygon = _polygon()
    zs = polygon['vertices']
    # A's two pieces need B's zero-mass bridge z1; B retains its connected tail.
    edges = [(zs[0], zs[1]), (zs[1], zs[2]), (zs[1], zs[3])] + list(zip(zs[3:], zs[4:]))
    polygon.update(edges=edges, border=dict.fromkeys(edges, 30000.0), gaps={(zs[0], zs[2]): 40.0})
    owner = {z: 'A' if i in (0, 2) else 'B' for i, z in enumerate(zs)}
    mass = {z: 0.0 if i == 1 else 1.0 for i, z in enumerate(zs)}
    for gap in (False, True):
        adj = glue.gate_adjacency(polygon, gap_width=gap)
        assert (zs[2] in adj[zs[0]]) == gap
        for unresolved in (False, True):
            # The same returned side before/after used to erase an unresolved status.
            def necks(held):
                if zs[3] not in held:
                    return []
                return [glue.UnresolvedNeck({zs[3]})] if unresolved else []
            after, report = glue.glue_channel(owner, adj, mass, necks)
            accepted = bool(report['moved'])
            _truth(spec.glue_model(zero_path=True, donor_nonempty=True, piece_containment=True,
                neck_containment=True, donor_resolved=not unresolved, recipient_fewer_pieces=not gap,
                recipient_neck_count=True), accepted)
            assert sum(mass[z] for z in zs if owner[z] == 'A') == sum(mass[z] for z in zs if after[z] == 'A')


def test_formulation_assembly_gate_and_full_extract_30():
    polygon = _polygon()
    zs = polygon['vertices']
    for mass in (849.9, 900.0):
        ledger = [dict(zip_code=z, current_channel='wh', state='NY', model_channel='WH',
                       district='A', m_rel=mass / 30) for z in zs]
        rows = sealed.score.dollar_gate(ledger, [{'channel': 'WH', 'district': 'A'}], {'wh': 1e6})
        normalized = [{**r, **{k: r[k] / 1e6 if r[k] is not None else None
                              for k in ('usd', 'lo', 'hi', 'cap')}} for r in rows]
        for rc in (0, 1, None):
            for warm in (False, True):
                actual = sealed.label_point({'status': 'pass', 'summary': 'ok'}, normalized, [], False, gate_rc=rc)[0]
                _truth(spec.assembly_model(gate_rc=rc, m1_pass=True, windows=[r['ok'] for r in rows],
                    eligible=True, hard=False, breaches=[], warm=warm), actual == 'passes')
    # A gate that exited 1 passes only through the item-side adjudication; 2 and None never complete.
    ok = {'status': 'fail', 'summary': '1 necks'}
    for verdict in ({'passes': True, 'excepted': [('n', ['10001'])], 'blocking': []},
                    {'passes': False, 'excepted': [], 'blocking': ['an item outside Manhattan']}):
        for rc in (0, 1, 2, None):
            actual = sealed.label_point(ok, normalized, [], False, gate_rc=rc, verdict=verdict)[0] == 'passes'
            _truth(spec.assembly_model(gate_rc=rc, m1_pass=False, windows=[True], eligible=True, hard=False,
                breaches=[], manhattan_pass=verdict['passes']), actual)
    chain = sealed.point_chain('p', '/p', [(('NY',), '/f')], '/spec', '/full', None, dict(sealed.CAPS))
    command = next(c for s, c, _, _ in chain if s == 'score')
    assert command[-2:] == ['--extract', '/full']


def test_formulation_campaign_source_acceptance():
    import hashlib
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, 'instances'))
        body = b'fixed instance bytes for provenance-only test'
        with open(os.path.join(root, 'instances', 'S.json.gz'), 'wb') as fh:
            fh.write(body)
        sha = hashlib.sha256(body).hexdigest()
        for arm, source, finished in [('a', None, '01'), ('b', 'e' * 64, '02'), ('c', SRC, '03')]:
            os.makedirs(os.path.join(root, 'S', arm))
            row = dict(_res(arm, 'optimal', 1.0, _gate()), source_sha256=source,
                       instance_sha256=sha, finished=finished)
            with open(os.path.join(root, 'S', arm, 'result.json'), 'w') as fh:
                json.dump(row, fh)
        fresh, _ = bnc_report.split(root)
        admitted = {r['arm'] for r in fresh}
        for arm, source in [('a', None), ('b', 'e' * 64), ('c', SRC)]:
            _truth(spec.provenance_model(source=source, campaign_source=SRC, same_metadata=True,
                same_settings=True, instance_matches=True), arm in admitted)
