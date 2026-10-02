// Advanced Study tracks. DRAFT, written by Claude for Milo to review.
// Same block format as lessons.js, plus:
//   { type: 'code', language, code }   a code listing (every Qiskit snippet
//                                      here was run against Qiskit 2.5)
// Every circuit's caption was checked against its Qiskit-computed state.

const PI = Math.PI

export const ADVANCED_TRACKS = [
  {
    id: 'algorithms-advanced',
    title: 'Algorithms in depth',
    blurb: 'The subroutines real algorithms are built from, and the near-term variational methods.',
    lessons: [
      {
        id: 'qft',
        title: 'The quantum Fourier transform',
        minutes: 9,
        blocks: [
          { type: 'p', text: 'The **quantum Fourier transform** (QFT) is the discrete Fourier transform applied to amplitudes. On $n$ qubits ($N = 2^n$) it maps each basis state to a superposition whose phases encode it:' },
          { type: 'math', tex: '\\mathrm{QFT}\\,|x\\rangle = \\frac{1}{\\sqrt{N}} \\sum_{k=0}^{N-1} e^{2\\pi i\\, xk/N}\\, |k\\rangle' },
          { type: 'p', text: 'Every output amplitude has the same size. The information about $x$ is entirely in the **phases**, which rotate faster around the unit circle for larger $x$. That is why the QFT is good at exposing **periodicity**: a periodic input turns into sharp peaks.' },
          { type: 'p', text: 'The circuit uses only Hadamards, **controlled-phase** gates and a final reversal of qubit order: $O(n^2)$ gates, against $O(n 2^n)$ operations for the classical FFT on the full vector. The catch: you can\'t read the amplitudes out. The QFT only pays off inside a larger algorithm that measures something it makes visible.' },
          { type: 'circuit', numQubits: 2, gates: [['x', [0]], ['h', [1]], ['cp', [0, 1], [PI / 2]], ['h', [0]], ['swap', [0, 1]]], caption: '2-qubit QFT applied to |1⟩ (X prepares it). The phases step by i: 1, i, −1, −i.' },
          { type: 'note', text: 'Qiskit puts qubit 0 on the right of basis labels, so the final SWAP matters: drop it and you get the same transform with the output bits in reverse order. Getting this convention right is a classic interview stumble.' },
          {
            type: 'check',
            question: 'Why does the QFT not give an exponential speedup for computing Fourier transforms of data?',
            choices: ['It needs exponentially many gates', 'The output lives in amplitudes you can\'t read out efficiently', 'It only works on 2 qubits', 'It needs error correction'],
            answer: 1,
            explanation: 'The circuit is small, but measurement gives one sample from |amplitude|², not the vector. Loading classical data into amplitudes is also expensive. The speedup only appears when the QFT feeds an algorithm with a short, measurable answer, like phase estimation.',
          },
          { type: 'practice', challenges: ['adv_qft2'] },
        ],
      },
      {
        id: 'phase-estimation',
        title: 'Phase estimation',
        minutes: 9,
        blocks: [
          { type: 'p', text: 'Given a unitary $U$ and one of its eigenstates $|u\\rangle$, with $U|u\\rangle = e^{2\\pi i\\varphi}|u\\rangle$, **quantum phase estimation** (QPE) writes $\\varphi$ into a register of $t$ counting qubits as a binary fraction.' },
          { type: 'p', text: 'It has three steps. Put the counting qubits in uniform superposition. Apply controlled-$U^{2^j}$ from counting qubit $j$: by **phase kickback**, each counting qubit picks up phase $e^{2\\pi i \\varphi 2^j}$. Then the **inverse QFT** turns those phases into the binary digits of $\\varphi$.' },
          { type: 'math', tex: '\\frac{1}{\\sqrt{2^t}} \\sum_{k} e^{2\\pi i \\varphi k} |k\\rangle \\;\\xrightarrow{\\;\\mathrm{QFT}^\\dagger\\;}\\; |\\tilde\\varphi\\rangle' },
          { type: 'p', text: 'Example: $S = \\mathrm{diag}(1, i)$ has eigenstate $|1\\rangle$ with phase $i = e^{2\\pi i \\cdot 1/4}$, so $\\varphi = 1/4 = 0.01_2$. With two counting qubits, QPE should read exactly $01$.' },
          { type: 'circuit', numQubits: 3, gates: [['x', [2]], ['h', [0]], ['h', [1]], ['cp', [0, 2], [PI / 2]], ['cp', [1, 2], [PI]], ['swap', [0, 1]], ['h', [0]], ['cp', [0, 1], [-PI / 2]], ['h', [1]]], caption: 'QPE of S: q2 holds the eigenstate |1⟩; controlled-S and controlled-S² kick phases back; the inverse QFT leaves q1 q0 = 01, i.e. φ = 1/4.' },
          { type: 'p', text: 'When $\\varphi$ has more binary digits than you have counting qubits, the output is a distribution peaked at the nearest $t$-bit value: you get the closest estimate with probability at least $4/\\pi^2 \\approx 0.41$, and adding a few extra qubits pushes the success probability up quickly.' },
          { type: 'note', text: 'QPE is the engine of Shor\'s algorithm (the phase encodes the period) and of fault-tolerant quantum chemistry (the phase is an energy). It needs long, deep circuits, which is why it waits for error correction.' },
          { type: 'practice', challenges: ['adv_qpe_s'] },
        ],
      },
      {
        id: 'variational',
        title: 'Variational algorithms: VQE and QAOA',
        minutes: 9,
        blocks: [
          { type: 'p', text: 'Variational algorithms are built for today\'s noisy machines: a **short, parameterized circuit** runs on the quantum computer, and a **classical optimizer** tunes the parameters.' },
          { type: 'p', text: '**VQE** (variational quantum eigensolver) estimates a ground-state energy. It rests on the variational principle: no trial state can have lower energy than the true ground state, so minimizing the measured energy approaches it from above.' },
          { type: 'math', tex: 'E(\\theta) = \\langle \\psi(\\theta) | H | \\psi(\\theta) \\rangle \\;\\geq\\; E_0' },
          { type: 'p', text: '**QAOA** (quantum approximate optimization algorithm) targets combinatorial problems like MaxCut. It alternates a **cost layer** $e^{-i\\gamma C}$, which phases each bitstring by its cost, with a **mixer** $e^{-i\\beta \\sum X}$, for $p$ rounds.' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['h', [1]], ['rzz', [0, 1], [PI / 2]], ['rx', [0], [(3 * PI) / 4]], ['rx', [1], [(3 * PI) / 4]]], caption: 'QAOA, p = 1, MaxCut on a single edge, with γ = π/2 and β = 3π/8 (RX(2β) = RX(3π/4)). All the probability lands on the two cuts, |01⟩ and |10⟩.' },
          { type: 'p', text: 'That tiny case hits the optimum exactly. On real problems it is much harder: optimization landscapes can be flat (**barren plateaus**), shot noise blurs every energy estimate, and it is still an open question whether these methods beat the best classical heuristics on useful problems. Expect interviewers to probe that skepticism.' },
          {
            type: 'check',
            question: 'Why can VQE never report an energy below the true ground-state energy (ignoring noise and sampling error)?',
            choices: ['The optimizer is constrained to stop early', 'Any state\'s energy expectation is a weighted average of eigenvalues, all ≥ E₀', 'Qubits can\'t represent negative energies', 'The ansatz is always the ground state'],
            answer: 1,
            explanation: 'Expanding ψ in H\'s eigenbasis, ⟨H⟩ = Σ|cᵢ|²Eᵢ is a weighted average of eigenvalues, so it is at least the smallest one. Noise and finite shots can break this in practice, which is a useful sanity check on real data.',
          },
        ],
      },
      {
        id: 'hamiltonian-simulation',
        title: 'Hamiltonian simulation and Trotter steps',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'Simulating how a quantum system evolves is the application Feynman proposed quantum computers for. The goal is to implement $e^{-iHt}$ for a Hamiltonian written as a sum of simple terms, $H = \\sum_j H_j$, typically Pauli strings.' },
          { type: 'p', text: 'Each term is easy on its own. A $Z\\otimes Z$ interaction is just CNOT, RZ, CNOT:' },
          { type: 'math', tex: 'e^{-i\\frac{\\theta}{2} Z\\otimes Z} = \\mathrm{CX}\\,(I \\otimes R_Z(\\theta))\\,\\mathrm{CX}' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['h', [1]], ['cx', [0, 1]], ['rz', [1], [PI / 2]], ['cx', [0, 1]]], caption: 'A ZZ rotation (θ = π/2) on |++⟩. The CNOTs compute the parity onto qubit 1, RZ phases it, and the second CNOT uncomputes it.' },
          { type: 'p', text: 'The hard part is that the terms usually don\'t commute, so $e^{-i(A+B)t} \\neq e^{-iAt}e^{-iBt}$. **Trotterization** splits the time into $n$ small steps and alternates:' },
          { type: 'math', tex: 'e^{-i(A+B)t} \\approx \\left(e^{-iAt/n}\\, e^{-iBt/n}\\right)^n, \\qquad \\text{error} = O\\!\\left(\\frac{t^2\\,\\|[A,B]\\|}{n}\\right)' },
          { type: 'p', text: 'The error shrinks as you add steps, but every step costs gates and therefore noise. The symmetric (second-order) split $e^{-iA t/2n}e^{-iBt/n}e^{-iAt/2n}$ improves the error to $O(t^3/n^2)$ for little extra cost. Choosing the step count against a gate budget is a standard interview discussion.' },
          { type: 'practice', challenges: ['adv_rzz'] },
        ],
      },
    ],
  },
  {
    id: 'qec-advanced',
    title: 'Error correction in depth',
    blurb: 'Stabilizers, syndromes and why the surface code dominates.',
    lessons: [
      {
        id: 'stabilizers-syndromes',
        title: 'Stabilizers and syndromes',
        minutes: 9,
        blocks: [
          { type: 'p', text: 'Error correction has to find errors **without measuring the data**, because measuring the data would destroy the superposition it protects. The trick is to measure **parities**, which are the same for every codeword and only change when an error happens.' },
          { type: 'p', text: 'In the 3-qubit bit-flip code, the operators $Z_0Z_1$ and $Z_1Z_2$ have value $+1$ on both $|000\\rangle$ and $|111\\rangle$, and on any superposition of them. Those operators are the code\'s **stabilizers**. A bit flip anticommutes with some of them and flips their value, and the pattern of flipped values, the **syndrome**, points to the error.' },
          { type: 'math', tex: '\\begin{array}{c|cc} \\text{error} & Z_0Z_1 & Z_1Z_2 \\\\ \\hline \\text{none} & + & + \\\\ X_0 & - & + \\\\ X_1 & - & - \\\\ X_2 & + & - \\end{array}' },
          { type: 'p', text: 'To measure a parity without touching the data, use an **ancilla**: CNOT from each data qubit into a fresh qubit, which ends up holding their XOR.' },
          { type: 'circuit', numQubits: 5, gates: [['x', [0]], ['cx', [0, 1]], ['cx', [0, 2]], ['x', [1]], ['cx', [0, 3]], ['cx', [1, 3]], ['cx', [1, 4]], ['cx', [2, 4]]], caption: 'Encode |1⟩ as |111⟩ on q0–q2, flip q1 (the error), then extract both parities into ancillas q3 and q4. Both ancillas read 1: syndrome (−, −), so the error is on q1.' },
          { type: 'note', text: 'Real codes repeat syndrome extraction every cycle, because ancillas and measurements are noisy too. A decoder looks at the history of syndromes, not one snapshot.' },
          {
            type: 'check',
            question: 'The syndrome reads (−, +): Z₀Z₁ flipped, Z₁Z₂ didn\'t. Which correction should you apply?',
            choices: ['X on qubit 0', 'X on qubit 1', 'X on qubit 2', 'No correction'],
            answer: 0,
            explanation: 'Only an error on qubit 0 flips Z₀Z₁ while leaving Z₁Z₂ alone. Applying X₀ undoes it. (Two simultaneous errors would fool this code, which is why it only corrects one.)',
          },
          { type: 'practice', challenges: ['adv_bitflip_syndrome'] },
        ],
      },
      {
        id: 'phase-flips-shor-code',
        title: 'Phase flips and the Shor code',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'Qubits also suffer **phase flips** ($Z$ errors), which the bit-flip code can\'t see: $Z$ commutes with $Z_0Z_1$. But in the $X$ basis a phase flip looks like a bit flip, since $HZH = X$. So the **phase-flip code** is the bit-flip code with Hadamards added: $|0\\rangle \\to |{+}{+}{+}\\rangle$, $|1\\rangle \\to |{-}{-}{-}\\rangle$, with stabilizers $X_0X_1$ and $X_1X_2$.' },
          { type: 'circuit', numQubits: 3, gates: [['cx', [0, 1]], ['cx', [0, 2]], ['h', [0]], ['h', [1]], ['h', [2]]], caption: 'Phase-flip encoding of |0⟩: the bit-flip encoder followed by H on every qubit gives |+++⟩, an equal superposition of all 8 basis states.' },
          { type: 'p', text: '**Shor\'s 9-qubit code** nests the two: three blocks of three qubits. Inside each block a bit-flip code catches $X$ errors; across blocks a phase-flip code catches $Z$ errors. Because $Y \\propto XZ$ and any single-qubit error is a combination of $I, X, Y, Z$, correcting $X$ and $Z$ corrects **any** single-qubit error. This discretization of errors is one of the key ideas of the field.' },
          {
            type: 'check',
            question: 'Why is correcting X and Z errors enough to correct an arbitrary single-qubit error, like a small over-rotation?',
            choices: ['Small errors don\'t matter', 'Any single-qubit error is a linear combination of I, X, Y, Z, and syndrome measurement collapses it onto one of them', 'Over-rotations are always X errors', 'It isn\'t enough; you need a different code'],
            answer: 1,
            explanation: 'Measuring the syndrome projects the error onto one of the discrete Pauli possibilities, which the code then corrects. Continuous errors become discrete ones.',
          },
        ],
      },
      {
        id: 'surface-code',
        title: 'The surface code and thresholds',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'The **surface code** is the leading candidate for fault-tolerant hardware. Data qubits sit on a 2D grid, and each stabilizer checks only its four nearest neighbours, so it needs only local connections, which matches superconducting chips.' },
          { type: 'p', text: 'Its size is the **code distance** $d$: the smallest number of physical errors that can cause an undetected logical error. A distance-$d$ rotated surface code uses $d^2$ data qubits plus $d^2 - 1$ measurement qubits, and corrects up to $\\lfloor (d-1)/2 \\rfloor$ errors.' },
          { type: 'p', text: 'Below a **threshold** physical error rate $p_{\\mathrm{th}}$ (around 1% for the surface code), making the code bigger makes the logical qubit exponentially better:' },
          { type: 'math', tex: 'p_L \\approx A \\left(\\frac{p}{p_{\\mathrm{th}}}\\right)^{(d+1)/2}' },
          { type: 'p', text: 'Above threshold, adding qubits makes things **worse**, because there are more places for errors. That is why "below threshold" is the milestone everyone tracks.' },
          { type: 'note', text: 'Clifford gates are cheap in the surface code. The T gate isn\'t: it needs magic-state distillation, which can dominate the qubit and time budget of a fault-tolerant algorithm. This is why T-count is a standard cost metric.' },
          {
            type: 'check',
            question: 'Physical error rate p = 0.1% and threshold 1%. Going from distance 3 to distance 5 multiplies the logical error rate by roughly what?',
            choices: ['×10', '×0.1', '×0.01', 'No change'],
            answer: 1,
            explanation: 'p/p_th = 0.1, and the exponent (d+1)/2 goes from 2 to 3, so p_L gains one more factor of 0.1: ten times fewer logical errors.',
          },
        ],
      },
    ],
  },
  {
    id: 'noise-advanced',
    title: 'Noise and mitigation',
    blurb: 'How errors are modelled, and how near-term experiments fight them without full error correction.',
    lessons: [
      {
        id: 'noise-channels',
        title: 'Noise channels',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'Noise is described as a **quantum channel** acting on density matrices. Three channels cover most of what you will be asked about.' },
          { type: 'p', text: '**Depolarizing**: with probability $p$ the state is replaced by the maximally mixed state. It is the simplest "something went wrong" model, used for gate errors in most simulators (including this site\'s hardware track).' },
          { type: 'math', tex: '\\rho \\;\\to\\; (1-p)\\,\\rho + p\\,\\frac{I}{2}' },
          { type: 'p', text: '**Amplitude damping** models energy loss ($T_1$): $|1\\rangle$ decays to $|0\\rangle$ with probability $\\gamma = 1 - e^{-t/T_1}$. It is not symmetric, because it pushes every state towards $|0\\rangle$.' },
          { type: 'math', tex: 'K_0 = \\begin{pmatrix}1 & 0\\\\ 0 & \\sqrt{1-\\gamma}\\end{pmatrix}, \\quad K_1 = \\begin{pmatrix}0 & \\sqrt{\\gamma}\\\\ 0 & 0\\end{pmatrix}, \\quad \\rho \\to K_0\\rho K_0^\\dagger + K_1 \\rho K_1^\\dagger' },
          { type: 'p', text: '**Dephasing** ($T_2$) leaves populations alone but shrinks the off-diagonal terms, the coherences, by $e^{-t/T_2}$. Superpositions turn into classical mixtures, which is exactly what destroys interference.' },
          {
            type: 'check',
            question: 'A qubit in |+⟩ suffers pure dephasing for a long time (t ≫ T2). What state does it end up in?',
            choices: ['|0⟩', '|−⟩', 'The maximally mixed state I/2', '|+⟩, unchanged'],
            answer: 2,
            explanation: '|+⟩ has populations 1/2, 1/2 and coherence 1/2. Dephasing keeps the populations and kills the coherence, leaving diag(1/2, 1/2) = I/2.',
          },
          { type: 'practice', challenges: ['hw_t1_decay', 'hw_two_qubit_budget'] },
        ],
      },
      {
        id: 'error-mitigation',
        title: 'Error mitigation',
        minutes: 8,
        blocks: [
          { type: 'p', text: '**Error mitigation** is not error correction. It doesn\'t protect the quantum state; it post-processes many noisy runs to estimate what a noiseless run would have given. It costs extra shots instead of extra qubits, which makes it the workhorse of today\'s experiments.' },
          { type: 'p', text: '**Readout mitigation** measures a calibration (confusion) matrix $M$, with $M_{ij} = P(\\text{read } i \\mid \\text{prepared } j)$, and inverts it on the measured distribution. It is cheap and effective, but the matrix grows as $2^n \\times 2^n$, so large devices use per-qubit or tensored approximations.' },
          { type: 'p', text: '**Zero-noise extrapolation** (ZNE) runs the circuit at amplified noise levels, for example by folding $G \\to G G^\\dagger G$, and extrapolates the measured expectation value back to zero noise.' },
          { type: 'math', tex: '\\langle O \\rangle_0 \\approx \\text{extrapolate}\\big(\\langle O \\rangle_{\\lambda=1},\\ \\langle O \\rangle_{\\lambda=3},\\ \\dots\\big)' },
          { type: 'p', text: '**Probabilistic error cancellation** (PEC) goes further: it writes the ideal operation as a quasi-probability mixture of noisy ones and gives unbiased estimates, at a sampling cost that grows exponentially with circuit size. Every mitigation method trades variance (more shots) for bias.' },
          { type: 'note', text: 'Mitigation works on expectation values, not individual shots. It can\'t rescue an algorithm that needs one correct bitstring from a deep circuit, which is the case for Shor.' },
          { type: 'practice', challenges: ['hw_readout_mitigation', 'hw_zne'] },
        ],
      },
      {
        id: 'compiling-for-hardware',
        title: 'Compiling for real hardware',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'A textbook circuit can\'t run as written. The compiler (in Qiskit, the **transpiler**) has three jobs: **translate** every gate into the device\'s native set, **lay out** circuit qubits onto physical qubits, and **route** two-qubit gates between qubits that aren\'t connected by inserting SWAPs.' },
          { type: 'p', text: 'Each SWAP costs three CNOTs, so a good **layout** is worth a lot. Ask for a GHZ "star" (CNOTs from qubit 0 to 1 and to 2) on a 3-qubit line, and a good transpiler just puts the middle physical qubit in the role of qubit 0, needing no SWAPs at all.' },
          { type: 'circuit', numQubits: 3, gates: [['h', [0]], ['cx', [0, 1]], ['cx', [0, 2]]], caption: 'The logical circuit. On a line 0–1–2, CX(0,2) is impossible as written, but mapping logical q0 to physical qubit 1 makes both CNOTs nearest-neighbour.' },
          { type: 'p', text: 'Native gates also change what is "expensive": on IBM-style chips **RZ is free** (a software frame change), SX and X are cheap, and the CNOT is the costly, noisy one. Single-qubit rewrites like $H = R_Z(\\pi/2)\\,\\sqrt{X}\\,R_Z(\\pi/2)$ cost almost nothing.' },
          { type: 'practice', challenges: ['hw_native_h', 'hw_route_cx', 'hw_cx_no_swap', 'hw_ghz5_fidelity'] },
        ],
      },
    ],
  },
  {
    id: 'qiskit-practice',
    title: 'Qiskit in practice',
    blurb: 'The tools interviewers expect you to have used: primitives, the transpiler and dynamic circuits.',
    lessons: [
      {
        id: 'qiskit-primitives',
        title: 'Primitives: Sampler and Estimator',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'Modern Qiskit runs circuits through two **primitives**. The **Sampler** returns measured bitstrings (counts); use it when the answer *is* a bitstring. The **Estimator** returns expectation values of observables; use it for energies and other averages, where it can apply mitigation for you.' },
          { type: 'code', language: 'python', code: `from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorSampler, StatevectorEstimator

bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)

# Sampler: needs measurements, returns counts
measured = bell.copy()
measured.measure_all()
result = StatevectorSampler().run([measured], shots=1000).result()
print(result[0].data.meas.get_counts())   # e.g. {'00': 487, '11': 513}

# Estimator: no measurements, returns <ZZ>
value = StatevectorEstimator().run([(bell, SparsePauliOp("ZZ"))]).result()[0].data.evs
print(value)                               # 1.0` },
          { type: 'p', text: 'Each `run` takes a list of **PUBs** (primitive unified blocs): a circuit, plus observables and parameter values for the Estimator. On IBM hardware the same code uses `SamplerV2` and `EstimatorV2` from `qiskit_ibm_runtime`, in job, session or batch execution modes.' },
          {
            type: 'check',
            question: 'You need the energy ⟨H⟩ of a molecule\'s trial state for VQE. Which primitive fits?',
            choices: ['Sampler', 'Estimator', 'Either: they return the same thing', 'Neither: use the transpiler'],
            answer: 1,
            explanation: 'The Estimator computes expectation values of observables directly (here H as a sum of Pauli strings) and can apply error mitigation. With a Sampler you would have to measure each Pauli term in its own basis and average yourself.',
          },
        ],
      },
      {
        id: 'qiskit-transpiler',
        title: 'The transpiler',
        minutes: 6,
        blocks: [
          { type: 'p', text: '`transpile` turns a logical circuit into one a specific device can run. It works in stages: initialization, **layout**, **routing**, **translation** to native gates, **optimization**, and scheduling. Higher `optimization_level` values (0 to 3) spend more compile time searching for fewer gates.' },
          { type: 'code', language: 'python', code: `from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap

ghz = QuantumCircuit(3)
ghz.h(0)
ghz.cx(0, 1)
ghz.cx(0, 2)          # qubits 0 and 2 aren't neighbours on the line below

line = CouplingMap([(0, 1), (1, 0), (1, 2), (2, 1)])
compiled = transpile(ghz, basis_gates=["rz", "sx", "x", "cx"],
                     coupling_map=line, optimization_level=3, seed_transpiler=1)
print(compiled.count_ops())   # 2 CX and no SWAPs: the layout put logical q0 in the middle` },
          { type: 'p', text: 'Fix `seed_transpiler` when comparing results: layout and routing use randomized search, so two runs can return different (equally valid) circuits.' },
          { type: 'practice', challenges: ['hw_route_cx', 'hw_cx_no_swap'] },
        ],
      },
      {
        id: 'dynamic-circuits-qasm',
        title: 'Dynamic circuits and OpenQASM 3',
        minutes: 7,
        blocks: [
          { type: 'p', text: '**Dynamic circuits** measure mid-circuit and change what happens next based on the result, in real time. That is what teleportation, error-correction cycles and qubit reset actually need, instead of the "deferred measurement" trick of replacing classical control with controlled gates.' },
          { type: 'code', language: 'python', code: `from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, qasm3

q = QuantumRegister(2, "q")
c = ClassicalRegister(1, "c")
circuit = QuantumCircuit(q, c)
circuit.h(q[0])
circuit.measure(q[0], c[0])
with circuit.if_test((c, 1)):   # feed-forward: runs only if we measured 1
    circuit.x(q[1])

print(qasm3.dumps(circuit))` },
          { type: 'p', text: '**OpenQASM 3** is the text format circuits are exchanged in. Version 3 added real classical control flow, so the program above exports as:' },
          { type: 'code', language: 'qasm', code: `OPENQASM 3.0;
include "stdgates.inc";
bit[1] c;
qubit[2] q;
h q[0];
c[0] = measure q[0];
if (c == 1) {
  x q[1];
}` },
          { type: 'note', text: 'OpenQASM 3 and dynamic circuits are both on IBM\'s Qiskit developer certification exam, and reading QASM is a quick way for interviewers to check you know what a circuit really does.' },
        ],
      },
    ],
  },
]
