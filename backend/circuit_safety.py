"""
The one place circuits are built from untrusted input.

QuantumCircuit has hundreds of methods besides gates (draw, save_*, ...), so
looking a request's gate name up with getattr() must be limited to real gate
names. Qubit count is capped too: exact simulation and unitary checks cost
2^n (state) or 4^n (unitary) memory, and NFR-1 already scopes the app to
about 10 qubits.
"""

from qiskit import QuantumCircuit

MAX_QUBITS = 10
MAX_GATES = 200

# name -> (number of qubits, number of parameters)
GATE_SPECS = {
    "id": (1, 0), "h": (1, 0), "x": (1, 0), "y": (1, 0), "z": (1, 0),
    "s": (1, 0), "sdg": (1, 0), "t": (1, 0), "tdg": (1, 0), "sx": (1, 0),
    "rx": (1, 1), "ry": (1, 1), "rz": (1, 1), "p": (1, 1),
    "cx": (2, 0), "cy": (2, 0), "cz": (2, 0), "swap": (2, 0),
    "cp": (2, 1), "crz": (2, 1), "rzz": (2, 1),
    "ccx": (3, 0),
}


class CircuitInputError(ValueError):
    """Raised for input that must not be turned into a circuit."""


def validate_gate(name, qubits, params, num_qubits):
    spec = GATE_SPECS.get(name)
    if spec is None:
        raise CircuitInputError(f"Unsupported gate: {name!r}.")
    qubit_count, param_count = spec
    if len(qubits) != qubit_count or len(params) != param_count:
        raise CircuitInputError(f"{name.upper()} takes {qubit_count} qubit(s) and {param_count} parameter(s).")
    if len(set(qubits)) != len(qubits):
        raise CircuitInputError(f"{name.upper()} needs distinct qubits.")
    if any(q < 0 or q >= num_qubits for q in qubits):
        raise CircuitInputError(f"{name.upper()} uses a qubit outside 0–{num_qubits - 1}.")


def build_circuit(gate_list, num_qubits):
    """gate_list: iterable of (name, qubits, params). Validates everything first."""
    if not 1 <= num_qubits <= MAX_QUBITS:
        raise CircuitInputError(f"Circuits must have between 1 and {MAX_QUBITS} qubits.")
    gate_list = list(gate_list)
    if len(gate_list) > MAX_GATES:
        raise CircuitInputError(f"Circuits are limited to {MAX_GATES} gates.")
    qc = QuantumCircuit(num_qubits)
    for name, qubits, params in gate_list:
        validate_gate(name, tuple(qubits), tuple(params), num_qubits)
        getattr(qc, name)(*params, *qubits)
    return qc
