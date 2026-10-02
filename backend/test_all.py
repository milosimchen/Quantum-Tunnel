import os
# Tests call AI endpoints many times; lift the public-site rate limits.
os.environ.setdefault("AI_PER_IP_BURST", "100000")
os.environ.setdefault("AI_PER_IP_DAILY", "100000")
os.environ.setdefault("AI_SITE_DAILY", "100000")
from qiskit import QuantumCircuit
from equivalence import circuits_equivalent, format_dirac_notation
from targets import find_matching_target, find_closest_target, find_single_gate_completion,superdense_coding,w_state,grover_diffusion_2q,deutsch_jozsa_balanced, qft_butterfly_2q, toffoli_decomposition
from simplify import circuit_to_gate_list, simplify_once, simplify_fully, gate_list_to_circuit
from motifs import find_motifs
from fastapi.testclient import TestClient
from main import app, display_name
from motifs import instantiate_motif
from equivalence import is_fully_entangled 

import math
client = TestClient(app)

def check(description, condition):
    """Print a clear pass/fail line for one test."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {description}")
    return condition


results = []

# --- equivalence.py tests ---

qc_a = QuantumCircuit(2)
qc_a.h(0)
qc_a.cx(0, 1)

qc_b = QuantumCircuit(2)
qc_b.h(0)
qc_b.cx(0, 1)

qc_c = QuantumCircuit(2)
qc_c.h(0)
qc_c.h(1)

results.append(check(
    "Identical circuits are equivalent",
    circuits_equivalent(qc_a, qc_b) == True
))
results.append(check(
    "Different circuits are NOT equivalent",
    circuits_equivalent(qc_a, qc_c) == False
))
results.append(check(
    "Circuits with different qubit counts are NOT equivalent",
    circuits_equivalent(qc_a, QuantumCircuit(3)) == False
))

# --- main.py / API tests ---

bell_request = {
    "num_qubits": 2,
    "gates": [
        {"name": "h", "qubits": [0]},
        {"name": "cx", "qubits": [0, 1]}
    ]
}

sim_response = client.post("/simulate", json=bell_request)
results.append(check(
    "/simulate returns 200 and correct gate count for Bell state",
    sim_response.status_code == 200 and sim_response.json()["gate_count"] == 2
))

scan_response = client.post("/scan", json=bell_request)
results.append(check(
    "/scan correctly identifies Bell state as a target match",
    scan_response.status_code == 200 and scan_response.json()["target_match"] == "bell_state"
))

rotation_request = {
    "num_qubits": 1,
    "gates": [{"name": "rx", "qubits": [0], "params": [1.5708]}]
}
rotation_response = client.post("/simulate", json=rotation_request)
results.append(check(
    "/simulate correctly handles a parameterized rotation gate (rx)",
    rotation_response.status_code == 200 and rotation_response.json()["gate_count"] == 1
))

targets_response = client.get("/targets")
found_target_names = {t["name"] for t in targets_response.json()["targets"]}
results.append(check(
    "/targets lists both bell_state and ghz_state",
    targets_response.status_code == 200 and {"bell_state", "ghz_state"} <= found_target_names
))

gates_response = client.get("/gates")
results.append(check(
    "/gates lists the full expanded 11-gate set",
    gates_response.status_code == 200 and len(gates_response.json()["gates"]) == 11
))

# --- targets.py tests ---

bell_attempt = QuantumCircuit(2)
bell_attempt.h(0)
bell_attempt.cx(0, 1)

ghz_attempt = QuantumCircuit(3)
ghz_attempt.h(0)
ghz_attempt.cx(0, 1)
ghz_attempt.cx(0, 2)

incomplete_attempt = QuantumCircuit(3)
incomplete_attempt.h(0)
incomplete_attempt.cx(0, 1)

results.append(check(
    "Correct Bell state matches 'bell_state'",
    find_matching_target(bell_attempt) == "bell_state"
))
results.append(check(
    "Correct GHZ state matches 'ghz_state'",
    find_matching_target(ghz_attempt) == "ghz_state"
))
results.append(check(
    "Incomplete 3-qubit attempt matches NOTHING (regression check for the earlier bug)",
    find_matching_target(incomplete_attempt) is None
))
# Teleportation target test
teleport_attempt = QuantumCircuit(3)
teleport_attempt.h(1)
teleport_attempt.cx(1, 2)
teleport_attempt.cx(0, 1)
teleport_attempt.h(0)
teleport_attempt.cx(1, 2)
teleport_attempt.cz(0, 2)

results.append(check(
    "Correctly-built teleportation circuit matches 'teleportation'",
    find_matching_target(teleport_attempt) == "teleportation"
))
# --- motifs.py tests ---

motif_test = QuantumCircuit(3)
motif_test.x(0)
motif_test.h(1)
motif_test.cx(1, 2)
motif_test.z(0)

motif_matches = find_motifs(motif_test)
results.append(check(
    "Bell pair motif correctly detected on qubits (1,2) within a larger circuit",
    any(m["motif"] == "bell_pair" and m["qubits"] == (1, 2) for m in motif_matches)
))

no_motif_test = QuantumCircuit(2)
no_motif_test.h(0)
no_motif_test.h(1)  # NOT entangling -- should not match bell_pair
no_motif_matches = find_motifs(no_motif_test)
results.append(check(
    "Non-entangling circuit does NOT falsely match bell_pair",
    len(no_motif_matches) == 0
))

# --- simplify.py tests ---

# Adjacent cancellation
adj_test = QuantumCircuit(2)
adj_test.h(0)
adj_test.h(0)
adj_test.cx(0, 1)
adj_result, _ = simplify_fully(adj_test)
results.append(check(
    "Adjacent H-H cancels down to just the CNOT",
    len(adj_result.data) == 1 and circuits_equivalent(adj_test, adj_result)
))

# Full-order cancellation (S^4 = I)
s4_test = QuantumCircuit(1)
s4_test.s(0)
s4_test.s(0)
s4_test.s(0)
s4_test.s(0)
s4_result, _ = simplify_fully(s4_test)
results.append(check(
    "Four S gates fully cancel (S^4 = I)",
    len(s4_result.data) == 0 and circuits_equivalent(s4_test, s4_result)
))

# Two S gates should now correctly replace to a single Z gate (S^2 = Z),
# NOT vanish entirely (that would only be correct for a full S^4 = I run).
s2_test = QuantumCircuit(1)
s2_test.s(0)
s2_test.s(0)
s2_result, _ = simplify_fully(s2_test)
results.append(check(
    "Two S gates correctly replace to one Z gate (S^2 = Z), not removed entirely",
    len(s2_result.data) == 1 and circuits_equivalent(s2_test, s2_result)
))
# Commutation-based non-adjacent cancellation
commute_test = QuantumCircuit(2)
commute_test.h(0)
commute_test.x(1)
commute_test.h(0)
commute_test.cx(0, 1)
commute_result, _ = simplify_fully(commute_test)
results.append(check(
    "Non-adjacent H...H cancels via commutation, leaving X and CNOT",
    len(commute_result.data) == 2 and circuits_equivalent(commute_test, commute_result)
))

# A circuit with NO redundancy should be left completely untouched
no_redundancy_test = QuantumCircuit(2)
no_redundancy_test.h(0)
no_redundancy_test.cx(0, 1)
no_redundancy_result, no_redundancy_steps = simplify_fully(no_redundancy_test)
results.append(check(
    "A circuit with no redundancy is left unchanged",
    len(no_redundancy_result.data) == 2 and len(no_redundancy_steps) == 0
))

# Multiple different kinds of redundancy in one circuit, all at once
combo_test = QuantumCircuit(2)
combo_test.h(0)
combo_test.h(0)      # adjacent cancellation
combo_test.s(1)
combo_test.s(1)
combo_test.s(1)
combo_test.s(1)      # full-order cancellation
combo_test.cx(0, 1)
combo_result, combo_steps = simplify_fully(combo_test)
results.append(check(
    "A circuit combining adjacent AND full-order redundancy fully simplifies to just the CNOT",
    len(combo_result.data) == 1 and circuits_equivalent(combo_test, combo_result)
))
chat_request_body = {
    "num_qubits": 2,
    "gates": [
        {"name": "h", "qubits": [0]},
        {"name": "h", "qubits": [0]},
        {"name": "cx", "qubits": [0, 1]}
    ],
    "question": "How many gates were removed?"
}
chat_response = client.post("/chat", json=chat_request_body)
results.append(check(
    "/chat returns 200 and a non-empty answer",
    chat_response.status_code == 200 and len(chat_response.json()["answer"]) > 0
))

substitution_test_request = {
    "num_qubits": 2,
    "gates": [
        {"name": "h", "qubits": [0]},
        {"name": "h", "qubits": [0]},
        {"name": "cx", "qubits": [0, 1]}
    ],
    "question": "What was the original gate count?"
}
substitution_response = client.post("/chat", json=substitution_test_request)
response_json = substitution_response.json()
results.append(check(
    "/chat substitutes real numbers with no leftover unfilled placeholders",
    substitution_response.status_code == 200
    and "{" not in response_json["answer"]
    and len(response_json["invalid_fields_referenced"]) == 0
))

# Power replacement (S^2 = Z, T^2 = S)
power_test = QuantumCircuit(1)
power_test.s(0)
power_test.s(0)
power_test.t(0)
power_test.t(0)
power_result, power_steps = simplify_fully(power_test)
results.append(check(
    "S^2=Z and T^2=S power replacements both fire correctly",
    len(power_result.data) == 2 and circuits_equivalent(power_test, power_result)
))

# Rotation composition (RZ(a) + RZ(b) = RZ(a+b))
rotation_compose_test = QuantumCircuit(1)
rotation_compose_test.rz(0.3, 0)
rotation_compose_test.rz(0.4, 0)
rotation_result, rotation_steps = simplify_fully(rotation_compose_test)
results.append(check(
    "Two RZ rotations combine into one with summed angle",
    len(rotation_result.data) == 1
    and circuits_equivalent(rotation_compose_test, rotation_result)
))

# Rotation composition landing exactly on the identity (RZ(pi) + RZ(pi) = RZ(2pi) = I)

rotation_identity_test = QuantumCircuit(1)
rotation_identity_test.rz(math.pi, 0)
rotation_identity_test.rz(math.pi, 0)
rotation_identity_result, _ = simplify_fully(rotation_identity_test)
results.append(check(
    "RZ(pi) + RZ(pi) correctly collapses to 0 gates (identity), not a lingering RZ(2pi)",
    len(rotation_identity_result.data) == 0
    and circuits_equivalent(rotation_identity_test, rotation_identity_result)
))

# Pauli product (X*Y = Z, up to global phase)
pauli_test = QuantumCircuit(1)
pauli_test.x(0)
pauli_test.y(0)
pauli_result, _ = simplify_fully(pauli_test)
results.append(check(
    "X then Y correctly combines into Z (Pauli product, up to global phase)",
    len(pauli_result.data) == 1
    and circuits_equivalent(pauli_test, pauli_result)
))



# New motif detection tests
swap_test = QuantumCircuit(2)
swap_test.cx(0, 1)
swap_test.cx(1, 0)
swap_test.cx(0, 1)
swap_matches = find_motifs(swap_test)
results.append(check(
    "SWAP gate (3 CNOTs) correctly recognized as a motif",
    any(m["motif"] == "swap_gate" for m in swap_matches)
))

cz_test = QuantumCircuit(2)
cz_test.h(1)
cz_test.cx(0, 1)
cz_test.h(1)
cz_matches = find_motifs(cz_test)
results.append(check(
    "H-CX-H identity correctly recognized as cz_via_hadamard motif",
    any(m["motif"] == "cz_via_hadamard" for m in cz_matches)
))

repetition_test = QuantumCircuit(3)
repetition_test.cx(0, 1)
repetition_test.cx(0, 2)
repetition_matches = find_motifs(repetition_test)
ghz_test_for_distinction = QuantumCircuit(3)
ghz_test_for_distinction.h(0)
ghz_test_for_distinction.cx(0, 1)
ghz_test_for_distinction.cx(0, 2)
ghz_matches_for_distinction = find_motifs(ghz_test_for_distinction)
results.append(check(
    "Repetition code (no H) and GHZ state (with H) are correctly distinguished",
    any(m["motif"] == "repetition_code" for m in repetition_matches)
    and not any(m["motif"] == "ghz_state_3" for m in repetition_matches)
    and any(m["motif"] == "ghz_state_3" for m in ghz_matches_for_distinction)
))

# instantiate_motif reverse-conversion test
reconstructed_bell = instantiate_motif("bell_pair", (2, 5))
results.append(check(
    "instantiate_motif correctly remaps bell_pair onto real qubits (2, 5)",
    reconstructed_bell == [("h", (2,), ()), ("cx", (2, 5), ())]
))

from fastapi.testclient import TestClient
# (client should already exist from earlier tests)

named_pattern_response = client.post("/generate_circuit", json={"request": "build a Bell state on qubits 2 and 4"})
named_pattern_data = named_pattern_response.json()
results.append(check(
    "/generate_circuit correctly builds a named Bell state on specified qubits",
    named_pattern_response.status_code == 200
    and named_pattern_data["success"] is True
    and named_pattern_data["gates"] == [
        {"name": "h", "qubits": [2], "params": []},
        {"name": "cx", "qubits": [2, 4], "params": []},
    ]
))

explicit_gates_response = client.post("/generate_circuit", json={"request": "add an H gate on qubit 0 and a CNOT from qubit 0 to qubit 1"})
explicit_gates_data = explicit_gates_response.json()
results.append(check(
    "/generate_circuit correctly builds explicit gates from a direct request",
    explicit_gates_response.status_code == 200
    and explicit_gates_data["success"] is True
    and len(explicit_gates_data["gates"]) == 2
))

invalid_request_response = client.post("/generate_circuit", json={"request": "build me a flibbertigibbet circuit with 47 qubits doing nonsense"})
invalid_request_data = invalid_request_response.json()
results.append(check(
    "/generate_circuit correctly reports failure for an unfulfillable request",
    invalid_request_response.status_code == 200
    and invalid_request_data["success"] is False
))

append_test_response = client.post("/generate_circuit", json={
    "request": "now also add a GHZ state on qubits 2, 3, and 4",
    "current_gates": [
        {"name": "h", "qubits": [0], "params": []},
        {"name": "cx", "qubits": [0, 1], "params": []},
    ],
})
append_test_data = append_test_response.json()
results.append(check(
    "/generate_circuit correctly appends a new pattern to an existing circuit",
    append_test_response.status_code == 200
    and append_test_data["success"] is True
    and len(append_test_data["gates"]) == 5
    and append_test_data["gates"][0] == {"name": "h", "qubits": [0], "params": []}
))



entangled_bell = QuantumCircuit(2)
entangled_bell.h(0)
entangled_bell.cx(0, 1)
results.append(check(
    "is_fully_entangled correctly identifies a Bell state as fully entangled",
    is_fully_entangled(entangled_bell) is True
))

not_entangled_test = QuantumCircuit(2)
not_entangled_test.h(0)
not_entangled_test.h(1)
results.append(check(
    "is_fully_entangled correctly identifies two independent qubits as NOT fully entangled",
    is_fully_entangled(not_entangled_test) is False
))

partial_entanglement_test = QuantumCircuit(3)
partial_entanglement_test.h(0)
partial_entanglement_test.cx(0, 1)
results.append(check(
    "is_fully_entangled correctly rejects a circuit with one untouched qubit",
    is_fully_entangled(partial_entanglement_test) is False
))

goal_circuit_response = client.post("/generate_goal_circuit", json={"request": "build me a circuit that entangles 3 qubits"})
goal_circuit_data = goal_circuit_response.json()

if goal_circuit_data["success"]:
    goal_gate_list = [
        (g["name"], tuple(g["qubits"]), tuple(g["params"]))
        for g in goal_circuit_data["gates"]
    ]
    goal_circuit = gate_list_to_circuit(goal_gate_list, goal_circuit_data["num_qubits"])
    results.append(check(
        "/generate_goal_circuit produces a circuit that is ACTUALLY fully entangled (not just claimed)",
        is_fully_entangled(goal_circuit)
    ))
else:
    results.append(check(
        "/generate_goal_circuit produces a circuit that is ACTUALLY fully entangled (not just claimed)",
        False
    ))

multi_goal_response = client.post("/generate_goal_circuit", json={
    "request": "build a fully entangled 3-qubit circuit using only Clifford gates with exactly 4 gates"
})
multi_goal_data = multi_goal_response.json()

if multi_goal_data["success"]:
    multi_goal_gate_list = [
        (g["name"], tuple(g["qubits"]), tuple(g["params"]))
        for g in multi_goal_data["gates"]
    ]
    multi_goal_circuit = gate_list_to_circuit(multi_goal_gate_list, multi_goal_data["num_qubits"])
    clifford_set = {"h", "s", "cx", "x", "y", "z"}
    used_gates = {name for name, _, _ in multi_goal_gate_list}

    results.append(check(
        "/generate_goal_circuit satisfies multiple simultaneous goals (gate count, Clifford-only, full entanglement) -- independently re-verified",
        len(multi_goal_gate_list) == 4
        and used_gates.issubset(clifford_set)
        and is_fully_entangled(multi_goal_circuit)
    ))
else:
    results.append(check(
        "/generate_goal_circuit satisfies multiple simultaneous goals (gate count, Clifford-only, full entanglement) -- independently re-verified",
        False
    ))
for _ in range(3):
    goal_directed_via_merged_endpoint = client.post("/generate_circuit", json={
        "request": "build a fully entangled 3-qubit circuit using only Clifford gates",
        "current_gates": [],
    })
    goal_directed_data = goal_directed_via_merged_endpoint.json()
    results.append(check(
        "/generate_circuit (merged goal_directed path) succeeds consistently despite LLM-reported num_qubits potentially being unreliable",
        goal_directed_via_merged_endpoint.status_code == 200
        and goal_directed_data["success"] is True
    ))

near_miss_gap_test = QuantumCircuit(3)
near_miss_gap_test.h(0)
near_miss_gap_test.cx(0, 1)
gap_result = find_closest_target(near_miss_gap_test)
results.append(check(
    "find_closest_target correctly identifies GHZ as closest with a 1-gate diff for a near-miss circuit",
    gap_result is not None
    and gap_result[1] == "ghz_state"
    and gap_result[0] == 1
))

near_miss_explain_test = {
    "num_qubits": 3,
    "gates": [
        {"name": "h", "qubits": [0]},
        {"name": "cx", "qubits": [0, 1]},
    ],
}
near_miss_response = client.post("/explain", json=near_miss_explain_test)
near_miss_data = near_miss_response.json()
results.append(check(
    "/explain correctly narrates the closest-target gap for a near-miss circuit, verified as consistent",
    near_miss_response.status_code == 200
    and near_miss_data["interpretation"] is not None
    and near_miss_data["interpretation_check"]["consistent"] is True
))



results.append(check(
    "display_name correctly translates raw internal names to readable form",
    display_name("bell_pair") == "Bell pair"
    and display_name("ghz_state") == "GHZ state"
    and display_name("unknown_thing") == "unknown_thing"
))


single_gate_test = QuantumCircuit(3)
single_gate_test.h(0)
single_gate_test.cx(0, 1)
completion_result = find_single_gate_completion(single_gate_test)
results.append(check(
    "find_single_gate_completion correctly identifies the exact missing gate for a 1-away circuit",
    completion_result == ("ghz_state", ("cx", (0, 2), ()))
))

far_circuit_test = QuantumCircuit(3)
far_circuit_test.x(0)
far_circuit_test.h(1)
far_circuit_test.z(2)
no_completion_result = find_single_gate_completion(far_circuit_test)
results.append(check(
    "find_single_gate_completion correctly returns None for a circuit that's not one gate away from any target",
    no_completion_result is None
))

single_gate_explain_test = {
    "num_qubits": 3,
    "gates": [
        {"name": "h", "qubits": [0]},
        {"name": "cx", "qubits": [0, 1]},
    ],
}
single_gate_response = client.post("/explain", json=single_gate_explain_test)
single_gate_data = single_gate_response.json()
results.append(check(
    "/explain gives a specific, confident single-gate completion suggestion when applicable",
    single_gate_response.status_code == 200
    and single_gate_data["interpretation"] is not None
    and "cx" in single_gate_data["interpretation"].lower()
))

single_gate_structured_response = client.post("/explain", json=single_gate_explain_test)
single_gate_structured_data = single_gate_structured_response.json()
results.append(check(
    "/explain returns single_gate_completion as structured data, not just narration text",
    single_gate_structured_data.get("single_gate_completion") == {
        "target_name": "ghz_state",
        "gate_name": "cx",
        "gate_qubits": [0, 2],
    }
))



bell_dirac_test = QuantumCircuit(2)
bell_dirac_test.h(0)
bell_dirac_test.cx(0, 1)
results.append(check(
    "format_dirac_notation correctly computes the exact Bell state superposition",
    format_dirac_notation(bell_dirac_test) == "0.7071|00⟩ + 0.7071|11⟩"
))

math_dive_response = client.post("/math_deep_dive", json={
    "circuit_request": {
        "num_qubits": 2,
        "gates": [
            {"name": "h", "qubits": [0]},
            {"name": "cx", "qubits": [0, 1]},
        ]
    }
})
math_dive_data = math_dive_response.json()
results.append(check(
    "/math_deep_dive returns correct exact Dirac notation and unitary availability for a small circuit",
    math_dive_response.status_code == 200
    and math_dive_data["dirac_notation"] == "0.7071|00⟩ + 0.7071|11⟩"
    and math_dive_data["unitary_available"] is True
))

large_math_dive_response = client.post("/math_deep_dive", json={
    "circuit_request": {
        "num_qubits": 4,
        "gates": [{"name": "h", "qubits": [i]} for i in range(4)],
    }
})
large_math_dive_data = large_math_dive_response.json()
results.append(check(
    "/math_deep_dive correctly skips the unitary matrix (too large) but still computes Dirac notation for a 4-qubit circuit",
    large_math_dive_response.status_code == 200
    and large_math_dive_data["unitary_available"] is False
    and large_math_dive_data["dirac_available"] is True
))




sdc_motif_test = superdense_coding()
sdc_matches = find_motifs(sdc_motif_test)
results.append(check(
    "Superdense coding (message '11') correctly recognized as a motif",
    any(m["motif"] == "superdense_coding" for m in sdc_matches)
))




w_motif_test = w_state()
w_matches = find_motifs(w_motif_test)
results.append(check(
    "W-state correctly recognized as a motif, distinct from GHZ",
    any(m["motif"] == "w_state" for m in w_matches)
    and not any(m["motif"] == "ghz_state_3" for m in w_matches)
))



grover_motif_test = grover_diffusion_2q()
grover_matches = find_motifs(grover_motif_test)
results.append(check(
    "Grover diffusion operator correctly recognized as a motif",
    any(m["motif"] == "grover_diffusion_2q" for m in grover_matches)
))



dj_motif_test = deutsch_jozsa_balanced()
dj_matches = find_motifs(dj_motif_test)
results.append(check(
    "Deutsch-Jozsa (balanced oracle example) correctly recognized as a motif",
    any(m["motif"] == "deutsch_jozsa_balanced" for m in dj_matches)
))

 

qft_motif_test = qft_butterfly_2q()
qft_matches = find_motifs(qft_motif_test)
results.append(check(
    "QFT butterfly stage correctly recognized as a motif",
    any(m["motif"] == "qft_butterfly_2q" for m in qft_matches)
))

toffoli_motif_test = toffoli_decomposition()
toffoli_matches = find_motifs(toffoli_motif_test)
results.append(check(
    "Toffoli decomposition correctly recognized as a motif",
    any(m["motif"] == "toffoli_decomposition" for m in toffoli_matches)
))

toffoli_nl_test = client.post("/generate_circuit", json={
    "request": "build a toffoli decomposition",
    "current_gates": [],
})
toffoli_nl_data = toffoli_nl_test.json()
results.append(check(
    "/generate_circuit correctly builds the Toffoli decomposition from natural language",
    toffoli_nl_test.status_code == 200
    and toffoli_nl_data["success"] is True
    and len(toffoli_nl_data["gates"]) == 24
))

jobs_response = client.post("/jobs_search", json={"query": "quantum computing", "location": "", "page": 1})
jobs_data = jobs_response.json()
if jobs_data.get("success"):
    results.append(check(
        "/jobs_search returns real, normalized job listings from Adzuna",
        jobs_response.status_code == 200
        and len(jobs_data["jobs"]) > 0
        and "title" in jobs_data["jobs"][0]
        and "apply_url" in jobs_data["jobs"][0]
    ))
else:
    print(f"[SKIPPED] /jobs_search test skipped -- network/credentials unavailable: {jobs_data.get('message')}")
    
# --- Summary ---
print(f"\n{sum(results)} / {len(results)} tests passed.")
if all(results):
    print("Everything is behaving correctly.")
else:
    print("Something needs attention -- check the FAIL lines above.")