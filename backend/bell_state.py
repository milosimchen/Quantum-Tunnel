from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Operator

# Build a 2-qubit circuit
qc = QuantumCircuit(2)
qc.h(0)        # Hadamard on qubit 0 — puts it in superposition
qc.cx(0, 1)    # CNOT: qubit 0 is control, qubit 1 is target — creates entanglement

print("Circuit:")
print(qc.draw())

# Get the unitary matrix (this is the mechanism your whole verification engine relies on)
unitary = Operator(qc).data
print("\nUnitary matrix:")
print(unitary)

# Simulate it and measure
qc_measured = qc.copy()
qc_measured.measure_all()

simulator = AerSimulator()
result = simulator.run(qc_measured, shots=1000).result()
counts = result.get_counts()
print("\nMeasurement counts (out of 1000 shots):")
print(counts)
