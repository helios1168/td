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
