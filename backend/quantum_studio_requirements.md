# Quantum Studio: Requirements Document

**Author:** [Your Name]
**Date:** July 2026
**Status:** Draft v2
**Timeline:** 4–6 weeks (solo project, ~20 hrs/week)

---

## 1. Project Overview

Quantum Studio is an interactive practice tool for building quantum circuits — the quantum-computing equivalent of a coding practice platform like LeetCode, but for circuit construction rather than algorithms. A user attempts to build a canonical circuit (a Bell state, a GHZ state, a teleportation protocol) from memory, and the system gives instant, mathematically verified feedback: whether the attempt matches the target, which known patterns it already recognizes within the attempt, and — once a working version is achieved — whether it can be simplified further. Every claim the system makes — a simplification, a motif match, or a target match — is confirmed via unitary matrix equivalence before being surfaced, so nothing is suggested or claimed on faith. An LLM layer sits on top of this verified core to prioritize, explain, and summarize findings in natural language, and to answer on-request questions about the current state of the circuit.

**Positioning note:** this is explicitly a *practice and feedback* tool, not an optimization tool, and not a tutorial. Production-grade quantum circuit optimization already exists and is a solved, shipped feature — e.g., Qiskit's own transpiler performs gate cancellation, commutation-based reordering, and unitary-based resynthesis automatically at `optimization_level=3`. Static tutorial material also already exists — IBM's Qiskit Textbook and Microsoft's Quantum Katas are widely recommended for hands-on learning. Quantum Studio does not attempt to replace either. What's missing from both is a hands-on, build-it-yourself loop with instant, verified grading — the same gap that dedicated coding-practice platforms fill relative to reading a textbook or docs. See Section 3 for the evidence behind this need.

**One-line pitch:** *For students and self-learners preparing for quantum computing interviews and coursework, who currently only have static tutorials or passive mock-interview tools to prepare with, I want to build an interactive circuit-building practice tool, that grades attempts against canonical targets, recognizes known patterns within them, and suggests verified simplifications — all confirmed via unitary matrix equivalence, not asserted by the AI.*

---

## 2. Goals

- Demonstrate a working, end-to-end AI-assisted tool combining formal verification with LLM-based reasoning across three related capabilities: simplification, motif recognition, and target-matching — all grounded in the same verification engine.
- Produce a polished, demoable artifact suitable for a technical portfolio and interviews.
- Build genuine hard skills in: backend API design, quantum circuit simulation, rule-based algorithms over structured data, linear algebra verification, and LLM integration with guardrails.

### Non-goals (see also Section 7, Out of Scope)
- This is not an attempt to compete with research-scale AI circuit optimization (e.g., DeepMind/Quantinuum's T-gate reduction work) or with production compiler tooling (e.g., Qiskit's transpiler). Both already solve the raw optimization problem better than this tool ever will. Quantum Studio's value is in the hands-on practice loop, not out-performing existing optimizers or replacing existing tutorials.

---

## 3. Evidence of Need

This section documents why the underlying skill (building canonical quantum circuits correctly and efficiently) is a real, tested competency, and why a hands-on practice tool fills a genuine gap rather than solving an invented problem:

