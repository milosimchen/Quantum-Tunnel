import { createContext, useContext, useState } from 'react'
import { apiUrl } from './api'

const CircuitContext = createContext(null)

export function useCircuit() {
  const context = useContext(CircuitContext)
  if (!context) {
    throw new Error('useCircuit must be used within a CircuitProvider')
  }
  return context
}

const GATE_QUBIT_COUNTS = {
  h: 1, x: 1, y: 1, z: 1, s: 1, t: 1,
  cx: 2, cz: 2,
}

const DISPLAY_NAMES = {
  bell_state: 'Bell state',
  ghz_state: 'GHZ state',
  ghz_state_3: 'GHZ state',
  teleportation: 'Quantum teleportation',
  bell_pair: 'Bell pair',
  swap_gate: 'SWAP gate',
  cz_via_hadamard: 'CZ (via Hadamard identity)',
  repetition_code: 'Repetition code',
  teleportation_prep: 'Teleportation prep',
}

export function displayName(internalName) {
  return DISPLAY_NAMES[internalName] || internalName
}

export function CircuitProvider({ children }) {
  const [gates, setGates] = useState([])
  const [gateName, setGateName] = useState('h')
  const [qubitInput, setQubitInput] = useState('0')
  const [scanResult, setScanResult] = useState(null)
  const [isScanning, setIsScanning] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)
  const [showLimitations, setShowLimitations] = useState(false)

  const [chatQuestion, setChatQuestion] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [isAsking, setIsAsking] = useState(false)

  const [isCopilotOpen, setIsCopilotOpen] = useState(false)

  const [pendingTwoQubitGate, setPendingTwoQubitGate] = useState(null)

  const [minQubits, setMinQubits] = useState(1)

  // Natural-language circuit generation state
  const [nlRequest, setNlRequest] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationMessage, setGenerationMessage] = useState(null)

  function addQubit() {
    setMinQubits((current) => current + 1)
  }

  function removeQubit() {
    setMinQubits((current) => Math.max(1, current - 1))
  }

  function addGateDirect(name, qubits) {
    setErrorMessage(null)
    setScanResult(null)
    setGates((currentGates) => [...currentGates, { name, qubits }])
  }

  function handleAddGate() {
    const qubits = qubitInput
      .split(',')
      .map((q) => parseInt(q.trim(), 10))

    const expectedCount = GATE_QUBIT_COUNTS[gateName]

    if (qubits.length !== expectedCount) {
      setErrorMessage(
        `${gateName.toUpperCase()} requires exactly ${expectedCount} qubit(s), but ${qubits.length} were entered.`
      )
      return
    }

    if (qubits.some((q) => isNaN(q))) {
      setErrorMessage('Qubit input must be numbers only, e.g. "0" or "0,1".')
      return
    }

    addGateDirect(gateName, qubits)
  }

  function handleDeleteGate(indexToRemove) {
    setGates(gates.filter((_, index) => index !== indexToRemove))
    setScanResult(null)
  }

  function handleGateDrop(gateNameDropped, targetQubit) {
    const expectedCount = GATE_QUBIT_COUNTS[gateNameDropped]

    if (expectedCount === 1) {
      addGateDirect(gateNameDropped, [targetQubit])
      return
    }

    setPendingTwoQubitGate({ name: gateNameDropped, controlQubit: targetQubit })
    setErrorMessage(null)
  }

  function completeTwoQubitGate(targetQubit) {
    if (!pendingTwoQubitGate) return

    if (targetQubit === pendingTwoQubitGate.controlQubit) {
      setErrorMessage('Control and target qubits must be different.')
      return
    }

    addGateDirect(pendingTwoQubitGate.name, [pendingTwoQubitGate.controlQubit, targetQubit])
    setPendingTwoQubitGate(null)
  }

  function cancelPendingGate() {
    setPendingTwoQubitGate(null)
  }

  function clearCircuit() {
    setGates([])
    setScanResult(null)
    setErrorMessage(null)
    setPendingTwoQubitGate(null)
    setChatHistory([])
    setChatQuestion('')
    setShowLimitations(false)
    setGenerationMessage(null)
  }

  async function handleScan() {
    setIsScanning(true)
    setErrorMessage(null)

    const numQubits = Math.max(
      ...gates.flatMap((g) => g.qubits),
      0
    ) + 1
    const finalNumQubits = Math.max(numQubits, minQubits)

    try {
      const response = await fetch(apiUrl('/explain'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_qubits: finalNumQubits,
          gates: gates,
        }),
      })

      if (!response.ok) {
        throw new Error(`Backend returned an error (status ${response.status})`)
      }

      const data = await response.json()
      setScanResult(data)
      setShowLimitations(false)
    } catch (error) {
      setErrorMessage(`Scan failed: ${error.message}`)
      setScanResult(null)
    } finally {
      setIsScanning(false)
    }
  }

  async function handleAskQuestion() {
    if (!chatQuestion.trim() || gates.length === 0) return

    setIsAsking(true)

    const numQubits = Math.max(
      ...gates.flatMap((g) => g.qubits),
      0
    ) + 1
    const finalNumQubits = Math.max(numQubits, minQubits)

    const questionAsked = chatQuestion

    try {
      const response = await fetch(apiUrl('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_qubits: finalNumQubits,
          gates: gates,
          question: questionAsked,
        }),
      })

      if (!response.ok) {
        throw new Error(`Backend returned an error (status ${response.status})`)
      }

      const data = await response.json()

      setChatHistory([
        ...chatHistory,
        {
          question: questionAsked,
          answer: data.answer,
          canAnswer: data.can_answer,
          verified: data.verification?.consistent ?? null,
        },
      ])
      setChatQuestion('')
    } catch (error) {
      setChatHistory([
        ...chatHistory,
        {
          question: questionAsked,
          answer: `Error: ${error.message}`,
          canAnswer: false,
          verified: null,
        },
      ])
    } finally {
      setIsAsking(false)
    }
  }

  async function handleGenerateCircuit() {
    if (!nlRequest.trim()) return

    setIsGenerating(true)
    setGenerationMessage(null)

    try {
      const response = await fetch(apiUrl('/generate_circuit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        request: nlRequest,
        current_gates: gates.map((g) => ({
          name: g.name,
          qubits: g.qubits,
          params: g.params || [],
        })),
      }),
      })

      if (!response.ok) {
        throw new Error(`Backend returned an error (status ${response.status})`)
      }

      const data = await response.json()

      if (data.success) {
        setGates(data.gates)
        setScanResult(null)
        setErrorMessage(null)
        setPendingTwoQubitGate(null)
        setGenerationMessage({ type: 'success', text: data.message })
      } else {
        setGenerationMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setGenerationMessage({ type: 'error', text: `Generation failed: ${error.message}` })
    } finally {
      setIsGenerating(false)
    }
  }

  const [mathDeepDive, setMathDeepDive] = useState(null)
  const [isMathDeepDiveOpen, setIsMathDeepDiveOpen] = useState(false)
  const [isLoadingMathDeepDive, setIsLoadingMathDeepDive] = useState(false)
  const [mathDeepDiveView, setMathDeepDiveView] = useState('original')

  async function fetchMathDeepDive(view) {
  const sourceGates = view === 'simplified' && scanResult
    ? scanResult.final_circuit_gates
    : gates

  if (sourceGates.length === 0) return

  setIsLoadingMathDeepDive(true)
  setMathDeepDiveView(view)

  const numQubits = Math.max(
    ...sourceGates.flatMap((g) => g.qubits),
    0
  ) + 1

  try {
    const response = await fetch(apiUrl('/math_deep_dive'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        circuit_request: {
          num_qubits: Math.max(numQubits, minQubits),
          gates: sourceGates.map((g) => ({
            name: g.name,
            qubits: g.qubits,
            params: g.params || [],
          })),
        },
      }),
    })

    if (!response.ok) {
      throw new Error(`Backend returned an error (status ${response.status})`)
    }

    const data = await response.json()
    setMathDeepDive(data)
  } catch (error) {
    setMathDeepDive({ error: error.message })
  } finally {
    setIsLoadingMathDeepDive(false)
  }
  }
  
  const currentNumQubits = Math.max(
    ...gates.flatMap((g) => g.qubits),
    0
  ) + 1

  const value = {
    gates, setGates,
    gateName, setGateName,
    qubitInput, setQubitInput,
    scanResult, setScanResult,
    isScanning,
    errorMessage,
    showLimitations, setShowLimitations,
    chatQuestion, setChatQuestion,
    chatHistory,
    isAsking,
    isCopilotOpen, setIsCopilotOpen,
    currentNumQubits,
    pendingTwoQubitGate,
    minQubits,
    addQubit,
    removeQubit,
    nlRequest, setNlRequest,
    isGenerating,
    generationMessage,
    handleAddGate,
    addGateDirect,
    handleDeleteGate,
    handleScan,
    handleAskQuestion,
    handleGateDrop,
    completeTwoQubitGate,
    cancelPendingGate,
    clearCircuit,
    handleGenerateCircuit,
    mathDeepDive,
    isMathDeepDiveOpen, setIsMathDeepDiveOpen,
    isLoadingMathDeepDive,
    mathDeepDiveView,
    fetchMathDeepDive,
  }

  return (
    <CircuitContext.Provider value={value}>
      {children}
    </CircuitContext.Provider>
  )
}

