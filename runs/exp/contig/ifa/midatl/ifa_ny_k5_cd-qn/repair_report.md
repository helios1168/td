# Queens/Nassau local repair

NY candidate: **yes**, by requested local criterion: 0 detached pieces; Manhattan only remaining M1 neck under both gates. Not CONUS-deliverable: partial NY ledger leaves 7,482 channel ZIPs unowned and 23,992 fine-channel cells missing; strict M1 remains fail.

Default gate used for repair, TD_NECK_GAP_WIDTH unset. Window held at 798.74–1148.19 m_rel, intersected with scenario band; no loosening. One solver process. --time-limit 240, --budget 540. No timeout needed.

## Windows

Queens/Nassau original: NY#3 / IFA_03, 11004..., 41 ZIPs, 7.48 km, 45.9% land, 68.8% mass.

| neck | shape | size | status | elapsed | kept |
|---|---|---:|---|---:|---|
| Queens/Nassau | ball h=3 | 109 ZIPs | optimal | 2.6 s | yes |

No other Queens/Nassau windows tried. Neck count among window districts: 2 → 1. Manhattan NY#2 exempt. Three neck cuts; transient newly constructed Nassau neck cut away before acceptance.

## Re-audits

| gate | remaining M1 neck | km | ZIPs | land | mass |
|---|---|---:|---:|---:|---:|
| default | Manhattan IFA_02, 10001... | 5.50 | 40 | 5.2% | 47.5% |
| TD_NECK_GAP_WIDTH=1 | Manhattan IFA_02, 10001... | 6.99 | 40 | 5.4% | 47.4% |

Both: 0 districts in pieces, 0 detached pieces, 1 M1 neck. Queens/Nassau neck gone. Diagnostic-only mass neck remains IFA_02, 10170: default 0.69 km, 1 ZIP, 0.0% land, 8.3% mass; gap=1: 1.09 km, 1 ZIP, 0.0% land, 8.3% mass.

## District opportunity

$M conversion reuses tools/exp/contig/merge.py DOLLARS_PER_M_REL = 1.2519681558.

| district | drawn m_rel | $M |
|---|---:|---:|
| IFA_01 | 922.998655 | 1155.56 |
| IFA_02 | 868.781115 | 1087.69 |
| IFA_03 | 925.703282 | 1158.95 |
| IFA_04 | 826.726173 | 1035.03 |
| IFA_05 | 824.758100 | 1032.57 |

## Reproduction

repair.py has no district/neck CLI selector. Supervisor approved /tmp/iss/ifa/ny_qn_wrapper.py, copied here as repair_wrapper.py: imports unchanged repair.py and skips _repair_neck only when cut-off side contains 10001. Exhausted Manhattan skipped twice (initial and next round). All other repair logic/exemption semantics unchanged. manifest.json notes records wrapper, skip and exact argv. repair.log and both audit logs copied here.

HEAD before/after: 63c4f22df0cd97f1239c232dec40d0c05d7413a5. No tracked edits; no staged files; no git add/commit/push. Other worker folders untouched.

LEARNED: NY congressional K5 Queens/Nassau neck can be removed by 109-ZIP h=3 local repair within 798.74–1148.19 m_rel; Manhattan remains sole M1 neck under default and gap=1 gates.
DECIDED: Supervisor approved run-only wrapper to skip exhausted Manhattan side containing 10001; repair CLI has no selector. Budget 540 s bounds run while preserving full 240 s first Queens/Nassau window allowance.
