// Study module content. DRAFT, written by Claude for Milo to review and edit.
//
// Block types (rendered by LessonBlocks.jsx):
//   { type: 'p', text }            paragraph; supports $inline tex$ and **bold**
//   { type: 'math', tex }          display equation (KaTeX)
//   { type: 'circuit', numQubits, gates, caption }
//                                  live diagram; the output state shown under it
//                                  is computed by Qiskit (/state), never typed here
//   { type: 'note', text }         highlighted aside
//   { type: 'check', question, choices, answer, explanation }
//                                  quick self-check (answer = index into choices)
//   { type: 'practice', challenges: [ids] }
//                                  links to Interview Prep challenges
//
// Gates are [name, [qubits]] or [name, [qubits], [params]].

export const TRACKS = [
  {
    id: 'foundations',
    title: 'Foundations',
    blurb: 'What a qubit is, and why it isn\'t just a probabilistic bit.',
    lessons: [
      {
        id: 'what-is-a-qubit',
        title: 'What is a qubit?',
        minutes: 6,
        blocks: [
          { type: 'p', text: 'A classical bit is either 0 or 1. A **qubit** has two basis states too, written $|0\\rangle$ and $|1\\rangle$, but it can also be in a **superposition** of both:' },
          { type: 'math', tex: '|\\psi\\rangle = \\alpha|0\\rangle + \\beta|1\\rangle, \\qquad |\\alpha|^2 + |\\beta|^2 = 1' },
          { type: 'p', text: 'The numbers $\\alpha$ and $\\beta$ are **amplitudes**. They are complex numbers, and that is the crucial difference from a coin flip: amplitudes can be negative or imaginary, so they can cancel each other out. Probabilities can\'t.' },
          { type: 'p', text: 'When you **measure** the qubit, you get 0 with probability $|\\alpha|^2$ and 1 with probability $|\\beta|^2$, and the superposition is gone: the qubit is now whichever state you saw.' },
          { type: 'circuit', numQubits: 1, gates: [['h', [0]]], caption: 'One Hadamard gate turns |0⟩ into an equal superposition.' },
          { type: 'note', text: 'Superposition is not "secretly 0 or 1 and we don\'t know which". Interference experiments rule that out: a qubit in superposition can behave in ways no unknown-but-definite bit can.' },
          {
            type: 'check',
            question: 'A qubit is in the state $\\tfrac{1}{2}|0\\rangle + \\tfrac{\\sqrt{3}}{2}|1\\rangle$. What is the probability of measuring 1?',
            choices: ['1/2', '√3/2', '3/4', '1/4'],
            answer: 2,
            explanation: 'Square the amplitude: (√3/2)² = 3/4. The two probabilities, 1/4 and 3/4, add to 1 as they must.',
          },
        ],
      },
      {
        id: 'measurement-and-phase',
        title: 'Measurement and phase',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'Compare these two states:' },
          { type: 'math', tex: '|+\\rangle = \\tfrac{1}{\\sqrt{2}}(|0\\rangle + |1\\rangle) \\qquad |-\\rangle = \\tfrac{1}{\\sqrt{2}}(|0\\rangle - |1\\rangle)' },
          { type: 'p', text: 'Measured directly, both give 0 or 1 with probability 1/2. They look identical. But they are different states, and the difference is the **relative phase**: the minus sign between the terms.' },
          { type: 'p', text: 'Apply a Hadamard to each and the difference becomes visible: $H|+\\rangle = |0\\rangle$ and $H|-\\rangle = |1\\rangle$. The amplitudes interfere: for $|-\\rangle$ the two paths to $|0\\rangle$ cancel exactly.' },
          { type: 'circuit', numQubits: 1, gates: [['x', [0]], ['h', [0]], ['h', [0]]], caption: 'X then H makes |−⟩; a second H turns it into |1⟩ with certainty.' },
          { type: 'p', text: 'A **global phase**, multiplying the whole state by the same factor like $-1$ or $i$, is different. It cancels in every probability, so it has no physical effect. $|\\psi\\rangle$ and $-|\\psi\\rangle$ are the same physical state.' },
          { type: 'note', text: 'This is why every check in Studio and Interview Prep says "up to global phase": two circuits that differ only by a global phase are physically indistinguishable.' },
          {
            type: 'check',
            question: 'Which pair of states can be told apart by some measurement?',
            choices: ['|+⟩ and −|+⟩', '|+⟩ and |−⟩', '|0⟩ and i|0⟩', 'None of these'],
            answer: 1,
            explanation: '|+⟩ and |−⟩ differ by a relative phase, which H turns into a measurable difference. The other two pairs differ only by a global phase.',
          },
        ],
      },
      {
        id: 'bloch-sphere',
        title: 'The Bloch sphere',
        minutes: 5,
        blocks: [
          { type: 'p', text: 'Any single-qubit state can be written, up to global phase, using two angles:' },
          { type: 'math', tex: '|\\psi\\rangle = \\cos\\tfrac{\\theta}{2}|0\\rangle + e^{i\\varphi}\\sin\\tfrac{\\theta}{2}|1\\rangle' },
          { type: 'p', text: 'Read $\\theta$ and $\\varphi$ as latitude and longitude, and every qubit state is a point on a sphere: the **Bloch sphere**. $|0\\rangle$ is the north pole, $|1\\rangle$ the south pole, and the equal superpositions sit on the equator: $|+\\rangle$ at $+X$, $|-\\rangle$ at $-X$, $|{+i}\\rangle$ at $+Y$.' },
          { type: 'p', text: 'In this picture, single-qubit gates are **rotations**. X is a half-turn about the X axis, Z a half-turn about Z, and S a quarter-turn about Z. H is a half-turn about the diagonal axis between X and Z, which is why it swaps the two.' },
          { type: 'circuit', numQubits: 1, gates: [['h', [0]], ['s', [0]]], caption: 'H moves |0⟩ to +X; S rotates a quarter-turn around the equator to +Y.' },
          { type: 'note', text: 'The sphere only describes one qubit. Entangled multi-qubit states have no picture like this, which is part of what makes them powerful.' },
          { type: 'practice', challenges: ['plus', 'minus', 'plus_i'] },
        ],
      },
    ],
  },
  {
    id: 'gates',
    title: 'Gates & circuits',
    blurb: 'The building blocks, and the identities that relate them.',
    lessons: [
      {
        id: 'single-qubit-gates',
        title: 'Single-qubit gates',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'Quantum gates are **unitary** matrices: they preserve total probability, and every gate can be undone. The core single-qubit gates:' },
          { type: 'math', tex: 'X = \\begin{pmatrix}0&1\\\\1&0\\end{pmatrix} \\quad Y = \\begin{pmatrix}0&-i\\\\i&0\\end{pmatrix} \\quad Z = \\begin{pmatrix}1&0\\\\0&-1\\end{pmatrix} \\quad H = \\tfrac{1}{\\sqrt2}\\begin{pmatrix}1&1\\\\1&-1\\end{pmatrix}' },
          { type: 'p', text: '**X** is the bit flip (quantum NOT). **Z** is the phase flip: it leaves $|0\\rangle$ alone and negates $|1\\rangle$. **Y** does both, with a factor of $i$. **H** creates and undoes superpositions.' },
          { type: 'p', text: 'The phase gates add a phase to $|1\\rangle$ only:' },
          { type: 'math', tex: 'S = \\begin{pmatrix}1&0\\\\0&i\\end{pmatrix} \\qquad T = \\begin{pmatrix}1&0\\\\0&e^{i\\pi/4}\\end{pmatrix}' },
          { type: 'p', text: 'They stack up neatly: $T^2 = S$, $S^2 = Z$ and $Z^2 = I$. Studio\'s simplifier uses exactly these relations.' },
          { type: 'circuit', numQubits: 1, gates: [['h', [0]], ['z', [0]], ['h', [0]]], caption: 'H Z H acts exactly like X: try it on |0⟩ and you get |1⟩.' },
          {
            type: 'check',
            question: 'What single gate is equal to S·S·S·S?',
            choices: ['Z', 'I (nothing)', 'S†', 'T'],
            answer: 1,
            explanation: 'S² = Z and Z² = I, so S⁴ = I. Four S gates in a row cancel completely.',
          },
          { type: 'practice', challenges: ['z_from_s', 'x_from_hz', 'minus_i_clifford'] },
        ],
      },
      {
        id: 'two-qubit-gates',
        title: 'Two-qubit gates',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'With two qubits there are four basis states: $|00\\rangle, |01\\rangle, |10\\rangle, |11\\rangle$. A general state is a superposition of all four, so the state of $n$ qubits needs $2^n$ amplitudes.' },
          { type: 'note', text: 'Ordering convention: this app (like Qiskit) writes qubit 0 as the rightmost digit. In |01⟩, qubit 0 is 1 and qubit 1 is 0.' },
          { type: 'p', text: 'The **CNOT** (CX) gate flips its target qubit if and only if its control qubit is $|1\\rangle$. On basis states it is a reversible XOR: $|c, t\\rangle \\to |c, t \\oplus c\\rangle$.' },
          { type: 'circuit', numQubits: 2, gates: [['x', [0]], ['cx', [0, 1]]], caption: 'Control (qubit 0) is |1⟩, so the target flips too.' },
          { type: 'p', text: '**CZ** applies a Z to the target when the control is $|1\\rangle$, which means it negates only $|11\\rangle$. That is symmetric: in CZ there is no real difference between control and target.' },
          { type: 'p', text: 'Gates convert into each other. A CNOT sandwiched between Hadamards on its target becomes a CZ, and three alternating CNOTs make a SWAP, the quantum version of the XOR-swap trick.' },
          { type: 'circuit', numQubits: 2, gates: [['x', [0]], ['cx', [0, 1]], ['cx', [1, 0]], ['cx', [0, 1]]], caption: 'Start with qubit 0 set; three CNOTs move the 1 to qubit 1.' },
          { type: 'practice', challenges: ['cz_from_cx', 'swap_from_cx'] },
        ],
      },
      {
        id: 'universality',
        title: 'Universal gate sets',
        minutes: 6,
        blocks: [
          { type: 'p', text: 'Can a small set of gates build any quantum computation? Yes, approximately. **H, S, CNOT and T** form a universal set: any unitary can be approximated to arbitrary precision using only these.' },
          { type: 'p', text: 'Drop T, and what\'s left (H, S, CNOT) generates the **Clifford group**. Clifford circuits can create superposition and even entanglement, yet by the **Gottesman–Knill theorem** they can be simulated efficiently on an ordinary computer. They alone give no quantum speedup.' },
          { type: 'p', text: 'So T gates are the scarce resource. In fault-tolerant machines they are by far the most expensive gate to implement, which is why "T-count" is a standard measure of how costly a circuit is.' },
          { type: 'p', text: 'The **Solovay–Kitaev theorem** makes "approximately" precise: approximating a gate to accuracy $\\varepsilon$ takes only $O(\\log^c(1/\\varepsilon))$ gates, so the overhead is modest.' },
          {
            type: 'check',
            question: 'A circuit uses only H, S and CNOT gates. Which statement is true?',
            choices: ['It cannot create entanglement', 'It can be simulated efficiently on a classical computer', 'It is universal', 'It cannot create superposition'],
            answer: 1,
            explanation: 'Clifford circuits can create superposition and entanglement (a Bell pair is H plus CNOT), but Gottesman–Knill says they are classically simulable.',
          },
        ],
      },
    ],
  },
  {
    id: 'entanglement',
    title: 'Entanglement',
    blurb: 'Correlations with no classical explanation, and how to make them.',
    lessons: [
      {
        id: 'bell-states',
        title: 'Bell states',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'Two qubits are **entangled** when their joint state can\'t be written as (state of qubit A) ⊗ (state of qubit B). The simplest example is a **Bell state**:' },
          { type: 'math', tex: '|\\Phi^+\\rangle = \\tfrac{1}{\\sqrt2}(|00\\rangle + |11\\rangle)' },
          { type: 'p', text: 'Measure either qubit and you get 0 or 1 at random, but the other qubit always agrees. Try to factor it: $(a|0\\rangle + b|1\\rangle)\\otimes(c|0\\rangle + d|1\\rangle)$ would need $ad = 0$ (no $|01\\rangle$) while $ac$ and $bd$ are both nonzero. Impossible.' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['cx', [0, 1]]], caption: 'The standard recipe: superpose, then copy with a CNOT.' },
          { type: 'p', text: 'There are four Bell states, which together form a basis for two qubits:' },
          { type: 'math', tex: '|\\Phi^\\pm\\rangle = \\tfrac{1}{\\sqrt2}(|00\\rangle \\pm |11\\rangle) \\qquad |\\Psi^\\pm\\rangle = \\tfrac{1}{\\sqrt2}(|01\\rangle \\pm |10\\rangle)' },
          { type: 'note', text: 'Entanglement does not let you send signals. Each qubit on its own looks completely random no matter what is done to the other; the correlation only shows up when you compare results.' },
          { type: 'practice', challenges: ['bell_phi_plus', 'bell_psi_minus', 'undo_bell'] },
        ],
      },
      {
        id: 'ghz-and-w',
        title: 'GHZ and W states',
        minutes: 6,
        blocks: [
          { type: 'p', text: 'With three or more qubits, entanglement comes in genuinely different kinds. The two famous three-qubit examples:' },
          { type: 'math', tex: '|\\text{GHZ}\\rangle = \\tfrac{1}{\\sqrt2}(|000\\rangle + |111\\rangle) \\qquad |W\\rangle = \\tfrac{1}{\\sqrt3}(|001\\rangle + |010\\rangle + |100\\rangle)' },
          { type: 'circuit', numQubits: 3, gates: [['h', [0]], ['cx', [0, 1]], ['cx', [0, 2]]], caption: 'GHZ: one superposition, fanned out with CNOTs.' },
          { type: 'p', text: 'They behave very differently under loss. Lose one qubit of GHZ and the other two are left merely classically correlated: no entanglement survives. Lose one qubit of W and the remaining pair is **still entangled**.' },
          { type: 'p', text: 'This isn\'t a difference of degree. No local operations can turn one into the other: GHZ and W are inequivalent entanglement classes.' },
          { type: 'note', text: 'Studio can confirm a state is entangled across every single-qubit cut, but it doesn\'t classify GHZ-type versus W-type. That is a harder problem, and the app says so rather than guessing.' },
          { type: 'practice', challenges: ['ghz3', 'ghz4_shallow'] },
        ],
      },
    ],
  },
  {
    id: 'algorithms',
    title: 'Algorithms & protocols',
    blurb: 'What quantum computers are actually good at.',
    lessons: [
      {
        id: 'teleportation',
        title: 'Teleportation and superdense coding',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'Two protocols show that entanglement is a resource you can spend.' },
          { type: 'p', text: '**Superdense coding**: Alice and Bob share a Bell pair. By applying I, X, Z or XZ to her qubit alone, Alice turns it into one of the four Bell states, then sends her one qubit to Bob. Bob measures in the Bell basis and reads **two** classical bits.' },
          { type: 'p', text: '**Teleportation** runs the trade the other way: with a shared Bell pair plus **two** classical bits from Alice, Bob can reconstruct an unknown qubit state that Alice holds, without the qubit itself travelling.' },
          { type: 'math', tex: '1 \\text{ ebit} + 1 \\text{ qubit sent} \\Rightarrow 2 \\text{ bits} \\qquad 1 \\text{ ebit} + 2 \\text{ bits sent} \\Rightarrow 1 \\text{ qubit}' },
          { type: 'p', text: 'Teleportation never beats light speed: until the two classical bits arrive, Bob\'s qubit is completely random. And Alice\'s original is destroyed by her measurement, consistent with the **no-cloning theorem**.' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['cx', [0, 1]], ['x', [0]], ['z', [0]], ['cx', [0, 1]], ['h', [0]]], caption: 'Superdense coding for message 11: share Φ+, Alice applies X then Z, Bob decodes.' },
          { type: 'practice', challenges: ['superdense_11'] },
        ],
      },
      {
        id: 'deutsch-jozsa',
        title: 'Deutsch–Jozsa and phase kickback',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'You get a black-box function $f:\\{0,1\\}^n \\to \\{0,1\\}$, promised to be either **constant** (same output everywhere) or **balanced** (0 on exactly half the inputs). Classically you might need $2^{n-1}+1$ queries to be sure. Deutsch–Jozsa needs **one**.' },
          { type: 'p', text: 'The trick is **phase kickback**. Put the output qubit in $|-\\rangle$. Then the oracle, instead of flipping that qubit, multiplies the input state by $(-1)^{f(x)}$:' },
          { type: 'math', tex: '|x\\rangle|-\\rangle \\;\\to\\; (-1)^{f(x)}|x\\rangle|-\\rangle' },
          { type: 'p', text: 'Query on a uniform superposition of all inputs, apply H to every input qubit, and measure. If $f$ is constant, the phases are all equal and you get $|0\\dots0\\rangle$ with certainty. If balanced, they cancel at $|0\\dots0\\rangle$ exactly, so you never see it.' },
          { type: 'circuit', numQubits: 2, gates: [['x', [1]], ['h', [0]], ['h', [1]], ['cx', [0, 1]], ['h', [0]]], caption: 'One input qubit, balanced oracle f(x) = x (a CNOT). Qubit 0 ends in |1⟩: "balanced".' },
          { type: 'note', text: 'The speedup is real but narrow: a randomized classical algorithm is right with high probability after a handful of queries. Deutsch–Jozsa matters because it shows the mechanism (kickback plus interference) that the important algorithms build on.' },
        ],
      },
      {
        id: 'grover-and-shor',
        title: 'Grover and Shor',
        minutes: 8,
        blocks: [
          { type: 'p', text: '**Grover\'s algorithm** searches $N$ unsorted items for a marked one in about $\\tfrac{\\pi}{4}\\sqrt{N}$ queries, versus $N/2$ classically on average. Each round has two steps: the oracle flips the sign of the marked item, then the **diffusion** operator reflects every amplitude about the average. Together they rotate the state a little closer to the answer each round.' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['h', [1]], ['cz', [0, 1]], ['h', [0]], ['h', [1]], ['x', [0]], ['x', [1]], ['cz', [0, 1]], ['x', [0]], ['x', [1]], ['h', [0]], ['h', [1]]], caption: 'Grover on 2 qubits, marked item |11⟩: one round finds it with certainty.' },
          { type: 'p', text: 'The speedup is quadratic, and provably optimal for unstructured search. Useful, but not the kind of speedup that breaks cryptography.' },
          { type: 'p', text: '**Shor\'s algorithm** factors integers in polynomial time, an exponential speedup over the best known classical methods. The quantum part is only **period finding**: given $a$ and $N$, find the period $r$ of $a^x \\bmod N$. The **quantum Fourier transform** turns that periodicity into peaks you can measure. The rest (gcd, continued fractions) is classical.' },
          { type: 'note', text: 'Running Shor on keys of cryptographic size needs large numbers of error-corrected qubits, far beyond today\'s devices. The threat is real enough that post-quantum cryptography standards already exist.' },
          {
            type: 'check',
            question: 'Roughly how many oracle queries does Grover need to search a million items?',
            choices: ['About 20', 'About 800', 'About 500,000', 'About 1,000,000'],
            answer: 1,
            explanation: '(π/4)·√1,000,000 ≈ 0.785 × 1000 ≈ 785. A classical search needs about 500,000 on average.',
          },
        ],
      },
    ],
  },
  {
    id: 'math',
    title: 'The math',
    blurb: 'Tensor products, unitaries and density matrices, without hand-waving.',
    lessons: [
      {
        id: 'vectors-and-tensors',
        title: 'States as vectors, tensor products',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'A qubit state is a unit vector in $\\mathbb{C}^2$: $|0\\rangle = (1, 0)^T$ and $|1\\rangle = (0, 1)^T$. The **inner product** $\\langle\\phi|\\psi\\rangle$ measures overlap, and measurement probabilities are $|\\langle i|\\psi\\rangle|^2$.' },
          { type: 'p', text: 'Systems combine by the **tensor product**. For two qubits:' },
          { type: 'math', tex: '\\begin{pmatrix}a\\\\b\\end{pmatrix} \\otimes \\begin{pmatrix}c\\\\d\\end{pmatrix} = \\begin{pmatrix}ac\\\\ad\\\\bc\\\\bd\\end{pmatrix}' },
          { type: 'p', text: 'That gives $n$ qubits a $2^n$-dimensional state space, the source of both quantum computing\'s power and the exponential cost of simulating it. It\'s also why Studio\'s exact unitary checks are capped at around 10 qubits: a 10-qubit unitary already has about a million entries.' },
          { type: 'p', text: 'A state is a **product state** if it factors as a tensor product. Most states don\'t, and those are entangled. For two qubits with amplitudes $(\\alpha_{00}, \\alpha_{01}, \\alpha_{10}, \\alpha_{11})$, the state is a product exactly when $\\alpha_{00}\\alpha_{11} = \\alpha_{01}\\alpha_{10}$.' },
          {
            type: 'check',
            question: 'Is (|00⟩ + |01⟩ + |10⟩ + |11⟩)/2 entangled?',
            choices: ['Yes', 'No: it equals |+⟩ ⊗ |+⟩'],
            answer: 1,
            explanation: 'All amplitudes are 1/2, so α₀₀α₁₁ = α₀₁α₁₀ = 1/4. It factors as |+⟩⊗|+⟩: two H gates and no entanglement.',
          },
        ],
      },
      {
        id: 'unitaries',
        title: 'Unitaries and equivalence',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'A gate is a **unitary** matrix $U$, meaning $U^\\dagger U = I$. Unitaries preserve inner products (so probabilities still sum to 1) and are always invertible: $U^{-1} = U^\\dagger$. A circuit is the product of its gates, applied right to left.' },
          { type: 'math', tex: 'U_{\\text{circuit}} = U_k \\cdots U_2 U_1' },
          { type: 'p', text: 'Two circuits are **equivalent** if they give the same unitary up to a global phase: $U_2 = e^{i\\theta}U_1$. That is the exact check behind every verified claim in Studio. Find a nonzero entry, divide out the phase difference, and compare every entry.' },
          { type: 'p', text: 'Checking a whole unitary is stronger than checking one output state. Two circuits can both turn $|00\\rangle$ into a Bell state while acting differently on other inputs. That\'s why Interview Prep grades state-preparation tasks on states, and gate-identity tasks on full unitaries.' },
          { type: 'circuit', numQubits: 2, gates: [['h', [0]], ['h', [1]], ['h', [1]], ['cx', [0, 1]], ['h', [1]]], caption: 'Prepare |++⟩, then H·CX·H on the target: only |11⟩ picks up a minus sign, exactly what CZ does.' },
          { type: 'note', text: 'Global phase is ignored because it is unobservable. Relative phase within a state, or a phase that depends on the input (like CZ\'s sign on |11⟩), is never ignored.' },
        ],
      },
      {
        id: 'density-matrices',
        title: 'Density matrices and partial trace',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'State vectors can\'t describe part of an entangled system, or a qubit you only know statistically. **Density matrices** can. For a pure state, $\\rho = |\\psi\\rangle\\langle\\psi|$. For a mixture of states $|\\psi_i\\rangle$ with probabilities $p_i$:' },
          { type: 'math', tex: '\\rho = \\sum_i p_i |\\psi_i\\rangle\\langle\\psi_i|' },
          { type: 'p', text: 'The **partial trace** throws away one subsystem and keeps the correct description of the rest. Trace out either qubit of a Bell state and you get the maximally mixed state:' },
          { type: 'math', tex: '\\operatorname{Tr}_B\\, |\\Phi^+\\rangle\\langle\\Phi^+| = \\tfrac{1}{2}\\begin{pmatrix}1&0\\\\0&1\\end{pmatrix} = \\tfrac{I}{2}' },
          { type: 'p', text: '**Purity**, $\\operatorname{Tr}(\\rho^2)$, is 1 for a pure state and less than 1 for a mixed one. For a pure joint state, a subsystem that comes out mixed is entangled with the rest. That is exactly how Studio\'s `is_fully_entangled` check works: it computes every single-qubit reduced state and requires all of them to be mixed.' },
          {
            type: 'check',
            question: 'What is the purity Tr(ρ²) of the maximally mixed qubit I/2?',
            choices: ['0', '1/2', '1', '2'],
            answer: 1,
            explanation: '(I/2)² = I/4, and its trace is 1/2. That is the minimum possible for a single qubit.',
          },
        ],
      },
    ],
  },
  {
    id: 'hardware',
    title: 'Hardware & noise',
    blurb: 'Why real qubits are hard, and how error correction fights back.',
    lessons: [
      {
        id: 'physical-qubits',
        title: 'Physical qubits',
        minutes: 7,
        blocks: [
          { type: 'p', text: 'A qubit is any two-level quantum system you can control and measure. The leading platforms make very different trade-offs:' },
          { type: 'p', text: '**Superconducting circuits** (IBM, Google): fast gates (tens of nanoseconds), manufactured on chips, but need dilution refrigerators near absolute zero and usually connect only to nearest neighbors. **Trapped ions** (Quantinuum, IonQ): very high gate fidelity and all-to-all connectivity, but slower gates. **Neutral atoms** (QuEra, Pasqal, Atom Computing): large arrays and reconfigurable layouts. **Photonics** (PsiQuantum, Xanadu): room-temperature components and natural networking, with probabilistic gates as the main challenge.' },
          { type: 'p', text: 'Every device has a **native gate set** and a **coupling map** (which qubits can interact). A compiler, or **transpiler**, rewrites your circuit into native gates and inserts SWAPs to route interactions between qubits that aren\'t connected.' },
          { type: 'note', text: 'This is the setting for the "hardware-aware transpilation" feature on Studio\'s roadmap: rewrite a circuit for a real device, then verify the result is still equivalent to the original.' },
        ],
      },
      {
        id: 'noise-and-decoherence',
        title: 'Noise and decoherence',
        minutes: 6,
        blocks: [
          { type: 'p', text: 'Qubits leak information to their environment. Two timescales summarize how fast: **T1**, energy relaxation ($|1\\rangle$ decaying to $|0\\rangle$), and **T2**, dephasing (loss of the relative phase between $|0\\rangle$ and $|1\\rangle$). Physically $T_2 \\le 2T_1$.' },
          { type: 'p', text: 'On top of that, every gate has an error rate. Two-qubit gates are typically several times noisier than single-qubit ones, and measurement adds readout error.' },
          { type: 'p', text: 'So **depth** (roughly, how long the circuit runs) and **two-qubit gate count** are the numbers that matter on today\'s noisy (NISQ) hardware. Every CNOT the simplifier removes is a real reduction in expected error.' },
          {
            type: 'check',
            question: 'Two circuits produce the same unitary. One has 4 CNOTs and depth 6; the other has 2 CNOTs and depth 9. Which is likely better on noisy hardware?',
            choices: ['The 4-CNOT circuit', 'The 2-CNOT circuit', 'It depends on the device\'s error rates and T2', 'They are identical in practice'],
            answer: 2,
            explanation: 'There is a genuine trade-off: fewer noisy two-qubit gates versus a longer runtime during which qubits decohere. Which wins depends on the device. That is why transpilers use calibration data.',
          },
        ],
      },
      {
        id: 'error-correction',
        title: 'Error correction',
        minutes: 8,
        blocks: [
          { type: 'p', text: 'Classical error correction copies bits. Quantum states can\'t be copied, and measuring them destroys superposition, so for a while quantum error correction looked impossible. The trick is to measure **parities** of qubits, never the data itself.' },
          { type: 'p', text: 'The **bit-flip repetition code** encodes $\\alpha|0\\rangle + \\beta|1\\rangle$ as $\\alpha|000\\rangle + \\beta|111\\rangle$. Measuring "do qubits 0 and 1 agree?" and "do qubits 1 and 2 agree?" pinpoints a single bit flip without revealing $\\alpha$ or $\\beta$.' },
          { type: 'circuit', numQubits: 3, gates: [['h', [0]], ['cx', [0, 1]], ['cx', [0, 2]]], caption: 'Encoding |+⟩ into the repetition code: the same circuit as GHZ.' },
          { type: 'p', text: 'This code is blind to phase flips, so real codes protect against both. The **surface code** arranges qubits on a 2D grid with only nearest-neighbor checks and tolerates physical error rates up to about 1%. The cost is overhead: hundreds to thousands of physical qubits per logical qubit, depending on the target error rate.' },
          { type: 'p', text: 'Below the **threshold**, adding more physical qubits makes the logical qubit exponentially better. Demonstrating this below-threshold scaling has been a key recent milestone for the field.' },
        ],
      },
    ],
  },
]

export const ALL_LESSONS = TRACKS.flatMap((track) =>
  track.lessons.map((lesson) => ({ ...lesson, trackId: track.id, trackTitle: track.title }))
)

export function findLesson(lessonId) {
  const index = ALL_LESSONS.findIndex((l) => l.id === lessonId)
  if (index === -1) return null
  return { lesson: ALL_LESSONS[index], previous: ALL_LESSONS[index - 1] || null, next: ALL_LESSONS[index + 1] || null }
}
