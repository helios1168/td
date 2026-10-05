"""Run retained exhaustive numerical checks, with one HiGHS thread pool."""
from time import perf_counter
import clusters
import drawability
import objectives
import polygon_policy


def main():
    start = perf_counter()
    for script in (objectives, clusters, drawability, polygon_policy):
        print(f"=== {script.__name__} ===", flush=True)
        script.main()
    print(f"ALL CLAIM CHECKS PASSED elapsed={perf_counter() - start:.2f}s", flush=True)


if __name__ == "__main__":
    main()
