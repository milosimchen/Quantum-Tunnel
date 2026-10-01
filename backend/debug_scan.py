import math
from qiskit import QuantumCircuit
from simplify import simplify_fully

qc = QuantumCircuit(1)
qc.rz(math.pi, 0)
qc.rz(math.pi, 0)

print("Original:")
print(qc.draw())

final, steps = simplify_fully(qc)
print(f"\n{len(steps)} steps, final gate count: {len(final.data)}")
for s in steps:
    print(f"  {s['rule']}")
print(final.draw())