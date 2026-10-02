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

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from equivalence import circuits_equivalent, format_dirac_notation
from simplify import gate_list_to_circuit
from hardware import (
    DEVICES, public_device, coupling_violations, two_qubit_gate_count,
    noisy_state_fidelity, solve_numeric,
)

SKILLS = {
    "state_prep": "State preparation",
    "identities": "Gate identities",
    "entanglement": "Entanglement",
    "protocols": "Protocols",
    "optimization": "Optimization",
}

SKILLS.update({
    "native_gates": "Native gates",
    "routing": "Routing",
    "noise": "Noise & fidelity",
    "mitigation": "Error mitigation",
    "algorithms": "Algorithms",
    "qec": "Error correction",
    "simulation": "Hamiltonian simulation",
})

DIFFICULTIES = ["warm-up", "core", "challenge"]

# Tracks group challenges on the Interview Prep page. Challenges without a
# "track" key belong to "foundations".
TRACKS = {
    "foundations": "Circuit fundamentals",
    "hardware": "Real hardware",
    "advanced": "Advanced algorithms & QEC",
}

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

# ---- Real hardware track ----------------------------------------------------
# Devices, noise and calculation solvers live in hardware.py. Fidelity targets
# were calibrated so a well-routed circuit passes and a naive one fails under
# that noise model (see test_practice.py for both sides of each threshold).
PI = math.pi

