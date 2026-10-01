from itertools import combinations
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from equivalence import circuits_equivalent
from simplify import circuit_to_gate_list, gate_list_to_circuit
from targets import (
    bell_state,
    ghz_state,
    swap_gate,
    cz_via_hadamard,
    repetition_code,
    teleportation_prep,
    superdense_coding,
    w_state,
    grover_diffusion_2q,
    deutsch_jozsa_balanced,
    qft_butterfly_2q,
    toffoli_decomposition,
)


def ghz_state_3():
    """
    Fixed 3-qubit GHZ state, for motif-matching purposes. The GHZ TARGET
    (targets.py) scales to any qubit count, but the motif scanner assumes
    a fixed size per motif -- 3 qubits is the canonical minimal case.
    """
    return ghz_state(3)


# Registry of known motifs. Each has a fixed qubit count (a motif is a
# specific small pattern, unlike targets which can sometimes scale).
MOTIFS = {
    "bell_pair": {"builder": bell_state, "num_qubits": 2},
    "ghz_state_3": {"builder": ghz_state_3, "num_qubits": 3},
    "swap_gate": {"builder": swap_gate, "num_qubits": 2},
    "cz_via_hadamard": {"builder": cz_via_hadamard, "num_qubits": 2},
    "repetition_code": {"builder": repetition_code, "num_qubits": 3},
    "teleportation_prep": {"builder": teleportation_prep, "num_qubits": 3},
    "superdense_coding": {"builder": superdense_coding, "num_qubits": 2},
    "superdense_coding": {"builder": superdense_coding, "num_qubits": 2},
    "w_state": {"builder": w_state, "num_qubits": 3},
    "grover_diffusion_2q": {"builder": grover_diffusion_2q, "num_qubits": 2},
    "deutsch_jozsa_balanced": {"builder": deutsch_jozsa_balanced, "num_qubits": 2},
    "qft_butterfly_2q": {"builder": qft_butterfly_2q, "num_qubits": 2},
    "toffoli_decomposition": {"builder": toffoli_decomposition, "num_qubits": 3},
}

def find_motifs(qc):
    """
    Scan every contiguous sub-sequence of gates in qc, on every possible
    pair (or group) of qubits, and check whether it matches a known motif.
    Returns a list of matches: (motif_name, qubit_indices, start_index, end_index).
    Duplicate (motif, qubits) pairs are collapsed to a single entry.

    Performance optimizations (all correctness-preserving, not heuristic):
    1. A candidate window is only checked if its gate count EXACTLY matches
       the motif's own gate count.
    2. A qubit subset is skipped entirely if it doesn't have at least as
       many relevant gates as the motif requires.
    3. Within each specific candidate WINDOW (not just anywhere in the
       subset's gate history), every qubit in the subset must actually be
       touched by a gate inside that window. Without this, a motif with an
       idle internal qubit (e.g., teleportation_prep) could falsely match
       against ANY unrelated qubit that happens to have gates elsewhere in
       the circuit, since those unrelated gates would satisfy a subset-wide
       check without being part of the actual matched pattern.
    """
    gate_list = circuit_to_gate_list(qc)
    total_qubits = qc.num_qubits
    matches = []

    for motif_name, motif_info in MOTIFS.items():
        motif_num_qubits = motif_info["num_qubits"]
        motif_circuit = motif_info["builder"]()
        motif_gate_count = len(circuit_to_gate_list(motif_circuit))

        for qubit_subset in combinations(range(total_qubits), motif_num_qubits):

            relevant_indices = [
                i for i, (name, qubits, params) in enumerate(gate_list)
                if set(qubits).issubset(set(qubit_subset))
            ]

            if len(relevant_indices) < motif_gate_count:
                continue

            for start in range(len(relevant_indices) - motif_gate_count + 1):
                window_indices = relevant_indices[start:start + motif_gate_count]

                if window_indices != list(range(window_indices[0], window_indices[-1] + 1)):
                    continue

                sub_gate_list = [gate_list[i] for i in window_indices]

                # Optimization 3 (corrected): check qubit coverage WITHIN
                # this specific window, not the whole subset's history.
                qubits_touched_in_window = set()
                for _, gate_qubits, _ in sub_gate_list:
                    qubits_touched_in_window.update(gate_qubits)
                if not set(qubit_subset).issubset(qubits_touched_in_window):
                    continue

                qubit_map = {q: i for i, q in enumerate(qubit_subset)}
                remapped = [
                    (name, tuple(qubit_map[q] for q in qubits), params)
                    for name, qubits, params in sub_gate_list
                ]
                sub_circuit = gate_list_to_circuit(remapped, motif_num_qubits)

                if circuits_equivalent(sub_circuit, motif_circuit):
                    matches.append({
                        "motif": motif_name,
                        "qubits": qubit_subset,
                        "gate_range": (window_indices[0], window_indices[-1]),
                    })

    seen = set()
    deduplicated_matches = []
    for match in matches:
        key = (match["motif"], match["qubits"])
        if key not in seen:
            seen.add(key)
            deduplicated_matches.append(match)

    return deduplicated_matches


def instantiate_motif(motif_name, target_qubits):
    """
    The reverse of what find_motifs does internally: given a motif name
    and a tuple/list of REAL qubit indices to place it on, build that
    motif's canonical gate sequence and remap it onto those real qubits.

    Returns a plain gate list of (name, qubits, params) triples, using
    the REAL qubit numbers.

    Raises ValueError if motif_name is unknown or target_qubits doesn't
    match the motif's required qubit count.
    """
    if motif_name not in MOTIFS:
        raise ValueError(f"Unknown motif: '{motif_name}'")

    motif_info = MOTIFS[motif_name]
    expected_count = motif_info["num_qubits"]

    if len(target_qubits) != expected_count:
        raise ValueError(
            f"Motif '{motif_name}' requires exactly {expected_count} qubits, "
            f"but {len(target_qubits)} were given: {target_qubits}"
        )

    motif_circuit = motif_info["builder"]()
    internal_gate_list = circuit_to_gate_list(motif_circuit)

    qubit_map = {internal_index: real_qubit for internal_index, real_qubit in enumerate(target_qubits)}

    remapped_gate_list = [
        (name, tuple(qubit_map[q] for q in qubits), params)
        for name, qubits, params in internal_gate_list
    ]

    return remapped_gate_list


if __name__ == "__main__":
    qc = QuantumCircuit(3)
    qc.x(0)
    qc.h(1)
    qc.cx(1, 2)
    qc.z(0)

    print("Circuit:")
    print(qc.draw())

    found = find_motifs(qc)
    print("\nMotifs found:")
    for match in found:
        print(f"  '{match['motif']}' on qubits {match['qubits']}, "
              f"gates {match['gate_range'][0]}-{match['gate_range'][1]}")

    print("\n--- Testing instantiate_motif (reverse conversion) ---")
    reconstructed = instantiate_motif("bell_pair", (2, 5))
    print("bell_pair instantiated on qubits (2, 5):")
    for gate in reconstructed:
        print(f"  {gate}")