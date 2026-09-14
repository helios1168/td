import numpy as np
from types import SimpleNamespace
from td.solvers import level0
from tools.group2_support import generate_valid_supports, solve_exact_support, check_certificate

def toy(masses):
    cells = SimpleNamespace(
        M=np.asarray(masses, float).reshape(-1, 1),
        channels=("N_WH",), 
        state_list=[f"S{i}" for i in range(len(masses))]
    )
    # create a linear graph
    edges = [(i, i+1) for i in range(len(masses)-1)]
    # dummy state_xy where spacing is 100 units
    state_xy = np.array([[i * 100.0, 0.0] for i in range(len(masses))])
    
    problem = level0.build_level0(cells, {"N": ("N_WH",)},
                                  edges=edges,
                                  L=0.8, U=1.2, eta=0.05, state_xy=state_xy, dist_max=900)
    return problem

def test_support_generation():
    problem = toy([10.0] * 12)
    # max_size=3, max_dist=200
    supports = generate_valid_supports(problem, max_size=3, max_dist=200)
    # Size up to 3 => 12 supports of size 1, 11 of size 2, 10 of size 3 (since linear graph)
    assert len(supports) == 12 + 11 + 10

def test_support_generation_with_overrides():
    problem = toy([10.0] * 5)
    problem.state_list = ["S0", "S1", "WA", "S3", "S4"]
    # S0 to S4, total length 400.
    # max_dist = 100, WA = 300
    supports = generate_valid_supports(problem, max_size=4, max_dist=100, max_dist_state={"WA": 300.0})
    assert (1, 2, 3) not in supports
    assert (0, 1, 2) in supports

def test_master_problem_solves_toy():
    # 3 states, 30.0 each. Total 90.0
    # Want to partition into 1 district of band [80, 100]
    problem = toy([30.0, 30.0, 30.0])
    supports = generate_valid_supports(problem, max_size=3, max_dist=500)
    
    cert = solve_exact_support(problem, supports, count=1, band=(80.0, 100.0))
    assert cert is not None
    assert sum(cert["x"].values()) == 1
    # It must select the support (0, 1, 2) because sum w_v = 90
    support_idx = list(cert["x"].keys())[0]
    assert cert["supports"][support_idx] == (0, 1, 2)
    
def test_certificate_validator():
    problem = toy([30.0, 30.0, 30.0])
    supports = [(0, 1, 2)]
    cert = {
        "x": {0: 1},
        "y": {(0, 0): 1.0, (1, 0): 1.0, (2, 0): 1.0},
        "supports": supports
    }
    # Should pass
    assert check_certificate(cert, problem, max_dist=500, band=(80.0, 100.0), count=1)
    
    # Violate bound
    cert_bad_band = {
        "x": {0: 1},
        "y": {(0, 0): 0.5, (1, 0): 0.5, (2, 0): 0.5},
        "supports": supports
    }
    cert_bad_band["y"] = {(0, 0): 1.0, (1, 0): 1.0, (2, 0): 1.0}
    try:
        check_certificate(cert_bad_band, problem, max_dist=500, band=(95.0, 100.0), count=1)
        assert False, "Expected ValueError"
    except ValueError:
        pass
        
    # Violate coverage
    cert_bad_cov = {
        "x": {0: 1},
        "y": {(0, 0): 0.5, (1, 0): 1.0, (2, 0): 1.0},
        "supports": supports
    }
    try:
        check_certificate(cert_bad_cov, problem, max_dist=500, band=(80.0, 100.0), count=1)
        assert False, "Expected ValueError"
    except ValueError:
        pass