- **The skill is directly tested in industry interviews.** Quantum computing interview prep guides list constructing basic quantum circuits — creating Bell states and implementing quantum teleportation protocols — as expected candidate competencies, and one prep guide explicitly lists implementing basic quantum gates (Hadamard, CNOT, Toffoli), constructing Bell and GHZ states, and developing teleportation circuits as concrete interview-prep tasks. These are the same motifs and targets already scoped in Sections 5.4–5.5.
- **Gate count/depth awareness (the simplification engine's core metric) is itself an interview question.** One real quantum-software interview question asks candidates to write a routine estimating a circuit's total gate count and depth, including CNOT count and an approximate depth calculation — validating that this isn't an arbitrary metric invented for this project.
- **Existing resources address this need only partially.** IBM's Qiskit Textbook and Microsoft's Quantum Katas are commonly recommended for hands-on practice, and at least one commercial product offers AI-simulated mock interviews with real-time feedback on explanations. What's absent from both categories is an interactive build-it-yourself loop with instant, mathematically verified grading on the circuit itself — the gap this project targets.
- **Market context:** the quantum computing talent market is reported as significantly undersupplied relative to demand, which supports the premise that people are actively trying to break into the field and would value focused practice tools — though this project is not attempting to be a commercial response to that gap, only a portfolio piece grounded in a real one.

---

## 4. Personas

**Primary user:** A student or self-learner preparing for a quantum computing interview, course, or qualifying exam, who wants hands-on practice building canonical circuits (Bell state, GHZ state, teleportation) from memory, with instant feedback on correctness and efficiency — rather than only reading a tutorial or getting feedback after the fact from an interviewer or grader.

---

## 5. Functional Requirements

### 5.1 Circuit Construction
- FR-1: User can add a gate to the circuit by specifying gate type, target qubit(s), and position.
- FR-2: Supported gate set for v1: H, X, Y, Z, S, T, CNOT, and single-qubit rotation gates (RX, RY, RZ) — all natively supported by Qiskit, so this is a modest lift beyond a minimal H/X/Z/CNOT set.
- FR-3: User can remove or reorder gates.
- FR-4: The current circuit is rendered visually as a standard circuit diagram (read-only visualization; not drag-and-drop editable).

### 5.2 Simulation
- FR-5: User can run the current circuit and view measurement probabilities (bar chart or equivalent).
- FR-6: Simulation is powered by Qiskit's simulator backend.

### 5.3 Rule-Based Simplification Engine
- FR-7: The system maintains a library of circuit simplification rules (minimum for v1: adjacent identical self-inverse gate cancellation, e.g., H-H or X-X; commuting-gate reordering where applicable; at least one small known circuit identity).
- FR-8: Every time the circuit changes, the system automatically re-scans it against the rule library (no user action required).
- FR-9: For each candidate simplification found, the system computes the unitary matrix of the original sub-circuit and the proposed replacement, and confirms equivalence up to global phase before surfacing the suggestion.
- FR-10: Suggestions that fail verification are discarded silently (never shown to the user).
- FR-11: Verified suggestions are displayed to the user with the specific gates affected and the resulting change in gate count/depth.

### 5.4 Motif Recognition
- FR-15: The system maintains a library of known circuit motifs (minimum for v1: Bell state preparation, GHZ state preparation; add more if time allows, e.g., a QFT butterfly stage or Toffoli decomposition).
- FR-16: As the circuit changes, the system checks whether any sub-circuit matches a known motif, using the same unitary-equivalence verification approach as the simplification engine (Section 5.3) — a motif match is only reported once confirmed mathematically, not pattern-matched loosely on gate names alone.
- FR-17: Recognized motifs are surfaced to the user by name (e.g., "qubits 0-1 implement a Bell pair").

### 5.5 Target-Matching / Practice Mode
- FR-18: User can select a named target (e.g., "Bell state," "GHZ state," "teleportation circuit") or, as a stretch, supply a target unitary directly.
- FR-19: The system checks the user's current circuit against the target using the same verification engine (Sections 5.3, 5.4) — full match, or no match.
- FR-20: If no match, the AI layer (Section 5.6) describes what's different in plain language, grounded in the actual gate-level comparison (e.g., "your circuit is missing an entangling gate between qubits 1 and 2") — not a free-floating guess.

### 5.6 AI Layer
- FR-12: When multiple verified simplifications, motif matches, or target-comparison results exist, an LLM is used to prioritize and explain them in plain language (e.g., which simplification to apply first and why, or what's missing to reach a target).
- FR-13: User can, on request, ask a natural-language question (e.g., "how's this circuit looking?") and receive a summary covering current gate count/depth, any pending verified suggestions, recognized motifs, and (if in practice mode) progress toward the target.
- FR-14: The LLM never simulates or asserts equivalence itself — it only summarizes and prioritizes results that have already been verified by the rule/motif/target-matching engines. This boundary is a hard architectural rule, not a soft guideline.

### 5.7 Stretch Goals (only after 5.1–5.6 are complete and stable)
- SG-1: Natural-language circuit construction (e.g., "build a Bell state" → AI adds the correct gates via the existing add-gate interface).
- SG-2: LLM-generated (not just rule-generated) candidate simplifications, subject to the same verification step before being shown.
- SG-3: User-supplied target unitary (beyond the named target list in FR-18).
- SG-4: Additional motifs and simplification rules beyond the v1 minimums.

---

## 6. Non-Functional Requirements

- NFR-1: Target scale is small circuits — up to ~8–10 qubits. The unitary-matrix verification approach scales exponentially (2ⁿ × 2ⁿ) and is not intended to extend to hardware-compilation-scale circuits; this is an intentional scope boundary, not an oversight.
- NFR-2: Background re-scanning (FR-8) should feel responsive in the UI — target under ~1–2 seconds for circuits within the target scale.
- NFR-3: The system must never present an unverified suggestion to the user (see FR-10) — this is a correctness guarantee, not a best-effort behavior.
- NFR-4: Codebase should be structured so the rule engine and verification logic are decoupled from the LLM layer (testable independently of any AI API call).

---

## 7. Out of Scope

- Noise-aware or hardware-specific optimization (real quantum hardware topology, error rates, etc.)
- Support for circuits beyond ~10 qubits
- Drag-and-drop visual circuit editing (structured form-based input only, per architecture decision)
- T-gate-specific optimization or other research-grade optimization objectives
- User accounts, saved circuit history/persistence beyond a single session (unless time allows as a stretch item)
- Insurance-grade or production-grade reliability guarantees — this is a portfolio/demo tool

---

## 8. Architecture & Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Circuit simulation & matrix computation | Qiskit (Python) | `Operator(circuit).data` for unitary extraction |
| Backend | Python, FastAPI | Endpoints: `/simulate`, `/scan`, `/chat` |
| Rule engine | Plain Python, operates on gate-list data structure | Decoupled from API and LLM layers |
| Frontend | React | Structured circuit-builder UI (forms/dropdowns), not canvas-based |
| LLM integration | Claude or OpenAI API | Structured input (verified candidates) → natural language output only |
| Deployment | Vercel (frontend), Render/Railway (backend) | |

---

## 9. Success Criteria

A v1 is considered complete when:
1. A user can build a circuit via the UI and run it to see real Qiskit simulation results.
2. The system automatically detects and verifies at least the 3 rule types listed in FR-7 on a test set of ~10 circuits.
3. The system correctly recognizes at least the 2 motifs listed in FR-15 on a test set of circuits containing them.
4. Practice mode correctly confirms a match (or accurately identifies the gap) for at least the 3 named targets in FR-18, tested on a mix of correct and incorrect attempts.
5. No unverified suggestion, motif match, or target match is ever shown (spot-checked against manual calculation on at least 5 circuits per feature).
6. The on-request "how's it looking?" query returns an accurate, LLM-generated summary matching the actual verified state across all three capabilities.
7. The full flow is deployed and demoable via a recorded 3–5 minute walkthrough.

---

## 10. Milestones (6-week plan)

| Week | Deliverable |
|---|---|
| 1 | Python + Qiskit fundamentals; hardcoded circuit + unitary extraction; first 2–3 simplification rules as functions |
| 2 | Rule library expanded (5–8 patterns) + verification step (equivalence up to global phase); first 2 motif definitions (Bell, GHZ) using the same verification approach — all working end-to-end in a script |
| 3 | FastAPI backend wrapping simulation + rule engine + motif recognition + verification; target-matching endpoint added (checks current circuit against a named target's unitary) |
| 4 | React frontend: circuit builder (expanded gate set) + live scan results panel + motif/target-match display |
| 5 | LLM layer: prioritization/explanation across simplifications, motifs, and target progress + on-request chat endpoint |
| 6 | Polish, deployment, demo video, README documenting design decisions (esp. the verify-before-suggest architecture and why target-matching/motif recognition reuse the same engine) |

**Note on sequencing:** if week 5-6 time gets tight, cut in this order: additional motifs beyond the v1 minimum first, then target-matching down to a single hardcoded target (Bell state only), then simplification rules down to the 3 required minimum. The core simplification engine (Section 5.3, week 1-2) should never be cut — it's the foundation everything else reuses.

---

## 11. Open Questions (for technical mentor)

- Which additional simplification rules are most valuable to include beyond the minimal set in FR-7, given real circuits students are likely to build?
- Is there a more efficient equivalence-check strategy for slightly larger circuits within the target scale (e.g., checking sub-circuits rather than the full circuit unitary each time) worth adopting even at v1?
- Any known pitfalls in handling global phase in practice that are worth guarding against beyond the standard normalization approach?
- Are there other canonical circuits (beyond Bell, GHZ, teleportation) that show up often enough in interviews/coursework to be worth adding as named targets or motifs in v1?
