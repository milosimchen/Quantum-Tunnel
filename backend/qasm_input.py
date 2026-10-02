"""
OpenQASM answers for practice challenges.

QASM is parsed, never executed, so accepting it from users is safe. After
parsing, the circuit is reduced to the same (name, qubits, params) gate list
the visual builder sends, then checked by the same grader and the same
allowlist (circuit_safety.py). User-defined `gate` blocks are expanded into
built-in gates; final measurements are dropped (challenges grade the state or
operator, not samples); anything else classical is rejected with a clear
message rather than silently ignored.
"""

import re

from qiskit import qasm2, qasm3

from circuit_safety import GATE_SPECS, MAX_QUBITS, CircuitInputError

MAX_SOURCE_CHARS = 20_000
_IGNORED = {"barrier"}


def _parse(source):
    version = re.search(r"OPENQASM\s+(\d+)", source)
    if version is None:
        raise CircuitInputError('Start your program with a version line, e.g. "OPENQASM 3.0;".')
    try:
        if version.group(1) == "2":
            return qasm2.loads(source)
        return qasm3.loads(source)
    except IndexError:
        raise CircuitInputError("A qubit index is out of range for its register.")
    except Exception as e:  # The importers raise several unrelated exception types.
        detail = str(e).strip().strip("'\"")
        hint = "Check for a missing semicolon, a misspelled gate or a missing include line."
        raise CircuitInputError(f"Couldn't parse the program. {detail + '. ' if detail else ''}{hint}")


def _expand_custom_gates(circuit):
    """Decompose user-defined gates until only built-in gates remain (bounded)."""
    for _ in range(5):
        names = {instr.operation.name for instr in circuit.data}
        if names <= set(GATE_SPECS) | {"measure"} | _IGNORED:
            return circuit
        circuit = circuit.decompose(gates_to_decompose=list(names - set(GATE_SPECS) - {"measure"} - _IGNORED))
    leftover = sorted({i.operation.name for i in circuit.data} - set(GATE_SPECS) - {"measure"} - _IGNORED)
    raise CircuitInputError(f"Unsupported operation(s): {', '.join(leftover)}.")


def qasm_to_gate_list(source):
    """
    Returns (gate_list, num_qubits) for an OpenQASM 2 or 3 program.
    Raises CircuitInputError with a user-facing message on any problem.
    """
    if not source or not source.strip():
        raise CircuitInputError("The program is empty.")
    if len(source) > MAX_SOURCE_CHARS:
        raise CircuitInputError(f"Programs are limited to {MAX_SOURCE_CHARS:,} characters.")

    circuit = _parse(source)
    if circuit.num_qubits > MAX_QUBITS:
        raise CircuitInputError(f"Programs are limited to {MAX_QUBITS} qubits.")
    circuit = _expand_custom_gates(circuit)

    gate_list = []
    measured = set()
    for instr in circuit.data:
        name = instr.operation.name
        qubits = tuple(circuit.find_bit(q).index for q in instr.qubits)
        if name in _IGNORED:
            continue
        if name == "measure":
            measured.update(qubits)
            continue
        if not hasattr(instr.operation, "params") or name not in GATE_SPECS:
            raise CircuitInputError(f"Unsupported operation: {name}.")
        if measured & set(qubits):
            raise CircuitInputError("Gates after a measurement aren't supported here; measure at the end (or not at all).")
        gate_list.append((name, qubits, tuple(float(p) for p in instr.operation.params)))
    return gate_list, circuit.num_qubits
