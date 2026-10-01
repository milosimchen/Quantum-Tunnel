"""
Simulated hardware for the Interview Prep "Real hardware" track.

Two small devices modelled on today's superconducting chips: a native gate
set (RZ, SX, X, CX), limited connectivity, gate errors, readout errors and
errors on idle qubits. Idle noise is what makes circuit DEPTH cost fidelity,
as it does on real machines, not just gate count.

Everything here is computed (Qiskit Aer density-matrix simulation); nothing
is estimated by an LLM. The numbers are illustrative of current hardware,
not a model of any specific vendor's device.
"""

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error, ReadoutError

# Error rates in the range of current superconducting devices.
ONE_QUBIT_ERROR = 0.002
TWO_QUBIT_ERROR = 0.02
READOUT_ERROR = (0.02, 0.04)  # P(read 1 | 0), P(read 0 | 1)
T1_US = 100.0
T2_US = 80.0
LAYER_TIME_US = 0.6  # roughly one two-qubit-gate duration per circuit layer

DEVICES = {
    "line5": {
        "name": "Line-5",
        "description": "5 qubits in a row. Each qubit only talks to its neighbours.",
        "num_qubits": 5,
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4)],
        # Drawing positions (x, y) in a 4x2 grid of units, for the frontend.
        "layout": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
    },
    "line3": {
        "name": "Line-3",
        "description": "3 qubits in a row: 0 and 2 are not connected.",
        "num_qubits": 3,
        "edges": [(0, 1), (1, 2)],
        "layout": [(0, 0), (1, 0), (2, 0)],
    },
    "tee5": {
        "name": "Tee-5",
        "description": "5 qubits in a T, like a fragment of IBM's heavy-hex lattice.",
        "num_qubits": 5,
        "edges": [(0, 1), (1, 2), (1, 3), (3, 4)],
        "layout": [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2)],
    },
}

NATIVE_GATES = ["rz", "sx", "x", "cx"]
TWO_QUBIT = {"cx", "cz", "swap"}


def public_device(device_id):
    device = DEVICES[device_id]
    return {
        "id": device_id,
        "name": device["name"],
        "description": device["description"],
        "num_qubits": device["num_qubits"],
        "edges": [list(e) for e in device["edges"]],
        "layout": [list(p) for p in device["layout"]],
        "native_gates": NATIVE_GATES,
        "error_rates": {
            "one_qubit": ONE_QUBIT_ERROR,
            "two_qubit": TWO_QUBIT_ERROR,
            "readout": list(READOUT_ERROR),
            "t1_us": T1_US,
            "t2_us": T2_US,
        },
    }


def connected(device_id, a, b):
    edges = DEVICES[device_id]["edges"]
    return (a, b) in edges or (b, a) in edges


def coupling_violations(device_id, gate_list):
    """Two-qubit gates acting on qubits the chip doesn't connect."""
    return [
        (i, name, qubits)
        for i, (name, qubits, _params) in enumerate(gate_list)
        if name in TWO_QUBIT and not connected(device_id, *qubits)
    ]


def two_qubit_gate_count(gate_list):
    """SWAP counts as 3: on hardware it is compiled to three CNOTs."""
    return sum(3 if name == "swap" else 1 for name, _, _ in gate_list if name in TWO_QUBIT)


def _noise_model():
    model = NoiseModel()
    one = depolarizing_error(ONE_QUBIT_ERROR, 1)
    model.add_all_qubit_quantum_error(one, ["rz", "sx", "x", "h", "s", "t", "y", "z", "rx", "ry"])
    model.add_all_qubit_quantum_error(depolarizing_error(TWO_QUBIT_ERROR, 2), ["cx", "cz"])
    # Idle qubits relax and dephase for one layer's worth of time.
    model.add_all_qubit_quantum_error(
        thermal_relaxation_error(T1_US, T2_US, LAYER_TIME_US), ["id"]
    )
    p01, p10 = READOUT_ERROR
    model.add_all_qubit_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]))
    return model


NOISE_MODEL = _noise_model()
_SIMULATOR = AerSimulator(method="density_matrix", noise_model=NOISE_MODEL)


def _layered_with_idles(gate_list, num_qubits):
    """
    Rebuild the circuit layer by layer (as soon as each gate's qubits are
    free), inserting an identity on every qubit that sits idle in a layer so
    the idle-noise channel applies. SWAPs are expanded to 3 CNOTs first.
    """
    expanded = []
    for name, qubits, params in gate_list:
        if name == "swap":
            a, b = qubits
            expanded += [("cx", (a, b), ()), ("cx", (b, a), ()), ("cx", (a, b), ())]
        else:
            expanded.append((name, tuple(qubits), tuple(params)))

    layers = []
    free_at = [0] * num_qubits
    for gate in expanded:
        layer = max(free_at[q] for q in gate[1])
        while len(layers) <= layer:
            layers.append([])
        layers[layer].append(gate)
        for q in gate[1]:
            free_at[q] = layer + 1

    qc = QuantumCircuit(num_qubits)
    for layer in layers:
        busy = set()
        for name, qubits, params in layer:
            getattr(qc, name)(*params, *qubits)
            busy.update(qubits)
        for q in range(num_qubits):
            if q not in busy:
                qc.id(q)
    return qc, len(layers)


def noisy_state_fidelity(gate_list, num_qubits, ideal_gate_list):
    """
    Fidelity between the noisy output of `gate_list` and the ideal state
    `ideal_gate_list` prepares from |0...0>. Returns (fidelity, depth).
    """
    noisy, depth = _layered_with_idles(gate_list, num_qubits)
    noisy.save_density_matrix()
    rho = _SIMULATOR.run(noisy).result().data()["density_matrix"]

    ideal = QuantumCircuit(num_qubits)
    for name, qubits, params in ideal_gate_list:
        getattr(ideal, name)(*params, *qubits)
    return float(state_fidelity(rho, Statevector(ideal))), depth


# --- Calculation tasks -------------------------------------------------------
# Answers are computed from the parameters by these functions, never typed in.

def readout_mitigated_p1(p_read1_given0, p_read0_given1, measured_p1):
    """Invert the single-qubit confusion matrix for the true P(1)."""
    return (measured_p1 - p_read1_given0) / (1 - p_read1_given0 - p_read0_given1)


def t1_survival(t1_us, t_us):
    return math.exp(-t_us / t1_us)


def zne_linear(scale_a, value_a, scale_b, value_b):
    """Linear (Richardson, two-point) extrapolation to zero noise."""
    slope = (value_b - value_a) / (scale_b - scale_a)
    return value_a - slope * scale_a


def two_qubit_gate_success(error_per_gate, count):
    return (1 - error_per_gate) ** count


NUMERIC_SOLVERS = {
    "readout_mitigated_p1": readout_mitigated_p1,
    "t1_survival": t1_survival,
    "zne_linear": zne_linear,
    "two_qubit_gate_success": two_qubit_gate_success,
}


def solve_numeric(spec):
    return float(NUMERIC_SOLVERS[spec["solver"]](**spec["args"]))
