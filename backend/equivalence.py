import numpy as np
from qiskit.quantum_info import Operator
from qiskit.quantum_info import Statevector, partial_trace

def is_fully_entangled(qc, tolerance=1e-6):
    """
    Check whether every qubit in qc is entangled with the rest of the
    system -- i.e., no single qubit's reduced state is pure on its own.

    Honest scope: this confirms bipartite entanglement across every
    qubit/rest-of-system cut. It does NOT classify the full multipartite
    entanglement structure (e.g. distinguishing GHZ-type from W-type
    entanglement) -- that's a substantially deeper question this function
    does not attempt to answer.
    """
    num_qubits = qc.num_qubits
    if num_qubits < 2:
        return False

    statevector = Statevector(qc)

    for qubit in range(num_qubits):
        other_qubits = [q for q in range(num_qubits) if q != qubit]
        reduced_state = partial_trace(statevector, other_qubits)
        purity_value = reduced_state.purity()

        if abs(purity_value.real - 1) < tolerance:
            return False  # this qubit's state is pure -- not entangled

    return True

def circuits_equivalent(qc1, qc2, tolerance=1e-8):
    """
    Check whether two quantum circuits are equivalent, up to global phase.
    Returns True/False.
    """
    if qc1.num_qubits != qc2.num_qubits:
        return False

    u1 = Operator(qc1).data
    u2 = Operator(qc2).data

    # Find the largest-magnitude entry in u1 -- guaranteed nonzero for any
    # valid unitary matrix.
    idx = np.unravel_index(np.argmax(np.abs(u1)), u1.shape)

    # If u1 and u2 were truly the same matrix up to a global phase, a
    # nonzero entry in u1 must correspond to a nonzero entry in u2 (phase
    # multiplication never turns a nonzero number into zero). If u2 is
    # zero here, that alone proves they're NOT equivalent -- return
    # immediately, no division, no risk of divide-by-zero.
    if np.abs(u2[idx]) < tolerance:
        return False

    phase_diff = u2[idx] / u1[idx]
    u2_adjusted = u2 / phase_diff

    return np.allclose(u1, u2_adjusted, atol=tolerance)



def format_dirac_notation(qc, tolerance=1e-6):
    """
    Compute the exact Dirac/bra-ket notation for the statevector resulting
    from qc applied to a standard |00...0> input. This is a real, exact
    computation from Qiskit's Statevector -- not an LLM approximation.
    """
    statevector = Statevector(qc)
    num_qubits = qc.num_qubits
    terms = []

    for index, amplitude in enumerate(statevector.data):
        if abs(amplitude) < tolerance:
            continue
        basis_label = format(index, f'0{num_qubits}b')
        real, imag = round(amplitude.real, 4), round(amplitude.imag, 4)

        if abs(imag) < tolerance:
            coeff_str = f"{real:.4f}"
        elif abs(real) < tolerance:
            coeff_str = f"{imag:.4f}i"
        else:
            sign = '+' if imag >= 0 else '-'
            coeff_str = f"({real:.4f}{sign}{abs(imag):.4f}i)"

        terms.append(f"{coeff_str}|{basis_label}\u27e9")

    return " + ".join(terms) if terms else "0"


# --- Quick test ---
if __name__ == "__main__":
    from qiskit import QuantumCircuit

    qc_a = QuantumCircuit(2)
    qc_a.h(0)
    qc_a.cx(0, 1)

    qc_b = QuantumCircuit(2)
    qc_b.h(0)
    qc_b.cx(0, 1)

    qc_c = QuantumCircuit(2)
    qc_c.h(0)
    qc_c.h(1)

    print("A vs B (should be True):", circuits_equivalent(qc_a, qc_b))
    print("A vs C (should be False):", circuits_equivalent(qc_a, qc_c))

    from qiskit import QuantumCircuit as QC2

    bell = QC2(2)
    bell.h(0)
    bell.cx(0, 1)
    print("Bell state fully entangled (should be True):", is_fully_entangled(bell))

    ghz = QC2(3)
    ghz.h(0)
    ghz.cx(0, 1)
    ghz.cx(0, 2)
    print("GHZ state fully entangled (should be True):", is_fully_entangled(ghz))

    not_entangled = QC2(2)
    not_entangled.h(0)
    not_entangled.h(1)
    print("Two independent H's fully entangled (should be False):", is_fully_entangled(not_entangled))

    partial = QC2(3)
    partial.h(0)
    partial.cx(0, 1)
    # qubit 2 left completely alone -- should NOT count as "all entangled"
    print("Bell pair + 1 untouched qubit, fully entangled (should be False):", is_fully_entangled(partial))

    print("\n--- Testing format_dirac_notation ---")
    bell_for_dirac = QC2(2)
    bell_for_dirac.h(0)
    bell_for_dirac.cx(0, 1)
    print("Bell state:", format_dirac_notation(bell_for_dirac))