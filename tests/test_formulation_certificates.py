"""Fixed-evidence specs versus production acceptance paths on 30-vertex maps.
Agent: modeler (openai-codex/gpt-6-astra).
"""
import csv
import json
import os
import tempfile

import pyomo.environ as pyo

from td import audit, data
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
        verdict = ifa_index.m1_verdict(check.status, check.summary, check.items, sides, manhattan, counts=check.counts)
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
            actual = ifa_index.m1_verdict('fail', 'neck', [item], sides, manhattan, diagnostic, counts={'necks': 1})['passes']
            _truth(spec.ifa_model(items=[(kind, {zs[0]})], manhattan=manhattan,
                                 diagnostic=diagnostic is not None), actual)


def test_formulation_ifa_current_ledger_mass_provenance_30():
    zs = _polygon()['vertices']
    base = [(z, 'ifa', 'A' if i < 15 else 'B') for i, z in enumerate(zs)]
    # Both districts start at mass 900. Moving one boundary cell keeps connectivity
    # and windows, but stale saved totals must prevent certification.
    mass = dict.fromkeys(((z, 'ifa') for z in zs), 60.0)
    saved = {'A': (900.0, 'in'), 'B': (900.0, 'in')}
    no_cell = audit.NO_CELL
    for variant in ('matching', 'moved', 'updated', 'missing_cell', 'missing_district', 'roundoff',
                    'no_cell_territory', 'no_cell_with_mass', 'no_cell_in_extract'):
        cells, extract, recorded = list(base), dict(mass), dict(saved)
        reason, m_rel, territory = {}, {}, set()
        if variant in ('moved', 'updated'):
            cells[14] = (zs[14], 'ifa', 'B')
        if variant == 'updated':
            recorded = {'A': (840.0, 'in'), 'B': (960.0, 'in')}
        if variant == 'missing_cell':
            del extract[zs[0], 'ifa']
        if variant == 'missing_district':
            del recorded['B']
        if variant == 'roundoff':
            recorded['A'] = (900.0 + 1e-8, 'in')
        if variant.startswith('no_cell'):
            # a footprint cell the extract lacks, owned at zero opportunity (`output.ledger`'s NO_CELL row);
            # its district keeps the other 14 cells' mass
            cells[0] = (zs[0], 'ifa', 'A')
            reason[zs[0], 'ifa'] = no_cell
            recorded['A'] = (840.0, 'in')
            if variant != 'no_cell_in_extract':
                del extract[zs[0], 'ifa']
            if variant == 'no_cell_with_mass':
                m_rel[zs[0], 'ifa'] = 0.5
            else:
                territory = {(zs[0], 'ifa')}
        ext = data.Extract(('ifa',), [z for z, f in extract], [f for z, f in extract],
                           list(extract.values()), [{} for _ in extract], [0.0 for _ in extract])
        ledger = [dict(zip_code=z, current_channel=f, district=j, reason=reason.get((z, f), ''),
                       m_rel=m_rel.get((z, f), 0.0 if (z, f) in reason else extract.get((z, f), 0.0)))
                  for z, f, j in cells]
        try:
            now = ifa_index.current_masses(ledger, ext)
            checked = ifa_index.checked_districts(
                {j: dict(m_rel=m, window=w) for j, (m, w) in recorded.items()}, now)
            over, under = ifa_index.window_verdict(checked)
            accepted = not (over or under)
        except ValueError:
            accepted = False
        assert accepted == (variant in ('matching', 'updated', 'roundoff', 'no_cell_territory')), variant
        _truth(spec.ifa_ledger_model(owned_cells=cells, extract_mass=extract, saved=recorded, no_cell=territory,
                                    items=[], manhattan=set()), accepted)


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
    # Real 30-vertex Manhattan-only gate evidence: the scorer's raw-M1 reason is replaced by the adjudication,
    # every other reason (and a flag with no reason) still vetoes, in the production label and in the spec.
    cells = [audit.Cell(z, 'wh', 'WH', 'B' if i == 0 or i >= 15 else 'A', 60.0)
             for i, z in enumerate(zs)]
    with ifa_index.recorded_sides() as sides:
        check = audit.check_m1(audit.Run(cells, {'WH': audit.Channel(2)}, polygon=polygon, fine=('wh',)))
    verdict = ifa_index.m1_verdict(check.status, check.summary, check.items, sides, {zs[0]}, counts=check.counts)
    assert check.status == 'fail' and verdict['passes']
    why = sealed.score.eligibility({'coverage': 'pass', audit.M1_CHECK: 'fail'}, check,
                                   {'WH': 48}, {}, m1=check, gate=[])
    duplicate = 'audit: M1 polygon contiguity fails'
    assert duplicate in why and any(w.startswith('M1: fail') for w in why)
    other = 'main K 47 outside 48-52'
    m1 = {'status': check.status, 'summary': check.summary}
    for reasons, flag in ((why, False), (why + [other], False), ([other], False), ([], False),
                          ([duplicate], False), (why + ['audit: coverage fails'], False),
                          (why + ['M1: not checked'], False), (['M1: not checked'], False), ([], True)):
        for warm in (False, True):
            for rc, v in ((1, verdict), (1, None), (0, verdict)):
                actual = sealed.label_point(m1 if rc else {'status': 'pass', 'summary': 'ok'}, normalized, [], False,
                                            eligible=flag, why=reasons, gate_rc=rc, verdict=v)[0] == 'passes'
                _truth(spec.assembly_model(gate_rc=rc, m1_pass=rc == 0, windows=[True], eligible=flag,
                                          hard=False, breaches=[], warm=warm,
                                          manhattan_pass=bool(v and v['passes']), reasons=reasons), actual)
    assert sealed.label_point(m1, normalized, [], False, eligible=False, why=why, gate_rc=1,
                              verdict=verdict) == ('passes', '')
    label, reason = sealed.label_point(m1, normalized, [], False, eligible=False, why=why + [other], gate_rc=1,
                                       verdict=verdict)
    assert label == 'ineligible' and reason == other
    # Exact windows on 30 vertices: $849,999,999.75 is under the $850M floor as the scorer's unrounded gate (#105) also reads it,
    # and $1,150,000,000.25 is over the ceiling of a district owning more than one state.
    for district_mass, want in ((849.99999975, False), (850.0, True), (900.0, True), (1150.0, True),
                                (1150.00000025, False)):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = [dict(zip_code=z, current_channel='wh', state='NY' if i % 2 else 'PA', model_channel='WH',
                           district='A' if i < 15 else 'B', reason='', m_rel=str(district_mass if i == 0 else 900.0 if i == 15 else 0.0))
                      for i, z in enumerate(zs)]
            for name, rows in (('ledger.csv', ledger), ('districts.csv', [dict(channel='WH', district='A'),
                                                                          dict(channel='WH', district='B')])):
                with open(os.path.join(tmp, name), 'w', newline='') as fh:
                    w = csv.DictWriter(fh, list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
            mass = {(r['zip_code'], 'wh'): float(r['m_rel']) for r in ledger}
            got = {r['district']: r for r in sealed.exact_rows(tmp, mass, {'wh': 1e6})}
            scored = {r['district']: r for r in sealed.score.dollar_gate(ledger, [{'channel': 'WH', 'district': 'A'},
                      {'channel': 'WH', 'district': 'B'}], {'wh': 1e6})}
            exact = sum(float(r['m_rel']) for r in ledger if r['district'] == 'A') * 1e6
            assert got['A']['ok'] == want == (0.85e9 <= exact <= 1.15e9), district_mass
            assert got['B']['ok'] and scored['B']['ok']
            if district_mass in (849.99999975, 1150.00000025):
                assert not scored['A']['ok']                 # the scorer compares unrounded dollars too (#105)
            rows = list(got.values())
            for warm in (False, True):
                actual = sealed.label_point({'status': 'pass', 'summary': 'ok'}, rows, [], False)[0] == 'passes'
                _truth(spec.assembly_ledger_model(
                    owned_cells=[(r['zip_code'], 'wh', r['district']) for r in ledger],
                    extract_mass=mass, rates={'wh': 1e6}, bounds={'A': (0.85e9, 1.15e9), 'B': (0.85e9, 1.15e9)},
                    gate_rc=0, m1_pass=True, eligible=True, hard=False, breaches=[], warm=warm), actual)
            # Stale ledger amounts must not replace full-extract masses in the production join.
            for r in ledger:
                r['m_rel'] = '0.0'
            with open(os.path.join(tmp, 'ledger.csv'), 'w', newline='') as fh:
                writer = csv.DictWriter(fh, list(ledger[0]))
                writer.writeheader()
                writer.writerows(ledger)
            assert sealed.exact_rows(tmp, mass, {'wh': 1e6}) == rows
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


def test_formulation_ifa_requires_measured_necks_30():
    polygon = _polygon()
    zs = polygon['vertices']
    cells = [audit.Cell(z, 'ifa', 'IFA', 'B' if i == 0 or i >= 15 else 'A', 60.0)
             for i, z in enumerate(zs)]
    for measured in (True, False):
        graph = dict(polygon)
        if not measured:
            del graph['border']
        with ifa_index.recorded_sides() as sides:
            check = audit.check_m1(audit.Run(cells, {'IFA': audit.Channel(2)}, polygon=graph, fine=('ifa',)))
        assert check.status == 'fail' and (check.counts['necks'] is not None) == measured
        for counts in (check.counts, {}, None):
            accepted = ifa_index.m1_verdict(check.status, check.summary, check.items, sides, {zs[0]},
                                           counts=counts)['passes']
            assert accepted == (measured and counts == check.counts)
            _truth(spec.ifa_model(items=[('piece', {zs[0]})], manhattan={zs[0]},
                                 necks_measured=measured and counts == check.counts), accepted)


def test_formulation_scorer_ifa_window_waiver_and_eligibility_30():
    score = sealed.score
    zs = _polygon()['vertices']
    # A owns 15 ZIPs across MD+DE+WV, B owns PA. Zero-dollar ownership still ends whole-state status.
    cases = [('lower_out', 1e9 - .25, False), ('lower', 1e9, True), ('upper', 1.4375e9, True),
             ('waiver', 1.4375e9 + .25, True), ('extra_state', 1.9e9, False),
             ('shared', 1.9e9, False), ('missing_state', 1.9e9, False)]
    for variant, dollars, expected in cases:
        cells = [(z, ('MD', 'DE', 'WV')[i % 3] if i < 15 else 'PA', 'A' if i < 15 else 'B',
                  dollars if i == 0 else 1.2e9 if i == 15 else 0.0) for i, z in enumerate(zs)]
        if variant == 'extra_state':
            z, _, j, m = cells[1]
            cells[1] = z, 'VA', j, m
        elif variant == 'shared':
            z, _, j, m = cells[-1]
            cells[-1] = z, 'MD', j, m
        elif variant == 'missing_state':
            cells = [(z, 'MD' if s == 'WV' else s, j, m) for z, s, j, m in cells]
        ledger = [dict(zip_code=z, state=s, district=j, m_rel=m, current_channel='ifa', model_channel='IFA')
                  for z, s, j, m in cells]
        rows = score.dollar_gate(ledger, [{'channel': 'IFA', 'district': j} for j in ('A', 'B')],
                                 {'ifa': 1.0}, score.IFA_WINDOW)
        assert all(r['ok'] for r in rows) == expected
        for average, m1_pass, audit_ok in ((1.25e9, True, True), (1.125e9 - .75, True, True),
                                           (1.375e9 + .75, True, True), (1.25e9, False, True),
                                           (1.25e9, True, False)):
            # The old symmetric band fails; a supplied district gate makes it informational.
            why = score.eligibility({'coverage': 'pass' if audit_ok else 'fail'},
                audit.Check(score.BAND_CHECK, 'fail', 'informational band'), {'IFA': 2}, {'IFA': average},
                audit.Check(audit.M1_CHECK, 'pass' if m1_pass else 'fail', ''), rows)
            _truth(spec.scorer_ifa_model(cells=cells, districts=['A', 'B'], rate=1.0, average=average,
                                        audit_ok=audit_ok, m1_pass=m1_pass), not why)
    # Same physical instance in native m_rel units, using the production IFA rate rather than $ units.
    cells = [(z, 'NY', 'A' if i < 15 else 'B', 900.0 if i in (0, 15) else 0.0) for i, z in enumerate(zs)]
    ledger = [dict(zip_code=z, state=s, district=j, m_rel=m, current_channel='ifa', model_channel='IFA')
              for z, s, j, m in cells]
    rows = score.dollar_gate(ledger, [{'channel': 'IFA', 'district': j} for j in ('A', 'B')],
                             score.IFA_RATES, score.IFA_WINDOW)
    _truth(spec.scorer_ifa_model(cells=cells, districts=['A', 'B'], average=1.25e9), all(r['ok'] for r in rows))


def test_formulation_scorer_district_table_precondition_30():
    from unittest.mock import patch

    score = sealed.score
    zs = _polygon()['vertices']
    cells = [(z, 'NY', 'A' if i < 15 else 'B', 900.0 if i in (0, 15) else 0.0)
             for i, z in enumerate(zs)]
    ledger = [dict(zip_code=z, state=s, district=j, m_rel=m, current_channel='ifa', model_channel='IFA')
              for z, s, j, m in cells]
    for listed in (['A', 'B'], ['A'], ['A', 'B', 'C']):
        districts = [dict(channel='IFA', district=j) for j in listed]
        try:
            score.check_districts(ledger, districts)
            rows = score.dollar_gate(ledger, districts, score.IFA_RATES, score.IFA_WINDOW)
            why = score.eligibility({'coverage': 'pass'}, audit.Check(score.BAND_CHECK, 'fail', ''),
                {'IFA': 2}, {'IFA': 1.25e9}, audit.Check(audit.M1_CHECK, 'pass', ''), rows)
            accepted = not why
        except ValueError as exc:
            assert 'different districts' in str(exc)
            accepted = False
        assert accepted == (listed == ['A', 'B'])
        _truth(spec.scorer_ifa_model(cells=cells, districts=listed, average=1.25e9), accepted)
        if not accepted:
            # Exercise the public scorer as well: mismatch must stop it before geometry or eligibility.
            with tempfile.TemporaryDirectory() as tmp:
                for name, rows in (('ledger.csv', ledger), ('districts.csv', districts)):
                    with open(os.path.join(tmp, name), 'w', newline='') as fh:
                        writer = csv.DictWriter(fh, list(rows[0]))
                        writer.writeheader()
                        writer.writerows(rows)
                with patch.object(score, 'channel_looks', side_effect=AssertionError('table guard bypassed')):
                    try:
                        score.score(tmp, g=object())
                    except ValueError as exc:
                        assert 'different districts' in str(exc)
                    else:
                        raise AssertionError('mismatched district table reached scoring')


def test_formulation_overnight_completed_gate_and_district_table_30():
    from tests.test_overnight import _FinalRunner, _final_folder, _evidence, overnight
    from unittest.mock import patch

    zs = _polygon()['vertices']
    for variant in ('clean', 'below', 'above', 'manhattan', 'unmeasured', 'crash', 'missing_gate', 'missing_district'):
        with tempfile.TemporaryDirectory() as tmp:
            extract, final = _final_folder(tmp)
            total_a = {'below': 849.99999975, 'above': 1150.00000025}.get(variant, 900.0)
            cells = [(z, 'wh', 'WH_01' if i < 15 else 'WH_02') for i, z in enumerate(zs)]
            mass = {(z, 'wh'): total_a if i == 0 else 900.0 if i == 15 else 0.0 for i, z in enumerate(zs)}
            # The extra off-map cell fixes the whole-extract conversion at $1M per mass unit.
            ext_z = zs + ['99999']
            ext_m = [mass[z, 'wh'] for z in zs] + [overnight.score.DOLLARS['wh'] / 1e6 - total_a - 900.0]
            data.write(data.Extract(('wh',), ext_z, ['wh'] * 31, ext_m, [{}] * 31, [0.0] * 31), extract)
            ledger = [dict(zip_code=z, current_channel=f, district=j, model_channel='WH', state='NY', reason='',
                           m_rel=0.0) for z, f, j in cells]  # deliberately stale: full extract must win
            listed = ['WH_01'] if variant == 'missing_district' else ['WH_01', 'WH_02']
            for name, rows in (('ledger.csv', ledger), ('districts.csv', [dict(channel='WH', district=j) for j in listed])):
                with open(os.path.join(final, name), 'w', newline='') as fh:
                    writer = csv.DictWriter(fh, list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
            rc = 1 if variant in ('manhattan', 'unmeasured') else 2 if variant == 'crash' else None if variant == 'missing_gate' else 0
            evidence = (lambda f, p: _evidence(f, p, necks=None if variant == 'unmeasured' else 0)) if rc == 1 else None
            runner = _FinalRunner(tmp, extract, rc=rc, evidence=evidence)
            pt = dict(id='toy-pt', structure='ne_plains', k={'WH': 2}, parent='fixed')
            with patch.object(overnight._sealed().ifa_index, 'manhattan_zips', return_value={'10001'}):
                try:
                    accepted = runner._label_final(pt, os.path.dirname(final), final)[0] == 'eligible'
                except overnight.Stop as exc:
                    assert variant == 'missing_district' and exc.label == 'error'
                    accepted = False
            assert accepted == (variant in ('clean', 'manhattan')), variant
            assert [name for name, command in runner.calls] == ['gate']
            _truth(spec.assembly_ledger_model(owned_cells=cells, extract_mass=mass, rates={'wh': 1e6},
                bounds={j: (850e6, 1150e6) for j in ('WH_01', 'WH_02')}, listed_districts=listed,
                gate_rc=rc, m1_pass=True, manhattan_pass=variant == 'manhattan', eligible=True,
                hard=False, breaches=[]), accepted)
