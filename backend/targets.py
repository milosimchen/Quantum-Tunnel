from qiskit import QuantumCircuit
from equivalence import circuits_equivalent, format_dirac_notation, is_fully_entangled
from simplify import circuit_to_gate_list, gate_list_to_circuit
import numpy as np

def bell_state():
    """The canonical 2-qubit Bell state circuit. Fixed at 2 qubits — this doesn't generalize."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


def ghz_state(num_qubits=3):
    """The canonical GHZ state circuit, generalized to any number of qubits >= 2."""
    qc = QuantumCircuit(num_qubits)
    qc.h(0)
    for target_qubit in range(1, num_qubits):
        qc.cx(0, target_qubit)
    return qc


def teleportation_circuit():
    """
    The deferred-measurement (fully unitary) version of quantum teleportation.
    Qubit 0 holds the state to be teleported; qubit 2 ends up holding it.
    """
    qc = QuantumCircuit(3)
    qc.h(1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.h(0)
    qc.cx(1, 2)
    qc.cz(0, 2)
    return qc


def swap_gate():
    """The canonical SWAP gate, decomposed into 3 CNOTs."""
    qc = QuantumCircuit(2)
    qc.cx(0, 1)
    qc.cx(1, 0)
    qc.cx(0, 1)
    return qc


def cz_via_hadamard():
    """H(target), CX(control,target), H(target) -- exactly equivalent to CZ(control,target)."""
    qc = QuantumCircuit(2)
    qc.h(1)
    qc.cx(0, 1)
    qc.h(1)
    return qc


def repetition_code():
    """The 3-qubit bit-flip repetition code encoder: CX(0,1), CX(0,2), no initial H."""
    qc = QuantumCircuit(3)
    qc.cx(0, 1)
    qc.cx(0, 2)
    return qc


def teleportation_prep():
    """The entanglement-preparation sub-pattern from quantum teleportation."""
    qc = QuantumCircuit(3)
    qc.h(1)
    qc.cx(1, 2)
    return qc

def superdense_coding():
    """
    The canonical superdense coding circuit, encoding the message "11" --
    the standard textbook example, since it's the only one of the four
    messages that applies BOTH possible encoding gates (X then Z), making
    it the most illustrative canonical form. Qubit 0 is Alice's qubit
    (encodes/sends), qubit 1 is Bob's (receives/decodes).
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.x(0)
    qc.z(0)
    qc.cx(0, 1)
    qc.h(0)
    return qc


def w_state():
    """
    The canonical 3-qubit W-state: (|001> + |010> + |100>) / sqrt(3).
    Genuinely distinct entanglement class from GHZ. Uses a controlled-
    RY(pi/2) in place of the textbook-standard controlled-Hadamard,
    decomposed into standard RY/CX gates. Verified numerically to produce
    the exact expected state before registration.
    """
    theta = 2 * np.arccos(1 / np.sqrt(3))

    qc = QuantumCircuit(3)
    qc.ry(theta, 0)
    qc.ry(np.pi / 4, 1)
    qc.cx(0, 1)
    qc.ry(-np.pi / 4, 1)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.x(0)
    return qc


