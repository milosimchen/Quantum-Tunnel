"""
Interview Prep practice challenges.

Every challenge is graded here, in plain Python, with the same verification
engine used everywhere else (circuits_equivalent for operations, exact
statevector comparison for state preparation). The LLM is never involved in
deciding whether an attempt passed -- that's the same hard boundary as FR-14.

Two kinds of check:
  - "state":   the attempt, applied to |0...0> (after any fixed `setup` gates,
               and followed by any fixed `teardown` gates), must produce the
               same state as the reference, up to global phase.
  - "unitary": the attempt must implement the same operation as the
               reference, up to global phase (works for every input state).

On top of that, optional constraints: allowed gate set, max gate count, max
depth, and which qubits the attempt may touch.

Qubit-ordering note for anyone writing prompts: Qiskit labels basis states
|q_{n-1} ... q_1 q_0>, so qubit 0 is the RIGHTMOST digit. Prompts below either
use states that read the same both ways, or say explicitly which qubit is which.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from equivalence import circuits_equivalent, format_dirac_notation
from simplify import gate_list_to_circuit

SKILLS = {
    "state_prep": "State preparation",
    "identities": "Gate identities",
    "entanglement": "Entanglement",
    "protocols": "Protocols",
    "optimization": "Optimization",
}

DIFFICULTIES = ["warm-up", "core", "challenge"]

# Gate tuples use the same (name, qubits, params) shape as simplify.py.
CHALLENGES = [
    # ---- warm-up ---------------------------------------------------------
    {
        "id": "flip",
        "title": "Flip a bit",
        "skill": "state_prep",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Starting from |0⟩, prepare the state |1⟩.",
        "check": "state",
        "reference": [("x", (0,), ())],
        "hints": ["Which Pauli gate is the quantum NOT?"],
        "explanation": "X maps |0⟩ to |1⟩ and back, just like a classical NOT.",
    },
    {
        "id": "plus",
        "title": "Equal superposition",
        "skill": "state_prep",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Starting from |0⟩, prepare |+⟩ = (|0⟩ + |1⟩)/√2.",
        "check": "state",
        "reference": [("h", (0,), ())],
        "hints": ["One gate is enough. It's the most-used gate in the field."],
        "explanation": "H maps |0⟩ to |+⟩ and |1⟩ to |−⟩. It switches between the Z and X bases.",
    },
    {
        "id": "minus",
        "title": "Negative phase",
        "skill": "state_prep",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Starting from |0⟩, prepare |−⟩ = (|0⟩ − |1⟩)/√2.",
        "check": "state",
        "reference": [("x", (0,), ()), ("h", (0,), ())],
        "hints": [
            "H|1⟩ = |−⟩. How do you get to |1⟩ first?",
            "Alternatively: make |+⟩, then flip the sign of the |1⟩ part.",
        ],
        "explanation": "Either X then H, or H then Z. Both work, which is a nice illustration that HX = ZH.",
    },
    {
        "id": "z_from_s",
        "title": "Z from S",
        "skill": "identities",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Implement the Z gate using only S gates.",
        "check": "unitary",
        "reference": [("z", (0,), ())],
        "allowed_gates": ["s"],
        "hints": ["S is a quarter turn of phase; Z is a half turn."],
        "solution": [("s", (0,), ()), ("s", (0,), ())],
        "explanation": "S² = Z. S adds a phase of i to |1⟩; doing it twice adds i² = −1.",
    },
    {
        "id": "x_from_hz",
        "title": "X from H and Z",
        "skill": "identities",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Implement the X gate using only H and Z gates.",
        "check": "unitary",
        "reference": [("x", (0,), ())],
        "allowed_gates": ["h", "z"],
        "hints": ["H swaps the roles of X and Z. Try sandwiching."],
        "solution": [("h", (0,), ()), ("z", (0,), ()), ("h", (0,), ())],
        "explanation": "HZH = X. Conjugating by H turns a phase flip into a bit flip.",
    },
    # ---- core ------------------------------------------------------------
    {
        "id": "plus_i",
        "title": "Complex phase",
        "skill": "state_prep",
        "difficulty": "core",
        "num_qubits": 1,
        "prompt": "Starting from |0⟩, prepare |+i⟩ = (|0⟩ + i|1⟩)/√2.",
        "check": "state",
        "reference": [("h", (0,), ()), ("s", (0,), ())],
        "hints": ["Start from |+⟩. Which gate multiplies |1⟩ by i?"],
        "explanation": "H then S. S = diag(1, i), so it turns |+⟩ into |+i⟩, a point on the Y axis of the Bloch sphere.",
    },
    {
        "id": "bell_phi_plus",
        "title": "Bell pair",
        "skill": "entanglement",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "Prepare the Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2 using at most 2 gates.",
        "check": "state",
        "reference": [("h", (0,), ()), ("cx", (0, 1), ())],
        "max_gates": 2,
        "hints": [
            "First create a superposition on one qubit.",
            "Then copy that qubit's value onto the other with a controlled gate.",
        ],
        "explanation": "H on the control creates (|0⟩+|1⟩)/√2; CNOT copies it, giving (|00⟩+|11⟩)/√2.",
    },
    {
        "id": "bell_psi_minus",
        "title": "The singlet",
        "skill": "entanglement",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "Prepare the singlet state |Ψ−⟩ = (|01⟩ − |10⟩)/√2.",
        "check": "state",
        "reference": [("x", (0,), ()), ("x", (1,), ()), ("h", (0,), ()), ("cx", (0, 1), ())],
        "hints": [
            "Start from the Φ+ recipe and think about which inputs to flip first.",
            "H on |1⟩ gives a minus sign. CNOT on a |1⟩ target makes the two qubits disagree.",
        ],
        "explanation": "Flip both qubits to |11⟩, then H and CNOT. The H on |1⟩ supplies the minus sign, and the flipped target makes the qubits anti-correlated.",
    },
    {
        "id": "ghz3",
        "title": "Three-way entanglement",
        "skill": "entanglement",
        "difficulty": "core",
        "num_qubits": 3,
        "prompt": "Prepare the GHZ state (|000⟩ + |111⟩)/√2 on 3 qubits.",
        "check": "state",
        "reference": [("h", (0,), ()), ("cx", (0, 1), ()), ("cx", (0, 2), ())],
        "hints": ["It's the Bell pair recipe with one more CNOT."],
        "explanation": "H then a CNOT from the superposed qubit to each of the others. All three end up perfectly correlated.",
    },
    {
        "id": "cz_from_cx",
        "title": "CZ from CNOT",
        "skill": "identities",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "Implement CZ on qubits 0 and 1 using only H and CX gates.",
        "check": "unitary",
        "reference": [("cz", (0, 1), ())],
        "allowed_gates": ["h", "cx"],
        "hints": ["You already know HXH = Z. What happens if you sandwich the target of a CNOT?"],
        "solution": [("h", (1,), ()), ("cx", (0, 1), ()), ("h", (1,), ())],
        "explanation": "H on the target, CX, H on the target. CNOT is a controlled-X, and conjugating the X by H turns it into a Z.",
    },
    {
        "id": "undo_bell",
        "title": "Undo the entanglement",
        "skill": "entanglement",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "The qubits start in the Bell state (|00⟩ + |11⟩)/√2 (already prepared for you). Add gates that turn it back into |00⟩.",
        "check": "state",
        "setup": [("h", (0,), ()), ("cx", (0, 1), ())],
        "reference": [("cx", (0, 1), ()), ("h", (0,), ())],
        "target_override": [],
        "hints": ["Every gate is reversible. Run the preparation backwards."],
        "explanation": "CX then H: the preparation in reverse order (both gates are their own inverses). This is the core of a Bell measurement.",
    },
    # ---- challenge -------------------------------------------------------
    {
        "id": "swap_from_cx",
        "title": "SWAP from CNOTs",
        "skill": "identities",
        "difficulty": "challenge",
        "num_qubits": 2,
        "prompt": "Implement SWAP on qubits 0 and 1 using only CX gates, with at most 3 gates.",
        "check": "unitary",
        "reference": [("swap", (0, 1), ())],
        "allowed_gates": ["cx"],
        "max_gates": 3,
        "hints": [
            "Think of the classical XOR-swap trick: a ^= b; b ^= a; a ^= b.",
            "Alternate the direction of each CNOT.",
        ],
        "solution": [("cx", (0, 1), ()), ("cx", (1, 0), ()), ("cx", (0, 1), ())],
        "explanation": "CX(0,1), CX(1,0), CX(0,1). This is exactly the XOR-swap, and it's how SWAP is compiled on hardware without a native SWAP.",
    },
    {
        "id": "minus_i_clifford",
        "title": "Only H and S",
        "skill": "identities",
        "difficulty": "challenge",
        "num_qubits": 1,
        "prompt": "Prepare |−i⟩ = (|0⟩ − i|1⟩)/√2 using only H and S gates.",
        "check": "state",
        "reference": [("h", (0,), ()), ("s", (0,), ()), ("s", (0,), ()), ("s", (0,), ())],
        "allowed_gates": ["h", "s"],
        "hints": [
            "You need S† (a phase of −i), but you only have S.",
            "S has order 4: S⁴ = I. So what is S†?",
        ],
        "explanation": "H then three S gates. S⁴ = I, so S³ = S† = diag(1, −i).",
    },
    {
        "id": "superdense_11",
        "title": "Superdense coding",
        "skill": "protocols",
        "difficulty": "challenge",
        "num_qubits": 2,
        "prompt": (
            "Alice (qubit 0) and Bob (qubit 1) share the Bell state (|00⟩ + |11⟩)/√2, already prepared. "
            "After your gates, Bob decodes with CX(0,1) then H on qubit 0. "
            "Using gates on Alice's qubit only, encode the message so Bob measures |11⟩."
        ),
        "check": "state",
        "setup": [("h", (0,), ()), ("cx", (0, 1), ())],
        "teardown": [("cx", (0, 1), ()), ("h", (0,), ())],
        "reference": [("x", (0,), ()), ("z", (0,), ())],
        "target_override": [("x", (0,), ()), ("x", (1,), ())],
        "allowed_qubits": [0],
        "hints": [
            "Two classical bits, four Bell states. Each Pauli on Alice's qubit picks a different one.",
            "X flips which basis states are paired; Z flips the relative sign. You need both.",
        ],
        "explanation": "X then Z on Alice's qubit turns Φ+ into Ψ−, which Bob's decoding maps to |11⟩. One qubit sent, two bits received.",
    },
    {
        "id": "ghz4_shallow",
        "title": "Shallow GHZ",
        "skill": "optimization",
        "difficulty": "challenge",
        "num_qubits": 4,
        "prompt": "Prepare the 4-qubit GHZ state (|0000⟩ + |1111⟩)/√2 with circuit depth at most 3.",
        "check": "state",
        "reference": [
            ("h", (0,), ()),
            ("cx", (0, 1), ()),
            ("cx", (0, 2), ()),
            ("cx", (1, 3), ()),
        ],
        "max_depth": 3,
        "hints": [
            "A chain of CNOTs from qubit 0 works but has depth 4.",
            "Once two qubits are entangled, both can act as controls at the same time.",
        ],
        "explanation": "After H and CX(0,1), qubits 0 and 1 both carry the superposition, so CX(0,2) and CX(1,3) run in parallel. Doubling the entangled set each layer gives depth log₂(n) + 1.",
    },
]

CHALLENGES_BY_ID = {c["id"]: c for c in CHALLENGES}

# Fields that would give the answer away; never sent to the client.
_PRIVATE_FIELDS = {"reference", "solution", "setup", "teardown", "target_override", "explanation"}


def public_challenge(challenge):
    """Challenge data safe to send before the user has solved it."""
    data = {k: v for k, v in challenge.items() if k not in _PRIVATE_FIELDS}
    data["skill_label"] = SKILLS[challenge["skill"]]
    data["has_setup"] = bool(challenge.get("setup"))
    data["has_teardown"] = bool(challenge.get("teardown"))
    return data


def _circuit(gate_list, num_qubits):
    return gate_list_to_circuit(list(gate_list), num_qubits)


def _states_equal_up_to_phase(sv_a, sv_b, tolerance=1e-8):
    # |<a|b>| = 1 exactly when the two normalized states differ only by a global phase.
    return abs(abs(np.vdot(sv_a.data, sv_b.data)) - 1) < tolerance


def _target_circuit(challenge):
    """The full circuit whose output the attempt must match (state checks)."""
    n = challenge["num_qubits"]
    if "target_override" in challenge:
        return _circuit(challenge["target_override"], n)
    gates = list(challenge.get("setup", [])) + list(challenge["reference"]) + list(challenge.get("teardown", []))
    return _circuit(gates, n)


def check_attempt(challenge_id, attempt_gates):
    """
    Grade an attempt. attempt_gates is a list of (name, qubits, params) tuples.

    Returns a dict with an overall `passed` flag and one entry per individual
    check, so the UI can show exactly which requirement failed. Every value
    here is computed, none is generated by an LLM.
    """
    challenge = CHALLENGES_BY_ID.get(challenge_id)
    if challenge is None:
        raise KeyError(f"Unknown challenge: {challenge_id}")

    n = challenge["num_qubits"]
    checks = []

    # Structural validity first: a gate on a qubit that doesn't exist can't be simulated.
    for name, qubits, _params in attempt_gates:
        if any(q < 0 or q >= n for q in qubits):
            return {
                "passed": False,
                "checks": [{
                    "label": "Qubits in range",
                    "passed": False,
                    "detail": f"This challenge uses {n} qubit(s) (0–{n - 1}), but a {name.upper()} gate uses qubit(s) {list(qubits)}.",
                }],
                "your_state": None,
            }

    attempt_circuit = _circuit(attempt_gates, n)

    if "allowed_gates" in challenge:
        allowed = set(challenge["allowed_gates"])
        used = {name for name, _, _ in attempt_gates}
        disallowed = sorted(used - allowed)
        checks.append({
            "label": f"Only uses {', '.join(g.upper() for g in challenge['allowed_gates'])}",
            "passed": not disallowed,
            "detail": f"Not allowed here: {', '.join(g.upper() for g in disallowed)}." if disallowed else None,
        })

    if "allowed_qubits" in challenge:
        allowed_q = set(challenge["allowed_qubits"])
        touched = sorted({q for _, qubits, _ in attempt_gates for q in qubits} - allowed_q)
        checks.append({
            "label": f"Only touches qubit(s) {', '.join(map(str, challenge['allowed_qubits']))}",
            "passed": not touched,
            "detail": f"Also touches qubit(s) {', '.join(map(str, touched))}." if touched else None,
        })

    if "max_gates" in challenge:
        count = len(attempt_gates)
        checks.append({
            "label": f"At most {challenge['max_gates']} gates",
            "passed": count <= challenge["max_gates"],
            "detail": f"Uses {count} gates.",
        })

    if "max_depth" in challenge:
        depth = attempt_circuit.depth()
        checks.append({
            "label": f"Depth at most {challenge['max_depth']}",
            "passed": depth <= challenge["max_depth"],
            "detail": f"Depth is {depth}.",
        })

    if challenge["check"] == "unitary":
        reference = _circuit(challenge["reference"], n)
        matches = bool(circuits_equivalent(reference, attempt_circuit))
        checks.append({
            "label": "Implements the right operation (up to global phase)",
            "passed": matches,
            "detail": None if matches else "The circuit's unitary differs from the target operation on at least one input state.",
        })
        full_attempt = attempt_circuit
    else:
        full_attempt = _circuit(
            list(challenge.get("setup", [])) + list(attempt_gates) + list(challenge.get("teardown", [])),
            n,
        )
        matches = bool(_states_equal_up_to_phase(Statevector(full_attempt), Statevector(_target_circuit(challenge))))
        checks.append({
            "label": "Produces the target state (up to global phase)",
            "passed": matches,
            "detail": None,
        })

    passed = bool(all(c["passed"] for c in checks))

    # The actual output state is exact, computed feedback -- safe to show on a miss.
    your_state = format_dirac_notation(full_attempt) if n <= 5 else None

    result = {
        "passed": passed,
        "checks": checks,
        "your_state": your_state,
        "gate_count": len(attempt_gates),
        "depth": attempt_circuit.depth(),
    }
    if passed:
        result["explanation"] = challenge["explanation"]
    return result


def reveal_solution(challenge_id):
    """One known-good answer, for 'show solution'. Not the only correct answer."""
    challenge = CHALLENGES_BY_ID[challenge_id]
    gates = challenge.get("solution", challenge["reference"])
    return {
        "gates": [{"name": g, "qubits": list(q), "params": list(p)} for g, q, p in gates],
        "explanation": challenge["explanation"],
    }
