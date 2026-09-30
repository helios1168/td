"""python -m td <command>

    geo     fetch the 2025 geography sources and build reference/2025/ (td.geo)
    run     run <spec> (--extract PATH | --fixture SEED): master, realizer, ledger, audit,
            names and maps into runs/<scenario>/ (td.output)
    maps    maps <run dir>: redraw a run's maps from its ledger.csv (td.output)
"""
from __future__ import annotations

import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "geo":
        from td import geo
        return geo.main(rest)
    if cmd in ("run", "maps"):
        from td import output
        return output.main_run(rest) if cmd == "run" else output.main_maps(rest)
    print(f"unknown command {cmd!r}\n\n{__doc__.strip()}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