HARDWARE_CHALLENGES = [
    {
        "id": "hw_t1_decay",
        "title": "How long does |1⟩ last?",
        "track": "hardware",
        "kind": "numeric",
        "skill": "noise",
        "difficulty": "warm-up",
        "prompt": "A qubit has T1 = 100 µs. It starts in |1⟩. What is the probability it is still in |1⟩ after 20 µs? Give a decimal between 0 and 1.",
        "numeric": {"solver": "t1_survival", "args": {"t1_us": 100.0, "t_us": 20.0}},
        "tolerance": 0.003,
        "hints": ["Energy relaxation is exponential decay with time constant T1."],
        "explanation": "P = e^(−t/T1) = e^(−0.2) ≈ 0.819. Even a short wait costs almost a fifth of the excited population, which is why idle time matters.",
    },
    {
        "id": "hw_native_h",
        "title": "Hadamard, natively",
        "track": "hardware",
        "skill": "native_gates",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "IBM-style chips don't have an H gate. Implement H using only RZ and SX.",
        "check": "unitary",
        "reference": [("h", (0,), ())],
        "solution": [("rz", (0,), (PI / 2,)), ("sx", (0,), ()), ("rz", (0,), (PI / 2,))],
        "allowed_gates": ["rz", "sx"],
        "hints": [
            "SX is a quarter turn about X (√X). RZ turns about Z by any angle you choose.",
            "Try sandwiching one SX between two RZ gates of the same angle.",
        ],
        "explanation": "H = RZ(π/2) · SX · RZ(π/2), up to global phase. Compilers rewrite every H in your circuit like this, and RZ is free on hardware (it's done in software as a frame change).",
    },
    {
        "id": "hw_native_y",
        "title": "Y from X and RZ",
        "track": "hardware",
        "skill": "native_gates",
        "difficulty": "warm-up",
        "num_qubits": 1,
        "prompt": "Implement the Y gate using only X and RZ.",
        "check": "unitary",
        "reference": [("y", (0,), ())],
        "solution": [("rz", (0,), (PI,)), ("x", (0,), ())],
        "allowed_gates": ["x", "rz"],
        "hints": ["RZ(π) equals Z up to global phase. How do X and Z combine into Y?"],
        "explanation": "RZ(π) then X gives X·Z = −iY: Y up to global phase.",
    },
    {
        "id": "hw_two_qubit_budget",
        "title": "The CNOT budget",
        "track": "hardware",
        "kind": "numeric",
        "skill": "noise",
        "difficulty": "core",
        "prompt": "Each CNOT on a chip fails with probability 2%, independently. What is the probability that a circuit with 20 CNOTs runs with no CNOT error at all?",
        "numeric": {"solver": "two_qubit_gate_success", "args": {"error_per_gate": 0.02, "count": 20}},
        "tolerance": 0.003,
        "hints": ["Each gate succeeds with probability 0.98. All 20 must succeed."],
        "explanation": "0.98^20 ≈ 0.668. One in three runs has at least one two-qubit error, which is why CNOT count is the first thing compilers try to cut.",
    },
    {
        "id": "hw_route_cx",
        "title": "Route around a gap",
        "track": "hardware",
        "skill": "routing",
        "difficulty": "core",
        "device": "line3",
        "num_qubits": 3,
        "prompt": "On the Line-3 chip, qubits 0 and 2 aren't connected. Implement a CNOT from qubit 0 to qubit 2 using only gates the chip allows, leaving every qubit where it started.",
        "check": "unitary",
        "reference": [("cx", (0, 2), ())],
        "solution": [("swap", (0, 1), ()), ("cx", (1, 2), ()), ("swap", (0, 1), ())],
        "allowed_gates": ["cx", "swap"],
        "hints": [
            "A SWAP can move qubit 0's state next to qubit 2.",
            "Swap it over, do the CNOT, then swap it back.",
        ],
        "explanation": "SWAP(0,1), CX(1,2), SWAP(0,1). This is exactly what a router inserts. It works, but each SWAP is 3 CNOTs on hardware: 7 two-qubit gates for one logical CNOT.",
    },
    {
        "id": "hw_ghz3_line",
        "title": "GHZ on a line",
        "track": "hardware",
        "skill": "noise",
        "difficulty": "core",
        "device": "line3",
        "num_qubits": 3,
        "prompt": "Prepare the GHZ state (|000⟩ + |111⟩)/√2 on the Line-3 chip with fidelity at least 0.95 under its noise. Two-qubit gates only work between connected qubits.",
        "check": "state",
        "reference": [("h", (0,), ()), ("cx", (0, 1), ()), ("cx", (0, 2), ())],
        "solution": [("h", (0,), ()), ("cx", (0, 1), ()), ("cx", (1, 2), ())],
        "allowed_gates": ["h", "x", "rz", "sx", "cx", "swap"],
        "min_fidelity": 0.95,
        "hints": [
            "The textbook recipe uses CX(0,2), which this chip can't do directly.",
            "Once qubit 1 holds a copy, it can pass the value along to qubit 2.",
        ],
        "explanation": "H(0), CX(0,1), CX(1,2): chain the copies along the line instead of fanning out from qubit 0. No SWAPs needed, so fidelity stays around 0.96.",
    },
    {
        "id": "hw_readout_mitigation",
        "title": "Undo readout error",
        "track": "hardware",
        "kind": "numeric",
        "skill": "mitigation",
        "difficulty": "core",
        "prompt": "Calibration shows a qubit is read as 1 when it's really 0 with probability 0.05, and read as 0 when it's really 1 with probability 0.10. In your experiment, 30% of shots read 1. What is the corrected probability that the qubit was really 1?",
        "numeric": {"solver": "readout_mitigated_p1", "args": {"p_read1_given0": 0.05, "p_read0_given1": 0.10, "measured_p1": 0.30}},
        "tolerance": 0.004,
        "hints": [
            "Write P(read 1) in terms of the true P(1): some 1s come from real 1s read correctly, some from 0s misread.",
            "P(read 1) = 0.05·(1 − p) + 0.90·p. Solve for p.",
        ],
        "explanation": "0.30 = 0.05 + 0.85p, so p ≈ 0.294. This is single-qubit readout mitigation: invert the calibration (confusion) matrix. Many qubits need a bigger matrix or tensored approximations.",
    },
    {
        "id": "hw_native_cz",
        "title": "CZ from native gates",
        "track": "hardware",
        "skill": "native_gates",
        "difficulty": "challenge",
        "num_qubits": 2,
        "prompt": "Implement CZ on qubits 0 and 1 using only RZ, SX and CX.",
        "check": "unitary",
        "reference": [("cz", (0, 1), ())],
        "solution": [
            ("rz", (1,), (PI / 2,)), ("sx", (1,), ()), ("rz", (1,), (PI / 2,)),
            ("cx", (0, 1), ()),
            ("rz", (1,), (PI / 2,)), ("sx", (1,), ()), ("rz", (1,), (PI / 2,)),
        ],
        "allowed_gates": ["rz", "sx", "cx"],
        "hints": [
            "CZ = H·CX·H on the target. But H isn't native.",
            "You already built H from RZ and SX in an earlier challenge.",
        ],
        "explanation": "Replace each H in H·CX·H with RZ(π/2)·SX·RZ(π/2). Seven native gates for one CZ, but only one of them is a two-qubit gate.",
    },
    {
        "id": "hw_cx_no_swap",
        "title": "A cheaper long-range CNOT",
        "track": "hardware",
        "skill": "routing",
        "difficulty": "challenge",
        "device": "line3",
        "num_qubits": 3,
        "prompt": "On Line-3, implement CNOT from qubit 0 to qubit 2 again, but with at most 4 two-qubit gates. (Each SWAP counts as 3.)",
        "check": "unitary",
        "reference": [("cx", (0, 2), ())],
        "solution": [("cx", (0, 1), ()), ("cx", (1, 2), ()), ("cx", (0, 1), ()), ("cx", (1, 2), ())],
        "allowed_gates": ["cx", "swap"],
        "max_two_qubit_gates": 4,
        "hints": [
            "Two SWAPs cost 6. You need a trick that never moves the state.",
            "CX(0,1) then CX(1,2) puts q0 ⊕ q1 into qubit 2's XOR. What cancels the unwanted q1 part?",
        ],
        "explanation": "CX(0,1), CX(1,2), CX(0,1), CX(1,2): the q1 contributions cancel and only q0 is XORed into q2. Four CNOTs instead of seven, so roughly half the two-qubit error.",
    },
    {
        "id": "hw_ghz5_fidelity",
        "title": "GHZ-5 under noise",
        "track": "hardware",
        "skill": "noise",
        "difficulty": "challenge",
        "device": "line5",
        "num_qubits": 5,
        "prompt": "Prepare the 5-qubit GHZ state (|00000⟩ + |11111⟩)/√2 on Line-5 with fidelity at least 0.912 under its noise. Idle qubits decay too, so time counts.",
        "check": "state",
        "reference": [("h", (0,), ()), ("cx", (0, 1), ()), ("cx", (1, 2), ()), ("cx", (2, 3), ()), ("cx", (3, 4), ())],
        "solution": [("h", (2,), ()), ("cx", (2, 1), ()), ("cx", (2, 3), ()), ("cx", (1, 0), ()), ("cx", (3, 4), ())],
        "allowed_gates": ["h", "x", "rz", "sx", "cx", "swap"],
        "min_fidelity": 0.912,
        "hints": [
            "A chain from qubit 0 works but takes 5 layers, and the far qubits wait the whole time.",
            "Start the superposition in the middle and grow outwards in both directions at once.",
        ],
        "explanation": "H on qubit 2, then spread left and right: the last two CNOTs run in parallel, so the circuit is one layer shallower and the outer qubits idle less. Same gate count, higher fidelity: depth matters on real hardware.",
    },
    {
        "id": "hw_zne",
        "title": "Zero-noise extrapolation",
        "track": "hardware",
        "kind": "numeric",
        "skill": "mitigation",
        "difficulty": "challenge",
        "prompt": "You measure an expectation value of 0.80 at the device's normal noise level (scale 1) and 0.64 after deliberately tripling the noise (scale 3). Using a straight-line fit, estimate the zero-noise value.",
        "numeric": {"solver": "zne_linear", "args": {"scale_a": 1.0, "value_a": 0.80, "scale_b": 3.0, "value_b": 0.64}},
        "tolerance": 0.004,
        "hints": ["The slope is (0.64 − 0.80) / (3 − 1). Extend the line back to scale 0."],
        "explanation": "Slope −0.08 per unit of noise, so the zero-noise estimate is 0.80 + 0.08 = 0.88. Real ZNE amplifies noise by gate folding and often fits more than two points, trading extra shots for less bias.",
    },
]