def grover_diffusion_2q():
    """
    The Grover diffusion operator ("inversion about the mean"), for 2
    qubits. Core reflection step of Grover's search algorithm.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(1)
    qc.x(0)
    qc.x(1)
    qc.cz(0, 1)
    qc.x(0)
    qc.x(1)
    qc.h(0)
    qc.h(1)
    return qc


def deutsch_jozsa_balanced():
    """
    The Deutsch-Jozsa algorithm circuit, using the simplest standard
    'balanced' oracle example (a single CX from the input qubit to the
    output qubit) -- one specific, canonical instance, not the general
    algorithm shape.
    """
    qc = QuantumCircuit(2)
    qc.x(1)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.h(0)
    return qc


def qft_butterfly_2q():
    """
    The QFT 'butterfly' stage for 2 qubits: H on qubit 0, followed by a
    controlled-phase(pi/2) rotation between qubits 0 and 1, decomposed
    into RZ/CX gates. Verified numerically against a true CP(pi/2) gate
    before registration.
    """
    theta = np.pi / 2
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.rz(theta / 2, 0)
    qc.rz(theta / 2, 1)
    qc.cx(0, 1)
    qc.rz(-theta / 2, 1)
    qc.cx(0, 1)
    return qc


def toffoli_decomposition():
    """
    Standard Toffoli (CCX) decomposition into H, CX, T, and Z gates only
    (Nielsen & Chuang construction). Tdg is substituted as Z * T^3, since
    no T-dagger primitive exists in this app's gate set. Verified
    numerically to exactly match a true CCX gate before registration.
    """
    def apply_tdg(qc, qubit):
        qc.t(qubit)
        qc.t(qubit)
        qc.t(qubit)
        qc.z(qubit)

    qc = QuantumCircuit(3)
    qc.h(2)
    qc.cx(1, 2)
    apply_tdg(qc, 2)
    qc.cx(0, 2)
    qc.t(2)
    qc.cx(1, 2)
    apply_tdg(qc, 2)
    qc.cx(0, 2)
    qc.t(1)
    qc.t(2)
    qc.cx(0, 1)
    qc.h(2)
    qc.t(0)
    apply_tdg(qc, 1)
    qc.cx(0, 1)
    return qc


# Registry: each target stores its builder AND whether it's qubit-count-flexible.
TARGETS = {
    "bell_state": {"builder": bell_state, "fixed_qubits": 2},
    "ghz_state": {"builder": ghz_state, "fixed_qubits": None},
    "teleportation": {"builder": teleportation_circuit, "fixed_qubits": 3},
}

# Unified registry of every named circuit this app knows how to construct --
# combines TARGETS (whole-circuit patterns) and motif-style building blocks
# into one place, so the NL circuit-building endpoint has a single lookup
# table for "does a pattern by this name exist, and how do I build it."
# Each entry includes common alternate phrasings a user might say, so the
# LLM has real options to match against rather than requiring exact names.
NAMED_CIRCUITS = {
    "bell_state": {
        "builder": bell_state,
        "fixed_qubits": 2,
        "aliases": ["bell pair", "epr pair", "entangled pair"],
    },
    "ghz_state": {
        "builder": ghz_state,
        "fixed_qubits": None,
        "aliases": ["ghz", "greenberger-horne-zeilinger state"],
    },
    "teleportation": {
        "builder": teleportation_circuit,
        "fixed_qubits": 3,
        "aliases": ["quantum teleportation", "teleportation circuit"],
    },
    "swap_gate": {
        "builder": swap_gate,
        "fixed_qubits": 2,
        "aliases": ["swap", "swap circuit"],
    },
    "cz_via_hadamard": {
        "builder": cz_via_hadamard,
        "fixed_qubits": 2,
        "aliases": ["cz identity", "controlled-z via hadamard"],
    },
    "repetition_code": {
        "builder": repetition_code,
        "fixed_qubits": 3,
        "aliases": ["bit flip code", "repetition encoder", "3-qubit repetition code"],
    },
    "teleportation_prep": {
        "builder": teleportation_prep,
        "fixed_qubits": 3,
        "aliases": ["teleportation preparation", "entanglement prep"],
    },

    "superdense_coding": {
        "builder": superdense_coding,
        "fixed_qubits": 2,
        "aliases": ["superdense coding", "dense coding"],
    },
    "w_state": {
        "builder": w_state,
        "fixed_qubits": 3,
        "aliases": ["w state", "w-state"],
    },
    "grover_diffusion_2q": {
        "builder": grover_diffusion_2q,
        "fixed_qubits": 2,
        "aliases": ["grover diffusion", "grover diffusion operator", "inversion about the mean"],
    },
    "deutsch_jozsa_balanced": {
        "builder": deutsch_jozsa_balanced,
        "fixed_qubits": 2,
        "aliases": ["deutsch-jozsa", "deutsch jozsa", "deutsch-jozsa algorithm"],
    },
    "qft_butterfly_2q": {
        "builder": qft_butterfly_2q,
        "fixed_qubits": 2,
        "aliases": ["qft butterfly", "quantum fourier transform butterfly", "qft stage"],
    },
    "toffoli_decomposition": {
        "builder": toffoli_decomposition,
        "fixed_qubits": 3,
        "aliases": ["toffoli", "toffoli decomposition", "ccx decomposition", "toffoli gate"],
    },
}


def instantiate_named_circuit(name, qubits):
    """
    Given a name from NAMED_CIRCUITS and a list/tuple of REAL qubit indices
    to place it on, build that circuit's canonical gate sequence and remap
    it onto those real qubits. Returns a plain gate list of (name, qubits,
    params) triples using the REAL qubit numbers -- ready to insert directly
    into a user's circuit.

    Raises ValueError if the name is unknown or the qubit count doesn't
    match a fixed-size circuit's requirement.
    """
    if name not in NAMED_CIRCUITS:
        raise ValueError(f"Unknown named circuit: '{name}'")

    info = NAMED_CIRCUITS[name]
    fixed_qubits = info["fixed_qubits"]

    if fixed_qubits is not None and len(qubits) != fixed_qubits:
        raise ValueError(
            f"'{name}' requires exactly {fixed_qubits} qubits, "
            f"but {len(qubits)} were given: {qubits}"
        )

    built_circuit = (
        info["builder"]() if fixed_qubits is not None else info["builder"](len(qubits))
    )

    internal_gate_list = circuit_to_gate_list(built_circuit)
    qubit_map = {internal_index: real_qubit for internal_index, real_qubit in enumerate(qubits)}

    return [
        (gate_name, tuple(qubit_map[q] for q in gate_qubits), params)
        for gate_name, gate_qubits, params in internal_gate_list
    ]


def find_matching_target(qc):
    """
    Given a user-built circuit, check it against every known named target
    and return the name of the first match found, or None if it doesn't
    match anything. Targets with a fixed qubit count are skipped entirely
    if the user's circuit doesn't have that many qubits.
    """
    num_qubits = qc.num_qubits

    for target_name, target_info in TARGETS.items():
        fixed_qubits = target_info["fixed_qubits"]

        if fixed_qubits is not None and fixed_qubits != num_qubits:
            continue

        target_circuit = (
            target_info["builder"]()
            if fixed_qubits is not None
            else target_info["builder"](num_qubits)
        )

        if circuits_equivalent(qc, target_circuit):
            return target_name

    return None




def gate_edit_distance_and_diff(user_gate_list, target_gate_list):
    """
    Classic Levenshtein edit distance between two gate sequences, treating
    each gate (name, qubits, params) as a single atomic token. Returns the
    edit distance and the actual sequence of operations (add/remove/match)
    needed to turn the user's circuit into the target -- a real, exact
    algorithm, not a heuristic guess at similarity.
    """
    n, m = len(user_gate_list), len(target_gate_list)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if user_gate_list[i - 1] == target_gate_list[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and user_gate_list[i - 1] == target_gate_list[j - 1]:
            ops.append(("match", user_gate_list[i - 1]))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(("substitute", user_gate_list[i - 1], target_gate_list[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("remove", user_gate_list[i - 1]))
            i -= 1
        else:
            ops.append(("add", target_gate_list[j - 1]))
            j -= 1

    ops.reverse()
    return dp[n][m], ops


def find_closest_target(qc):
    """
    Among all named targets compatible with qc's qubit count, find the one
    requiring the fewest gate-list edits to reach exactly. Returns
    (distance, target_name, diff_ops) or None if no compatible target exists.
    """
    user_gate_list = circuit_to_gate_list(qc)
    num_qubits = qc.num_qubits
    best = None

    for name, info in TARGETS.items():
        fixed = info["fixed_qubits"]
        if fixed is not None and fixed != num_qubits:
            continue

        target_circuit = info["builder"]() if fixed is not None else info["builder"](num_qubits)
        target_gate_list = circuit_to_gate_list(target_circuit)
        distance, ops = gate_edit_distance_and_diff(user_gate_list, target_gate_list)

        if best is None or distance < best[0]:
            best = (distance, name, ops)

    return best


def find_single_gate_completion(qc):
    """
    Check whether adding exactly ONE gate would complete a match to some
    named target. Reuses find_closest_target's underlying computation --
    this is the special case where the edit distance is exactly 1 AND
    that one edit is an addition (not a removal or substitution).
    Returns (target_name, gate_to_add) or None.
    """
    closest = find_closest_target(qc)
    if closest is None:
        return None

    distance, target_name, diff_ops = closest
    if distance != 1:
        return None

    non_match_ops = [op for op in diff_ops if op[0] != "match"]
    if len(non_match_ops) != 1 or non_match_ops[0][0] != "add":
        return None

    gate_to_add = non_match_ops[0][1]
    return target_name, gate_to_add


def superdense_coding():
    """
    The canonical superdense coding circuit, encoding the message "11" --
    the standard textbook example, since it's the only one of the four
    messages that applies BOTH possible encoding gates (X then Z), making
    it the most illustrative canonical form (the "00" case, by contrast,
    applies no encoding gate at all and is less useful as a recognizable
    pattern). Qubit 0 is Alice's qubit (encodes/sends), qubit 1 is Bob's
    (receives/decodes). Structure: shared Bell pair prep, encoding gates
    for "11", then Bob's decoding step (CX, then H on the control qubit).
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.x(0)
    qc.z(0)
    qc.cx(0, 1)
    qc.h(0)
    return qc




