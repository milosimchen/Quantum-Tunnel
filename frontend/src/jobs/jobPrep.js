// "Prep me for this job": maps a listing's text to Study lessons, Interview Prep
// challenges and concept-quiz topics with transparent keyword rules. No AI is
// involved, so every recommendation can show exactly which words triggered it.
//
// Lesson ids must exist in study/lessons.js, challenge ids in backend/practice.py
// and quiz topics in backend/interview_questions.py.

const PREP_AREAS = [
  {
    id: 'software',
    label: 'Quantum software & compilers',
    keywords: ['qiskit', 'cirq', 'pennylane', 'q#', 'quantum software', 'sdk', 'compiler', 'transpil', 'circuit', 'python', 'c++', 'software engineer', 'developer'],
    lessons: ['qiskit-primitives', 'qiskit-transpiler', 'dynamic-circuits-qasm', 'unitaries'],
    challenges: ['hw_route_cx', 'hw_cx_no_swap', 'cz_from_cx', 'ghz4_shallow'],
    quizTopics: ['Gates', 'Advanced'],
  },
  {
    id: 'algorithms',
    label: 'Quantum algorithms',
    keywords: ['algorithm', 'grover', 'shor', 'vqe', 'qaoa', 'variational', 'optimization', 'machine learning', 'qml', 'simulation', 'chemistry', 'applications'],
    lessons: ['qft', 'phase-estimation', 'variational', 'hamiltonian-simulation'],
    challenges: ['adv_grover2', 'adv_qft2', 'adv_qpe_s', 'adv_rzz'],
    quizTopics: ['Algorithms', 'Advanced'],
  },
  {
    id: 'qec',
    label: 'Error correction & fault tolerance',
    keywords: ['error correction', 'qec', 'fault-tolerant', 'fault tolerant', 'fault tolerance', 'surface code', 'decoder', 'decoding', 'logical qubit'],
    lessons: ['stabilizers-syndromes', 'phase-flips-shor-code', 'surface-code', 'noise-channels'],
    challenges: ['adv_bitflip_syndrome', 'hw_readout_mitigation', 'hw_zne'],
    quizTopics: ['Hardware', 'Advanced'],
  },
  {
    id: 'hardware',
    label: 'Hardware & experimental physics',
    keywords: ['superconducting', 'transmon', 'trapped ion', 'ion trap', 'neutral atom', 'photonic', 'cryogenic', 'dilution', 'microwave', ' rf', 'fpga', 'laser', 'optics', 'calibration', 'fabrication', 'sensor', 'hardware', 'experimental', 'control system'],
    lessons: ['physical-qubits', 'noise-channels', 'error-mitigation', 'compiling-for-hardware'],
    challenges: ['hw_t1_decay', 'hw_native_h', 'hw_ghz3_line', 'hw_ghz5_fidelity'],
    quizTopics: ['Hardware', 'Fundamentals'],
  },
  {
    id: 'theory',
    label: 'Quantum information theory',
    keywords: ['entanglement', 'quantum information', 'research scientist', 'phd', 'theor', 'physicist', 'postdoc'],
    lessons: ['bell-states', 'ghz-and-w', 'density-matrices', 'vectors-and-tensors'],
    challenges: ['bell_psi_minus', 'undo_bell'],
    quizTopics: ['Entanglement', 'Fundamentals'],
  },
  {
    id: 'crypto',
    label: 'Cryptography & networking',
    keywords: ['post-quantum', 'pqc', 'cryptograph', 'qkd', 'key distribution', 'quantum network', 'communication', 'security'],
    lessons: ['teleportation', 'grover-and-shor', 'measurement-and-phase'],
    challenges: ['superdense_11'],
    quizTopics: ['Algorithms', 'Entanglement'],
  },
  {
    id: 'math',
    label: 'Linear algebra & math',
    keywords: ['linear algebra', 'mathemat', 'statistic', 'numerical'],
    lessons: ['vectors-and-tensors', 'unitaries', 'density-matrices'],
    challenges: ['x_from_hz', 'z_from_s', 'adv_rzz'],
    quizTopics: ['Gates'],
  },
]

const FALLBACK_AREA = {
  id: 'foundations',
  label: 'Core fundamentals',
  lessons: ['what-is-a-qubit', 'measurement-and-phase', 'bell-states'],
  challenges: ['plus', 'bell_phi_plus'],
  quizTopics: ['Fundamentals'],
}

// Returns the matching prep areas, strongest first, each with the keywords that matched.
export function prepForJob(job) {
  const text = ` ${job.title || ''} ${job.description || ''} `.toLowerCase()
  const title = (job.title || '').toLowerCase()

  const matches = PREP_AREAS.map((area) => {
    const evidence = area.keywords.filter((k) => text.includes(k))
    // A keyword in the title says more about the role than one in the description.
    const score = evidence.reduce((sum, k) => sum + (title.includes(k.trim()) ? 2 : 1), 0)
    return { ...area, evidence: evidence.map((k) => k.trim()), score }
  })
    .filter((area) => area.score > 0)
    .sort((a, b) => b.score - a.score)

  return matches.length > 0 ? matches : [{ ...FALLBACK_AREA, evidence: [], score: 0 }]
}
