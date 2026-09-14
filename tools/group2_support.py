import json
import networkx as nx
import numpy as np

def generate_valid_supports(problem, max_size=6, max_dist=900, max_dist_state=None):
    if max_dist_state is None:
        max_dist_state = {"WA": 1200.0}
        
    n = problem.n_state
    
    # Precompute distances
    dist = np.zeros((n, n))
    xy = problem.state_xy
    if len(xy) > 0:
        for i in range(n):
            for j in range(i+1, n):
                d = np.linalg.norm(xy[i] - xy[j])
                dist[i, j] = d
                dist[j, i] = d
                
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(problem.edges)
    
    supports = set()
    
    def extend(curr_set, neighbors):
        frozen = tuple(sorted(curr_set))
        if frozen in supports:
            return
        supports.add(frozen)
        if len(curr_set) < max_size:
            for v in neighbors:
                new_set = curr_set | {v}
                new_neighbors = (neighbors | set(G.neighbors(v))) - new_set
                extend(new_set, new_neighbors)
                
    for i in range(n):
        extend({i}, set(G.neighbors(i)))
        
    valid = []
    for s in supports:
        is_valid = True
        s_list = list(s)
        for i in range(len(s_list)):
            for j in range(i+1, len(s_list)):
                u, v = s_list[i], s_list[j]
                u_name = problem.state_list[u]
                v_name = problem.state_list[v]
                
                limit = max_dist
                if u_name in max_dist_state:
                    limit = max(limit, max_dist_state[u_name])
                if v_name in max_dist_state:
                    limit = max(limit, max_dist_state[v_name])
                    
                if dist[u, v] > limit:
                    is_valid = False
                    break
            if not is_valid:
                break
        if is_valid:
            valid.append(s)
            
    return valid

def solve_exact_support(problem, supports, count=14, band=(553.724691, 676.774623),
                        eligible_units=None, required_units=None,
                        exact_coverage=True, macro_contact_caps=None,
                        compactness_weight=0.001):
    import highspy
    
    if eligible_units is None:
        eligible_units = list(range(problem.n_state))
        
    num_supports = len(supports)
    if num_supports == 0:
        return None
        
    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
        
    state_to_idx = {name: i for i, name in enumerate(problem.state_list)}
    
    req_indices = set()
    if required_units is not None:
        for u in required_units:
            req_indices.add(u if isinstance(u, int) else state_to_idx[u])
    elif exact_coverage:
        req_indices = set(eligible_units)
        
    y_vars_per_support = [len(s) for s in supports]
    num_y_vars = sum(y_vars_per_support)
    num_vars = num_supports + num_y_vars
    
    w = problem.W[:, problem.slots["N"][0]] if "N" in problem.slots else problem.W[:, 0]
    
    model.addVars(num_vars, np.zeros(num_vars), np.ones(num_vars))
    for i in range(num_supports):
        model.changeColBounds(i, 0.0, float(count))
        model.changeColIntegrality(i, highspy.HighsVarType.kInteger)
        
    # Mapping
    y_offset = num_supports
    y_idx = {}
    for i, s in enumerate(supports):
        for v in s:
            y_idx[(v, i)] = y_offset
            y_offset += 1
            
    # 1. sum x_S == count
    model.addRow(float(count), float(count), num_supports, np.arange(num_supports, dtype=np.int32), np.ones(num_supports))
    
    # 2. Coverage
    for v in eligible_units:
        indices = [y_idx[(v, i)] for i, s in enumerate(supports) if v in s]
        if not indices:
            continue
        lo = 1.0 if v in req_indices else 0.0
        hi = 1.0
        model.addRow(lo, hi, len(indices), np.array(indices, dtype=np.int32), np.ones(len(indices)))
        
    # 3 & 4. Bands and share limits
    L, U = band
    for i, s in enumerate(supports):
        for v in s:
            idx = y_idx[(v, i)]
            model.addRow(0.0, highspy.kHighsInf, 2, np.array([idx, i], dtype=np.int32), np.array([1.0, -0.05]))
            model.addRow(-highspy.kHighsInf, 0.0, 2, np.array([idx, i], dtype=np.int32), np.array([1.0, -1.0]))
            
        indices = [y_idx[(v, i)] for v in s] + [i]
        vals_L = [w[v] for v in s] + [-L]
        vals_U = [w[v] for v in s] + [-U]
        model.addRow(0.0, highspy.kHighsInf, len(indices), np.array(indices, dtype=np.int32), np.array(vals_L))
        model.addRow(-highspy.kHighsInf, 0.0, len(indices), np.array(indices, dtype=np.int32), np.array(vals_U))
        
    # Macro contact caps (e.g. {'CA1': 2, 'CA2': 2})
    if macro_contact_caps:
        for unit, cap in macro_contact_caps.items():
            u_idx = unit if isinstance(unit, int) else state_to_idx[unit]
            matching_supports = [i for i, s in enumerate(supports) if u_idx in s]
            if matching_supports:
                model.addRow(0.0, float(cap), len(matching_supports),
                             np.array(matching_supports, dtype=np.int32), np.ones(len(matching_supports)))
        
    # Objective: maximize covered opportunity, with compactness penalty on support diameter
    for (v, i), col_idx in y_idx.items():
        model.changeColCost(col_idx, -float(w[v]))

    if compactness_weight > 0.0 and len(problem.state_xy) > 0:
        dist = np.zeros((problem.n_state, problem.n_state))
        xy = problem.state_xy
        for i in range(problem.n_state):
            for j in range(problem.n_state):
                if i != j:
                    dist[i, j] = np.linalg.norm(xy[i] - xy[j])
        for i, s in enumerate(supports):
            s_list = list(s)
            max_d = max(dist[u, v] for u in s_list for v in s_list) if len(s_list) > 1 else 0.0
            model.changeColCost(i, compactness_weight * max_d)
        
    model.run()
    
    status = model.getModelStatus()
    if status != highspy.HighsModelStatus.kOptimal:
        return None
        
    sol = model.getSolution()
    x_val = sol.col_value[:num_supports]
    y_val = sol.col_value[num_supports:]
    
    out_x = {}
    out_y = {}
    for i, s in enumerate(supports):
        val = int(round(x_val[i]))
        if val > 0:
            out_x[i] = val
            for v in s:
                out_y[(v, i)] = y_val[y_idx[(v, i)] - num_supports]
                
    return {"x": out_x, "y": out_y, "supports": supports, "status": status}

