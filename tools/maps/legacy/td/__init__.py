# Vendored unchanged from tag archive/pre-support-2026-09 (commit 1251534675dfcdc82e9aad402d10415b663c60e2), td/__init__.py, for tools/maps/render.py (#120).
"""td -- territory design for the national annuity wholesaling channel.

    from td import model, channel, instance
    from td.solvers import REGISTRY, base

`model`    the N-way maths: per-rep utilities, gains, the Nash objective, contiguity.
`channel`  the national-channel problem: two stages, the district budget, staffing.
`instance` loading the descaled real instance produced by tools/instance_export.
`solvers`  the MILP engines and the harness contract they implement.

See docs/CHANNEL.md for the problem and docs/MODEL.md for the model.
"""
__version__ = "0.2.0"
