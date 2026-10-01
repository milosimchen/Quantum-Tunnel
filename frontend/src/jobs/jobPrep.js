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
    lessons: ['single-qubit-gates', 'two-qubit-gates', 'unitaries', 'universality'],
    challenges: ['cz_from_cx', 'swap_from_cx', 'ghz4_shallow'],
    quizTopics: ['Gates'],
  },
  {
    id: 'algorithms',
    label: 'Quantum algorithms',
    keywords: ['algorithm', 'grover', 'shor', 'vqe', 'qaoa', 'variational', 'optimization', 'machine learning', 'qml', 'simulation', 'chemistry', 'applications'],
    lessons: ['deutsch-jozsa', 'grover-and-shor', 'teleportation'],
    challenges: ['bell_phi_plus', 'superdense_11'],
    quizTopics: ['Algorithms'],
  },
  {
    id: 'qec',
    label: 'Error correction & fault tolerance',
    keywords: ['error correction', 'qec', 'fault-tolerant', 'fault tolerant', 'fault tolerance', 'surface code', 'decoder', 'decoding', 'logical qubit'],
    lessons: ['error-correction', 'noise-and-decoherence', 'density-matrices'],
    challenges: ['ghz3', 'ghz4_shallow'],
    quizTopics: ['Hardware'],
  },
  {
    id: 'hardware',
    label: 'Hardware & experimental physics',
    keywords: ['superconducting', 'transmon', 'trapped ion', 'ion trap', 'neutral atom', 'photonic', 'cryogenic', 'dilution', 'microwave', ' rf', 'fpga', 'laser', 'optics', 'calibration', 'fabrication', 'sensor', 'hardware', 'experimental', 'control system'],
    lessons: ['physical-qubits', 'noise-and-decoherence', 'bloch-sphere'],
    challenges: ['plus_i', 'minus'],
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
    lessons: ['vectors-and-tensors', 'unitaries'],
    challenges: ['x_from_hz', 'z_from_s'],
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