def w_state():
    """
    The canonical 3-qubit W-state: (|001> + |010> + |100>) / sqrt(3).
    Genuinely distinct entanglement class from GHZ -- losing any one qubit
    leaves the other two in a real, partially entangled mixed state (unlike
    GHZ, which collapses entirely to a product state if any qubit is lost).

    Uses a controlled-RY(pi/2) in place of the textbook-standard controlled-
    Hadamard, decomposed into standard RY/CX gates (no new gate type
    needed) -- verified to produce an identical result for this specific
    circuit, since the target qubit is always |0> at that point, where H
    and RY(pi/2) act identically.
    """
    theta = 2 * np.arccos(1 / np.sqrt(3))

    qc = QuantumCircuit(3)
    qc.ry(theta, 0)
    qc.ry(np.pi / 4, 1)
    qc.cx(0, 1)
    qc.ry(-np.pi / 4, 1)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.x(0)
    return qc


def grover_diffusion_2q():
    """
    The Grover diffusion operator ("inversion about the mean"), for 2 qubits.
    Core reflection step of Grover's search algorithm -- one of the most
    commonly tested building blocks in quantum algorithms coursework.
    Structure: H on all qubits, X on all qubits, CZ (the multi-controlled-Z
    reflection, which for 2 qubits is just a standard CZ), X on all qubits,
    H on all qubits again.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(1)
    qc.x(0)
    qc.x(1)
    qc.cz(0, 1)
    qc.x(0)
    qc.x(1)
    qc.h(0)
    qc.h(1)
    return qc

def deutsch_jozsa_balanced():
    """
    The Deutsch-Jozsa algorithm circuit, using the simplest standard
    'balanced' oracle example (a single CX from the input qubit to the
    output qubit) -- one specific, canonical instance, since the general
    algorithm's oracle varies by the function being tested and there's no
    single universal oracle to register. Qubit 0 is the input register,
    qubit 1 is the output register (initialized via X + H to the |-> state,
    standard for phase-kickback oracles).
    """
    qc = QuantumCircuit(2)
    qc.x(1)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.h(0)
    return qc

def qft_butterfly_2q():
    """
    The QFT 'butterfly' stage for 2 qubits: H on qubit 0, followed by a
    controlled-phase(pi/2) rotation between qubits 0 (control) and 1
    (target) -- the core repeated building block of the Quantum Fourier
    Transform. The controlled-phase gate is decomposed into RZ/CX gates
    (a standard identity: phase gates are diagonal and commute predictably
    under CX conjugation), since a general controlled-phase primitive isn't
    in this app's gate set. Verified numerically against a true CP(pi/2)
    gate before registration.
    """
    theta = np.pi / 2
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.rz(theta / 2, 0)
    qc.rz(theta / 2, 1)
    qc.cx(0, 1)
    qc.rz(-theta / 2, 1)
    qc.cx(0, 1)
    return qc

def toffoli_decomposition():
    """
    Standard Toffoli (CCX) decomposition into H, CX, T, and Z gates only
    (Nielsen & Chuang construction). No T-dagger primitive exists in this
    app's gate set, so Tdg is substituted as Z * T^3 (T has order 8, and
    T^4 = Z, so T^-1 = T^7 = Z*T^3; T and Z commute since both diagonal).
    Verified numerically to exactly match a true CCX gate before
    registration. 24 gates total -- the largest single canonical circuit
    in this registry, reflecting genuine Toffoli decomposition complexity,
    not an implementation shortcut.
    """
    def apply_tdg(qc, qubit):
        qc.t(qubit)
        qc.t(qubit)
        qc.t(qubit)
        qc.z(qubit)

    qc = QuantumCircuit(3)
    qc.h(2)
    qc.cx(1, 2)
    apply_tdg(qc, 2)
    qc.cx(0, 2)
    qc.t(2)
    qc.cx(1, 2)
    apply_tdg(qc, 2)
    qc.cx(0, 2)
    qc.t(1)
    qc.t(2)
    qc.cx(0, 1)
    qc.h(2)
    qc.t(0)
    apply_tdg(qc, 1)
    qc.cx(0, 1)
    return qc

# --- Quick test ---
if __name__ == "__main__":
    attempt_1 = QuantumCircuit(2)
    attempt_1.h(0)
    attempt_1.cx(0, 1)
    print("Attempt 1 match:", find_matching_target(attempt_1))

    attempt_2 = QuantumCircuit(3)
    attempt_2.h(0)
    attempt_2.cx(0, 1)
    attempt_2.cx(0, 2)
    print("Attempt 2 match:", find_matching_target(attempt_2))

    attempt_3 = QuantumCircuit(3)
    attempt_3.h(0)
    attempt_3.cx(0, 1)
    print("Attempt 3 match:", find_matching_target(attempt_3))

    print("\n--- Testing instantiate_named_circuit ---")
    result = instantiate_named_circuit("bell_state", [3, 5])
    print("Bell state on qubits (3, 5):", result)

    result2 = instantiate_named_circuit("ghz_state", [1, 2, 3, 4])
    print("4-qubit GHZ on qubits (1,2,3,4):", result2)

    print("\n--- Testing find_closest_target ---")
    near_miss = QuantumCircuit(3)
    near_miss.h(0)
    near_miss.cx(0, 1)
    # missing the second CX to complete a 3-qubit GHZ state
    result = find_closest_target(near_miss)
    print(f"Closest target: {result[1]}, edit distance: {result[0]}")
    print("Diff operations:")
    for op in result[2]:
        print(f"  {op}")

    print("\n--- Testing find_closest_target (larger gap) ---")
    bigger_gap = QuantumCircuit(3)
    bigger_gap.h(0)
    result2 = find_closest_target(bigger_gap)
    print(f"Closest target: {result2[1]}, edit distance: {result2[0]}")
    print("Diff operations:")
    for op in result2[2]:
        print(f"  {op}")

    print("\n--- Testing find_closest_target (messy, arbitrary circuit) ---")
    messy = QuantumCircuit(3)
    messy.x(0)
    messy.h(1)
    messy.z(2)
    messy.s(0)
    messy.cx(1, 2)
    messy.y(0)
    messy.h(2)
    messy.cx(0, 1)
    messy.t(1)
    messy.z(0)
    result3 = find_closest_target(messy)
    print(f"Closest target: {result3[1]}, edit distance: {result3[0]}")
    print("Diff operations:")
    for op in result3[2]:
        print(f"  {op}")

    print("\n--- Testing find_single_gate_completion ---")
    completion = find_single_gate_completion(near_miss)
    print("Single-gate completion:", completion)

    print("\n--- Testing superdense_coding ---")
    sdc = superdense_coding()
    print(sdc.draw())
    print("Gate count:", len(circuit_to_gate_list(sdc)))

    print("\n--- Testing w_state ---")
    w = w_state()
    print(w.draw())
    dirac = format_dirac_notation(w)
    print("Dirac notation:", dirac)
    print("Gate count:", len(circuit_to_gate_list(w)))
    print("Correctly entangled (not GHZ-collapse type):", is_fully_entangled(w))

    print("\n--- Testing grover_diffusion_2q ---")
    grover = grover_diffusion_2q()
    print(grover.draw())
    print("Gate count:", len(circuit_to_gate_list(grover)))

    print("\n--- Testing deutsch_jozsa_balanced ---")
    dj = deutsch_jozsa_balanced()
    print(dj.draw())
    print("Gate count:", len(circuit_to_gate_list(dj)))

    print("\n--- Testing qft_butterfly_2q ---")
    qft = qft_butterfly_2q()
    print(qft.draw())
    print("Gate count:", len(circuit_to_gate_list(qft)))

    print("\n--- Testing toffoli_decomposition ---")
    toffoli = toffoli_decomposition()
    print(toffoli.draw())
    print("Gate count:", len(circuit_to_gate_list(toffoli)))

    from qiskit.quantum_info import Operator
    import numpy as np

    true_ccx = QuantumCircuit(3)
    true_ccx.ccx(0, 1, 2)
    actual_matrix = Operator(toffoli).data
    expected_matrix = Operator(true_ccx).data
    idx = np.unravel_index(np.argmax(np.abs(expected_matrix)), expected_matrix.shape)
    phase_diff = actual_matrix[idx] / expected_matrix[idx]
    adjusted = actual_matrix / phase_diff
    matches_true_toffoli = np.allclose(adjusted, expected_matrix, atol=1e-6)
    print("Toffoli decomposition matches true CCX gate:", matches_true_toffoli)