def check_certificate(cert, problem, max_dist=900, max_dist_state=None, band=(553.724691, 676.774623),
                      eligible_units=None, required_units=None, count=14, macro_contact_caps=None):
    if max_dist_state is None: max_dist_state = {"WA": 1200.0}
    if eligible_units is None: eligible_units = list(range(problem.n_state))
    
    state_to_idx = {name: i for i, name in enumerate(problem.state_list)}
    req_indices = set()
    if required_units is not None:
        for u in required_units:
            req_indices.add(u if isinstance(u, int) else state_to_idx[u])
    else:
        req_indices = set(eligible_units)
    
    # 1. Exactly count districts
    total_districts = sum(cert["x"].values())
    if total_districts != count:
        raise ValueError(f"Expected {count} districts, got {total_districts}")
        
    # 2. Coverage
    cov = {v: 0.0 for v in eligible_units}
    for (v, i), val in cert["y"].items():
        if v in cov:
            cov[v] += val
    for v, val in cov.items():
        if v in req_indices:
            if abs(val - 1.0) > 1e-4:
                raise ValueError(f"Required unit {problem.state_list[v]} coverage is {val} != 1.0")
        else:
            if val > 1.0 + 1e-4:
                raise ValueError(f"Unit {problem.state_list[v]} over-covered: {val} > 1.0")
            
    # Macro contact caps
    if macro_contact_caps:
        for unit, cap in macro_contact_caps.items():
            u_idx = unit if isinstance(unit, int) else state_to_idx[unit]
            touches = sum(cert["x"].get(i, 0) for i, s in enumerate(cert["supports"]) if u_idx in s and i in cert["x"])
            if touches > cap:
                raise ValueError(f"Macro unit {unit} contacts {touches} > {cap}")

    # Rest checks: distances, contiguity, bounds
    L, U = band
    w = problem.W[:, problem.slots["N"][0]] if "N" in problem.slots else problem.W[:, 0]
    dist = np.zeros((problem.n_state, problem.n_state))
    xy = problem.state_xy
    if len(xy) > 0:
        for i in range(problem.n_state):
            for j in range(problem.n_state):
                if i != j: dist[i, j] = np.linalg.norm(xy[i] - xy[j])
                
    G = nx.Graph()
    G.add_nodes_from(range(problem.n_state))
    G.add_edges_from(problem.edges)
    
    for i, cnt in cert["x"].items():
        s = cert["supports"][i]
        # Connected
        sub_G = G.subgraph(s)
        if not nx.is_connected(sub_G):
            raise ValueError(f"Support {s} is not connected")
            
        # Distances
        s_list = list(s)
        for u_idx in range(len(s_list)):
            for v_idx in range(u_idx+1, len(s_list)):
                u, v = s_list[u_idx], s_list[v_idx]
                limit = max_dist
                u_name = problem.state_list[u]
                v_name = problem.state_list[v]
                if u_name in max_dist_state: limit = max(limit, max_dist_state[u_name])
                if v_name in max_dist_state: limit = max(limit, max_dist_state[v_name])
                if dist[u, v] > limit + 1e-4:
                    raise ValueError(f"Support {s} distance violation {u_name}-{v_name}: {dist[u, v]} > {limit}")
                    
        # Band
        opp = sum(w[v] * cert["y"][(v, i)] for v in s)
        if opp < L * cnt - 1e-4 or opp > U * cnt + 1e-4:
            raise ValueError(f"Support {s} band violation: {opp/cnt}")
            
        # Share limit
        for v in s:
            val = cert["y"][(v, i)]
            if val < 0.05 * cnt - 1e-4 or val > cnt + 1e-4:
                raise ValueError(f"Support {s} share violation: {val}")
                
    return True