CHALLENGES.extend(HARDWARE_CHALLENGES)


# ---- Advanced track ---------------------------------------------------------
# Each reference was checked against Qiskit's own implementation where one
# exists (QFTGate, rzz); see test_practice.py.

ADVANCED_CHALLENGES = [
    {
        "id": "adv_rzz",
        "title": "Build a ZZ interaction",
        "track": "advanced",
        "skill": "simulation",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "Implement RZZ(π/2) = exp(−i·(π/4)·Z⊗Z), the building block of Hamiltonian simulation and QAOA, using only CX and RZ.",
        "check": "unitary",
        "reference": [("rzz", (0, 1), (PI / 2,))],
        "solution": [("cx", (0, 1), ()), ("rz", (1,), (PI / 2,)), ("cx", (0, 1), ())],
        "allowed_gates": ["cx", "rz"],
        "hints": [
            "Z⊗Z only cares about the parity of the two qubits.",
            "Compute the parity onto one qubit with a CNOT, rotate it, then uncompute.",
        ],
        "explanation": "CX(0,1), RZ(π/2) on qubit 1, CX(0,1). The CNOT writes the parity into qubit 1, RZ applies the parity-dependent phase, and the second CNOT restores the qubits. Every Pauli-string rotation in a Trotter step is built this way.",
    },
    {
        "id": "adv_grover2",
        "title": "One Grover iteration",
        "track": "advanced",
        "skill": "algorithms",
        "difficulty": "core",
        "num_qubits": 2,
        "prompt": "The search register starts in |++⟩ (prepared for you). Add one Grover iteration, an oracle marking |11⟩ followed by the diffusion operator, so a measurement finds |11⟩ with certainty. Use only H, X and CZ.",
        "check": "unitary",
        "setup": [("h", (0,), ()), ("h", (1,), ())],
        "reference": [
            ("cz", (0, 1), ()),
            ("h", (0,), ()), ("h", (1,), ()), ("x", (0,), ()), ("x", (1,), ()),
            ("cz", (0, 1), ()),
            ("x", (0,), ()), ("x", (1,), ()), ("h", (0,), ()), ("h", (1,), ()),
        ],
        "allowed_gates": ["h", "x", "cz"],
        "hints": [
            "The oracle flips the sign of |11⟩ only. Which single gate does exactly that?",
            "Diffusion reflects about |++⟩: H on both, flip the sign of |00⟩ (X, CZ, X), H on both.",
        ],
        "explanation": "Oracle: CZ. Diffusion: H⊗H, X⊗X, CZ, X⊗X, H⊗H. For N = 4 a single iteration rotates the state exactly onto the marked item. Graded on the full operator, so any circuit equal to oracle-then-diffusion passes.",
    },
    {
        "id": "adv_qft2",
        "title": "Two-qubit QFT",
        "track": "advanced",
        "skill": "algorithms",
        "difficulty": "challenge",
        "num_qubits": 2,
        "prompt": "Implement the 2-qubit quantum Fourier transform, matching Qiskit's convention (qubit 0 is the least significant bit), using H, controlled-phase (CP) and SWAP.",
        "check": "unitary",
        "reference": [("h", (1,), ()), ("cp", (0, 1), (PI / 2,)), ("h", (0,), ()), ("swap", (0, 1), ())],
        "allowed_gates": ["h", "cp", "swap"],
        "hints": [
            "Start with H on the most significant qubit (qubit 1).",
            "Then a controlled phase of π/2 between the qubits, H on qubit 0, and fix the bit order at the end.",
        ],
        "explanation": "H(1), CP(π/2) between 0 and 1, H(0), SWAP. Without the SWAP you get the QFT with reversed output order, a convention mismatch interviewers like to check.",
    },
    {
        "id": "adv_bitflip_syndrome",
        "title": "Extract a syndrome",
        "track": "advanced",
        "skill": "qec",
        "difficulty": "challenge",
        "num_qubits": 5,
        "prompt": "Qubits 0–2 hold the bit-flip codeword for |+⟩, (|000⟩ + |111⟩)/√2, and an X error has hit one data qubit (prepared for you). Using only CX, measure the parities Z₀Z₁ into ancilla 3 and Z₁Z₂ into ancilla 4, without disturbing the encoded superposition.",
        "check": "state",
        "setup": [("h", (0,), ()), ("cx", (0, 1), ()), ("cx", (0, 2), ()), ("x", (1,), ())],
        "reference": [("cx", (0, 3), ()), ("cx", (1, 3), ()), ("cx", (1, 4), ()), ("cx", (2, 4), ())],
        "allowed_gates": ["cx"],
        "hints": [
            "An ancilla that receives CNOTs from two data qubits ends up holding their XOR.",
            "Copying a single data qubit onto an ancilla entangles it with the superposition, which damages the code.",
        ],
        "explanation": "CX(0,3), CX(1,3) put q0⊕q1 on ancilla 3; CX(1,4), CX(2,4) put q1⊕q2 on ancilla 4. Both read 1 in both branches of the superposition, so the ancillas stay unentangled and point to qubit 1 without revealing the logical state.",
    },
    {
        "id": "adv_qpe_s",
        "title": "Estimate a phase",
        "track": "advanced",
        "skill": "algorithms",
        "difficulty": "challenge",
        "num_qubits": 3,
        "prompt": "Qubit 2 holds |1⟩, an eigenstate of S with phase e^{2πi·φ} (prepared for you). Use qubits 0 and 1 as a counting register (qubit 0 = least significant bit) and run phase estimation so the register reads φ as a 2-bit binary fraction. Qubit 2 may only be used as the target of controlled-phase gates.",
        "check": "state",
        "setup": [("x", (2,), ())],
        "reference": [
            ("h", (0,), ()), ("h", (1,), ()),
            ("cp", (0, 2), (PI / 2,)), ("cp", (1, 2), (PI,)),
            ("swap", (0, 1), ()), ("h", (0,), ()), ("cp", (0, 1), (-PI / 2,)), ("h", (1,), ()),
        ],
        "allowed_gates": ["h", "cp", "swap"],
        "qubit_gate_rules": {2: ["cp"]},
        "hints": [
            "S = diag(1, i), so φ = 1/4 = 0.01 in binary. The register should end up reading 01.",
            "Controlled-S from qubit 0 and controlled-S² (a CP of π) from qubit 1, then the inverse 2-qubit QFT on qubits 0 and 1.",
        ],
        "explanation": "H on both counting qubits, CP(π/2) from q0 and CP(π) from q1 onto q2 (phase kickback), then the inverse QFT: SWAP, H(0), CP(−π/2), H(1). The register reads q1q0 = 01, i.e. φ = 1/4.",
    },
]

