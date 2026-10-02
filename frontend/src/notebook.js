// Jupyter notebook export of verified solutions (no network code, so it can be tested in Node).

function pyAngle(value) {
  const ratio = value / Math.PI
  for (const d of [1, 2, 3, 4, 6, 8]) {
    const n = Math.round(ratio * d)
    if (n !== 0 && Math.abs(ratio * d - n) < 1e-9) {
      const top = Math.abs(n) === 1 ? 'math.pi' : `${Math.abs(n)} * math.pi`
      return `${n < 0 ? '-' : ''}${top}${d === 1 ? '' : ` / ${d}`}`
    }
  }
  return String(Number(value.toFixed(6)))
}

const lines = (text) => text.split('\n').map((line, i, all) => (i < all.length - 1 ? `${line}\n` : line))

// A Jupyter notebook (nbformat 4) with one section per verified solution.
export function buildNotebook({ name, entries, challenges }) {
  const date = new Date().toISOString().slice(0, 10)
  const cells = [
    {
      cell_type: 'markdown',
      metadata: {},
      source: lines(`# Quantum circuit solutions${name ? `: ${name}` : ''}\n\nExported from Quantum Tunnel on ${date}. Each circuit below was verified by the site's grader (exact unitary or state comparison in Qiskit) at export time. Run the cells to rebuild and inspect them.`),
    },
    {
      cell_type: 'code',
      metadata: {},
      execution_count: null,
      outputs: [],
      source: lines('import math\nfrom qiskit import QuantumCircuit\nfrom qiskit.quantum_info import Statevector'),
    },
  ]
  for (const entry of entries) {
    const challenge = challenges[entry.challenge_id]
    if (!challenge) continue
    const body = entry.gates.map(({ name: gate, qubits, params }) => {
      const args = [...(params || []).map(pyAngle), ...qubits].join(', ')
      return `qc.${gate}(${args})`
    })
    cells.push({
      cell_type: 'markdown',
      metadata: {},
      source: lines(`## ${challenge.title}\n\n${challenge.prompt}`),
    })
    cells.push({
      cell_type: 'code',
      metadata: {},
      execution_count: null,
      outputs: [],
      source: lines([
        ...(challenge.has_setup ? ['# Note: the challenge applied starting gates before this circuit (see the prompt above).'] : []),
        ...(challenge.has_teardown ? ['# Note: the challenge applied decoding gates after this circuit (see the prompt above).'] : []),
        `qc = QuantumCircuit(${challenge.num_qubits})`,
        ...body,
        'print(qc.draw())',
        'Statevector(qc).draw("latex")',
      ].join('\n')),
    })
  }
  return {
    nbformat: 4,
    nbformat_minor: 5,
    metadata: { kernelspec: { name: 'python3', display_name: 'Python 3', language: 'python' }, language_info: { name: 'python' } },
    cells,
  }
}

export function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 1)], { type: 'application/x-ipynb+json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
