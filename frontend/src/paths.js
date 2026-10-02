// Career paths. Grounded in Hughes et al., "Assessing the Needs of the Quantum
// Industry" (IEEE Trans. Education, 2022): across 57 companies, required
// skills cluster into separate software, hardware and business groups, and
// skills matter more than degrees. "Research" covers the quantum-specific
// algorithm / error-correction roles the same study found mostly need a PhD.
//
// Each path is a staged plan of steps. A step is done when the user's saved
// progress says so (lesson completed, challenge solved, quiz topic answered),
// never because the AI said so.

export const QUIZ_STEP_TARGET = 3 // correct answers in the topic

export const PATHS = [
  {
    id: 'software',
    title: 'Quantum software',
    roleExamples: 'Quantum software engineer, compiler engineer, SDK developer',
    why: 'The largest and fastest-growing group of roles. Interviews test circuits, Qiskit, compilation for real hardware and classical software engineering.',
    jobsQuery: 'software',
    stages: [
      {
        title: 'Foundations',
        steps: [
          { kind: 'lesson', id: 'what-is-a-qubit' },
          { kind: 'lesson', id: 'single-qubit-gates' },
          { kind: 'lesson', id: 'two-qubit-gates' },
          { kind: 'challenge', id: 'bell_phi_plus' },
          { kind: 'challenge', id: 'cz_from_cx' },
          { kind: 'quiz', id: 'Gates' },
        ],
      },
      {
        title: 'Working with real hardware',
        steps: [
          { kind: 'lesson', id: 'unitaries' },
          { kind: 'lesson', id: 'compiling-for-hardware' },
          { kind: 'challenge', id: 'hw_native_h' },
          { kind: 'challenge', id: 'hw_route_cx' },
          { kind: 'challenge', id: 'swap_from_cx' },
          { kind: 'lesson', id: 'qiskit-transpiler' },
        ],
      },
      {
        title: 'Interview-ready',
        steps: [
          { kind: 'lesson', id: 'qiskit-primitives' },
          { kind: 'lesson', id: 'dynamic-circuits-qasm' },
          { kind: 'challenge', id: 'hw_cx_no_swap' },
          { kind: 'challenge', id: 'ghz4_shallow' },
          { kind: 'challenge', id: 'adv_rzz' },
          { kind: 'quiz', id: 'Advanced' },
        ],
      },
    ],
  },
  {
    id: 'hardware',
    title: 'Hardware & experimental',
    roleExamples: 'Experimental physicist, quantum hardware / control engineer, test & measurement engineer',
    why: 'Engineering and experimental roles are what most quantum companies hire for. Interviews focus on noise, coherence, calibration and how errors are fought.',
    jobsQuery: 'hardware engineer',
    stages: [
      {
        title: 'Foundations',
        steps: [
          { kind: 'lesson', id: 'what-is-a-qubit' },
          { kind: 'lesson', id: 'bloch-sphere' },
          { kind: 'lesson', id: 'physical-qubits' },
          { kind: 'challenge', id: 'plus_i' },
          { kind: 'quiz', id: 'Fundamentals' },
        ],
      },
      {
        title: 'Noise and coherence',
        steps: [
          { kind: 'lesson', id: 'noise-and-decoherence' },
          { kind: 'lesson', id: 'noise-channels' },
          { kind: 'challenge', id: 'hw_t1_decay' },
          { kind: 'challenge', id: 'hw_two_qubit_budget' },
          { kind: 'challenge', id: 'hw_ghz3_line' },
          { kind: 'quiz', id: 'Hardware' },
        ],
      },
      {
        title: 'Interview-ready',
        steps: [
          { kind: 'lesson', id: 'error-mitigation' },
          { kind: 'challenge', id: 'hw_readout_mitigation' },
          { kind: 'challenge', id: 'hw_zne' },
          { kind: 'lesson', id: 'error-correction' },
          { kind: 'lesson', id: 'surface-code' },
          { kind: 'challenge', id: 'hw_ghz5_fidelity' },
        ],
      },
    ],
  },
  {
    id: 'research',
    title: 'Algorithms & research',
    roleExamples: 'Quantum algorithm researcher, error-correction scientist, theorist',
    why: 'The most quantum-specific roles, often PhD-level. Interviews go deep on the math, algorithms and fault tolerance.',
    jobsQuery: 'research',
    stages: [
      {
        title: 'Mathematical foundations',
        steps: [
          { kind: 'lesson', id: 'vectors-and-tensors' },
          { kind: 'lesson', id: 'unitaries' },
          { kind: 'lesson', id: 'density-matrices' },
          { kind: 'challenge', id: 'bell_psi_minus' },
          { kind: 'quiz', id: 'Entanglement' },
        ],
      },
      {
        title: 'Algorithms',
        steps: [
          { kind: 'lesson', id: 'grover-and-shor' },
          { kind: 'lesson', id: 'qft' },
          { kind: 'lesson', id: 'phase-estimation' },
          { kind: 'challenge', id: 'adv_grover2' },
          { kind: 'challenge', id: 'adv_qft2' },
          { kind: 'challenge', id: 'adv_qpe_s' },
          { kind: 'quiz', id: 'Algorithms' },
        ],
      },
      {
        title: 'Interview-ready',
        steps: [
          { kind: 'lesson', id: 'variational' },
          { kind: 'lesson', id: 'hamiltonian-simulation' },
          { kind: 'challenge', id: 'adv_rzz' },
          { kind: 'lesson', id: 'stabilizers-syndromes' },
          { kind: 'challenge', id: 'adv_bitflip_syndrome' },
          { kind: 'quiz', id: 'Advanced' },
        ],
      },
    ],
  },
  {
    id: 'business',
    title: 'Applications & business',
    roleExamples: 'Applications scientist, solutions engineer, product manager, business development',
    why: 'An often-overlooked share of quantum jobs. You need to explain what quantum computers can and can\'t do today, credibly and without hype.',
    jobsQuery: '',
    stages: [
      {
        title: 'Foundations',
        steps: [
          { kind: 'lesson', id: 'what-is-a-qubit' },
          { kind: 'lesson', id: 'measurement-and-phase' },
          { kind: 'lesson', id: 'bell-states' },
          { kind: 'challenge', id: 'plus' },
          { kind: 'quiz', id: 'Fundamentals' },
        ],
      },
      {
        title: 'What quantum is good for',
        steps: [
          { kind: 'lesson', id: 'universality' },
          { kind: 'lesson', id: 'grover-and-shor' },
          { kind: 'lesson', id: 'variational' },
          { kind: 'challenge', id: 'bell_phi_plus' },
          { kind: 'quiz', id: 'Algorithms' },
        ],
      },
      {
        title: 'Interview-ready',
        steps: [
          { kind: 'lesson', id: 'physical-qubits' },
          { kind: 'lesson', id: 'noise-and-decoherence' },
          { kind: 'lesson', id: 'error-correction' },
          { kind: 'challenge', id: 'hw_two_qubit_budget' },
          { kind: 'quiz', id: 'Hardware' },
        ],
      },
    ],
  },
]

export const PATHS_BY_ID = Object.fromEntries(PATHS.map((p) => [p.id, p]))

// progress: { lessons: Set, solved: Set, quizCorrectByTopic: { [topic]: n } }
export function isStepDone(step, progress) {
  if (step.kind === 'lesson') return progress.lessons.has(step.id)
  if (step.kind === 'challenge') return progress.solved.has(step.id)
  return (progress.quizCorrectByTopic[step.id] || 0) >= QUIZ_STEP_TARGET
}

export function pathProgress(path, progress) {
  const steps = path.stages.flatMap((s) => s.steps)
  const done = steps.filter((s) => isStepDone(s, progress)).length
  const next = steps.find((s) => !isStepDone(s, progress)) || null
  return { done, total: steps.length, next }
}

// Correct answers per quiz topic, counting each question's latest answer once.
export function quizCorrectByTopic(attempts) {
  const latest = new Map()
  for (const a of attempts) {
    if (a.challenge_id.startsWith('quiz:') && !latest.has(a.challenge_id)) latest.set(a.challenge_id, a)
  }
  const counts = {}
  for (const a of latest.values()) if (a.passed) counts[a.skill] = (counts[a.skill] || 0) + 1
  return counts
}
