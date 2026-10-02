// Turn a builder circuit into OpenQASM 3, so switching from the visual builder
// to the code editor starts from what the user already built.

const QASM_HEADER = 'OPENQASM 3.0;\ninclude "stdgates.inc";\n'

function formatQasmAngle(value) {
  const ratio = value / Math.PI
  for (const denominator of [1, 2, 3, 4, 6, 8]) {
    const numerator = Math.round(ratio * denominator)
    if (numerator !== 0 && Math.abs(ratio * denominator - numerator) < 1e-9) {
      const sign = numerator < 0 ? '-' : ''
      const n = Math.abs(numerator)
      const top = n === 1 ? 'pi' : `${n}*pi`
      return denominator === 1 ? `${sign}${top}` : `${sign}${top}/${denominator}`
    }
  }
  return String(Number(value.toFixed(6)))
}

export function gatesToQasm(gates, numQubits) {
  const lines = gates.map(({ name, qubits, params }) => {
    const args = params?.length ? `(${params.map(formatQasmAngle).join(', ')})` : ''
    return `${name}${args} ${qubits.map((q) => `q[${q}]`).join(', ')};`
  })
  return `${QASM_HEADER}qubit[${numQubits}] q;\n\n${lines.join('\n')}${lines.length ? '\n' : ''}`
}