CHALLENGES.extend(ADVANCED_CHALLENGES)

CHALLENGES_BY_ID = {c["id"]: c for c in CHALLENGES}

# Fields that would give the answer away; never sent to the client.
_PRIVATE_FIELDS = {"reference", "solution", "setup", "teardown", "target_override", "explanation", "numeric", "tolerance"}


def public_challenge(challenge):
    """Challenge data safe to send before the user has solved it."""
    data = {k: v for k, v in challenge.items() if k not in _PRIVATE_FIELDS}
    data["skill_label"] = SKILLS[challenge["skill"]]
    data["has_setup"] = bool(challenge.get("setup"))
    data["has_teardown"] = bool(challenge.get("teardown"))
    data["track"] = challenge.get("track", "foundations")
    data["kind"] = challenge.get("kind", "circuit")
    if challenge.get("device"):
        data["device"] = public_device(challenge["device"])
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

    if "qubit_gate_rules" in challenge:
        broken = sorted({
            f"{name.upper()} on q{q}"
            for name, qubits, _ in attempt_gates
            for q in qubits
            if q in challenge["qubit_gate_rules"] and name not in challenge["qubit_gate_rules"][q]
        })
        rule_text = "; ".join(
            f"q{q} only in {', '.join(g.upper() for g in names)}" for q, names in challenge["qubit_gate_rules"].items()
        )
        checks.append({
            "label": f"Respects qubit rules ({rule_text})",
            "passed": not broken,
            "detail": f"Not allowed: {', '.join(broken)}." if broken else None,
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

    if challenge.get("device"):
        violations = coupling_violations(challenge["device"], attempt_gates)
        device_name = DEVICES[challenge["device"]]["name"]
        checks.append({
            "label": f"Two-qubit gates only on connected qubits ({device_name})",
            "passed": not violations,
            "detail": (
                "Not connected: " + ", ".join(f"{name.upper()}{tuple(q)}" for _, name, q in violations) + "."
            ) if violations else None,
        })

    if "max_two_qubit_gates" in challenge:
        count = two_qubit_gate_count(attempt_gates)
        checks.append({
            "label": f"At most {challenge['max_two_qubit_gates']} two-qubit gates (SWAP = 3)",
            "passed": count <= challenge["max_two_qubit_gates"],
            "detail": f"Uses {count}.",
        })

    if challenge["check"] == "unitary":
        # Graded on the operator the user built, independent of any setup.
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

    fidelity = None
    if "min_fidelity" in challenge:
        # Only meaningful (and only worth the simulation) once the circuit is
        # legal and ideal-correct; otherwise report why it can't be scored.
        if all(c["passed"] for c in checks):
            fidelity, noisy_depth = noisy_state_fidelity(attempt_gates, n, challenge["reference"])
            checks.append({
                "label": f"Fidelity at least {challenge['min_fidelity']} under the chip's noise",
                "passed": fidelity >= challenge["min_fidelity"],
                "detail": f"Fidelity {fidelity:.3f} at depth {noisy_depth} (SWAPs expanded to CNOTs).",
            })
        else:
            checks.append({
                "label": f"Fidelity at least {challenge['min_fidelity']} under the chip's noise",
                "passed": False,
                "detail": "Not simulated until the checks above pass.",
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
        "fidelity": fidelity,
    }
    if passed:
        result["explanation"] = challenge["explanation"]
    return result


def check_numeric(challenge_id, value):
    """Grade a calculation task against the answer computed by hardware.py."""
    challenge = CHALLENGES_BY_ID.get(challenge_id)
    if challenge is None or challenge.get("kind") != "numeric":
        raise KeyError(f"Unknown calculation challenge: {challenge_id}")
    correct = solve_numeric(challenge["numeric"])
    passed = bool(abs(value - correct) <= challenge["tolerance"])
    result = {
        "passed": passed,
        "checks": [{
            "label": f"Within ±{challenge['tolerance']} of the computed answer",
            "passed": passed,
            "detail": None if passed else f"You entered {value:g}.",
        }],
        "your_state": None,
    }
    if passed:
        result["answer"] = round(correct, 4)
        result["explanation"] = challenge["explanation"]
    return result


def reveal_solution(challenge_id):
    """One known-good answer, for 'show solution'. Not the only correct answer."""
    challenge = CHALLENGES_BY_ID[challenge_id]
    if challenge.get("kind") == "numeric":
        return {"gates": [], "answer": round(solve_numeric(challenge["numeric"]), 4), "explanation": challenge["explanation"]}
    gates = challenge.get("solution", challenge["reference"])
    return {
        "gates": [{"name": g, "qubits": list(q), "params": list(p)} for g, q, p in gates],
        "explanation": challenge["explanation"],
    }
