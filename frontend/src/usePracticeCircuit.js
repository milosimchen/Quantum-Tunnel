import { useState } from 'react'

const TWO_QUBIT_GATES = new Set(['cx', 'cz', 'swap'])
const ROTATION_GATES = new Set(['rx', 'ry', 'rz'])

// Circuit state for Interview Prep's practice builder. Deliberately separate
// from CircuitContext so practice never touches (or is touched by) Studio's
// circuit, scan results or copilot conversation.
// angle: the current rotation angle (radians) for RZ/RX/RY placements.
export function usePracticeCircuit(numQubits, angle = Math.PI / 2) {
  const [gates, setGates] = useState([])
  const [pendingTwoQubitGate, setPendingTwoQubitGate] = useState(null)
  const [error, setError] = useState(null)

  function addGate(name, qubits, params) {
    setError(null)
    setGates((current) => [...current, params ? { name, qubits, params } : { name, qubits }])
  }

  function removeGate(indexToRemove) {
    setGates((current) => current.filter((_, index) => index !== indexToRemove))
  }

  function handleGateDrop(name, qubit) {
    if (qubit >= numQubits) return
    if (!TWO_QUBIT_GATES.has(name)) {
      if (ROTATION_GATES.has(name)) {
        if (angle === null || !Number.isFinite(angle)) {
          setError('Enter a valid angle first, e.g. pi/2 or -pi/4.')
          return
        }
        addGate(name, [qubit], [angle])
      } else {
        addGate(name, [qubit])
      }
      return
    }
    if (numQubits < 2) {
      setError(`${name.toUpperCase()} needs two qubits, and this challenge has one.`)
      return
    }
    setError(null)
    setPendingTwoQubitGate({ name, controlQubit: qubit })
  }

  function handleWireClick(qubit) {
    if (!pendingTwoQubitGate) return
    if (qubit === pendingTwoQubitGate.controlQubit) {
      setError('Control and target qubits must be different.')
      return
    }
    addGate(pendingTwoQubitGate.name, [pendingTwoQubitGate.controlQubit, qubit])
    setPendingTwoQubitGate(null)
  }

  function cancelPending() {
    setPendingTwoQubitGate(null)
    setError(null)
  }

  function clear() {
    setGates([])
    setPendingTwoQubitGate(null)
    setError(null)
  }

  return {
    gates,
    setGates,
    pendingTwoQubitGate,
    error,
    addGate,
    removeGate,
    handleGateDrop,
    handleWireClick,
    cancelPending,
    clear,
  }
}
