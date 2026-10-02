"""
Open-ended mock-interview prompts: "explain" and "system design" rounds.

Unlike circuits and multiple choice, these can't be graded exactly. Each has a
fixed rubric of criteria written in advance. The LLM only judges each
criterion met / not met with a one-line reason; the score is computed here
from those judgments. The UI labels this feedback as AI-generated.

`paths` lists which career paths a prompt suits (empty = any).
"""

EXPLAIN_PROMPTS = [
    {
        "id": "explain_mitigation_vs_qec",
        "paths": ["software", "hardware", "research"],
        "prompt": "An interviewer asks: \"If error mitigation works so well on today's devices, why can't we just use it to run Shor's algorithm?\" Answer as you would out loud, in a few sentences.",
        "rubric": [
            {"id": "expectation_values", "text": "Says mitigation corrects estimates of expectation values / averages, not individual runs or bitstrings."},
            {"id": "cost_scaling", "text": "Mentions that mitigation's cost (extra shots or sampling overhead) grows quickly, often exponentially, with circuit size or noise."},
            {"id": "shor_needs", "text": "Explains Shor needs long, deep circuits whose output is a specific bitstring / exact result."},
            {"id": "qec_role", "text": "Says fault-tolerant error correction (logical qubits) is needed for that regime."},
        ],
    },
    {
        "id": "explain_entanglement_no_signal",
        "paths": ["research", "business"],
        "prompt": "Explain to an interviewer why entanglement doesn't allow faster-than-light communication.",
        "rubric": [
            {"id": "local_random", "text": "Says each party's measurement results on their own look random regardless of what the other does."},
            {"id": "reduced_state", "text": "Mentions the reduced state / local statistics don't change (no-signaling), or an equivalent precise statement."},
            {"id": "correlation_compare", "text": "Says the correlations only appear when results are compared, which needs classical communication."},
            {"id": "teleport_example", "text": "Uses teleportation or a similar protocol correctly as an example of needing classical bits."},
        ],
    },
    {
        "id": "explain_depth_vs_cnots",
        "paths": ["software", "hardware"],
        "prompt": "You're given two equivalent circuits: one has fewer CNOTs, the other has lower depth. Which would you run on today's hardware, and how would you decide?",
        "rubric": [
            {"id": "two_qubit_errors", "text": "Notes that two-qubit gates are typically the noisiest operations."},
            {"id": "decoherence_time", "text": "Notes that depth sets runtime, during which qubits decohere (T1/T2, idle errors)."},
            {"id": "depends_on_device", "text": "Says the answer depends on the specific device's error rates and coherence times."},
            {"id": "measure_it", "text": "Proposes a concrete way to decide: estimate fidelity from calibration data, simulate with a noise model, or run both."},
        ],
    },
    {
        "id": "explain_vqe",
        "paths": ["research", "software", "business"],
        "prompt": "Explain how the variational quantum eigensolver (VQE) works and one major challenge it faces.",
        "rubric": [
            {"id": "ansatz", "text": "Describes a parameterized circuit (ansatz) that prepares trial states."},
            {"id": "classical_loop", "text": "Describes the classical optimizer updating parameters based on measured energies."},
            {"id": "variational_principle", "text": "Mentions the variational principle: measured energy is an upper bound on the ground-state energy."},
            {"id": "challenge", "text": "Names a real challenge: barren plateaus, shot noise / measurement cost, hardware noise, or ansatz expressivity."},
        ],
    },
    {
        "id": "explain_surface_code",
        "paths": ["hardware", "research"],
        "prompt": "Explain what an error-correction threshold is and why the surface code is popular.",
        "rubric": [
            {"id": "threshold_meaning", "text": "Explains that below a threshold physical error rate, increasing code size reduces the logical error rate."},
            {"id": "above_threshold", "text": "Notes that above threshold, larger codes make things worse (or don't help)."},
            {"id": "locality", "text": "Mentions the surface code needs only nearest-neighbour checks on a 2D grid."},
            {"id": "threshold_value_or_cost", "text": "Gives the rough threshold (~1%) or the qubit overhead cost."},
        ],
    },
    {
        "id": "explain_quantum_advantage_pitch",
        "paths": ["business"],
        "prompt": "A client asks whether they should invest in quantum computing for their logistics optimization today. Give a balanced answer.",
        "rubric": [
            {"id": "current_state", "text": "Is honest that current devices are noisy and haven't shown clear advantage on practical optimization problems."},
            {"id": "classical_baseline", "text": "Recommends comparing against strong classical solvers / heuristics."},
            {"id": "realistic_path", "text": "Suggests a realistic path: exploration, skills building, small pilots, or monitoring progress, rather than production deployment."},
            {"id": "no_hype", "text": "Avoids overclaiming (e.g. doesn't promise exponential speedups for optimization)."},
        ],
    },
]

DESIGN_PROMPTS = [
    {
        "id": "design_vqe_cloud",
        "paths": ["software", "research"],
        "prompt": "Design a hybrid quantum-classical service that runs VQE on cloud quantum hardware for many users. Describe the main components and how data flows between them.",
        "rubric": [
            {"id": "classical_optimizer", "text": "Separates the classical optimizer loop from quantum execution."},
            {"id": "batching_sessions", "text": "Addresses queueing/latency: batching circuits, sessions, or parameter sweeps to reduce round trips."},
            {"id": "transpile_cache", "text": "Mentions compiling/transpiling for the target device, ideally once with parameter binding or caching."},
            {"id": "mitigation_shots", "text": "Accounts for noise: shot budgets, error mitigation, or measurement grouping of Pauli terms."},
            {"id": "failure_handling", "text": "Mentions reliability concerns: retries, job failures, calibration drift, or monitoring."},
        ],
    },
    {
        "id": "design_transpiler_pass",
        "paths": ["software"],
        "prompt": "Design a compiler pass that reduces two-qubit gate count for circuits running on a device with limited connectivity. What would it do, and how would you make sure it's correct?",
        "rubric": [
            {"id": "layout_routing", "text": "Addresses qubit layout and/or routing (minimizing SWAPs)."},
            {"id": "rewrite_rules", "text": "Uses concrete optimizations: gate cancellation, commutation, resynthesis of 2-qubit blocks, or similar."},
            {"id": "verification", "text": "Verifies correctness, e.g. unitary equivalence checks on small circuits or randomized tests."},
            {"id": "tradeoffs", "text": "Discusses trade-offs: compile time, depth vs. gate count, or heuristic vs. optimal."},
        ],
    },
    {
        "id": "design_calibration",
        "paths": ["hardware"],
        "prompt": "Design an automated calibration pipeline for a 20-qubit superconducting device. What would it measure, how often, and what would it do with the results?",
        "rubric": [
            {"id": "what_measured", "text": "Lists concrete quantities: qubit frequencies, T1/T2, gate fidelities (e.g. randomized benchmarking), readout fidelity."},
            {"id": "scheduling", "text": "Addresses how often each is recalibrated or detecting drift to trigger recalibration."},
            {"id": "dependencies", "text": "Notes ordering/dependencies between calibrations (e.g. frequency before pulse amplitude)."},
            {"id": "feeds_compiler", "text": "Feeds results downstream: compiler/noise model, qubit selection, or alerting."},
        ],
    },
    {
        "id": "design_quantum_offering",
        "paths": ["business"],
        "prompt": "Outline how a company could help enterprise clients evaluate whether quantum computing is relevant to them. What would the engagement look like?",
        "rubric": [
            {"id": "problem_discovery", "text": "Starts by identifying candidate problems and their structure, not with the technology."},
            {"id": "baseline", "text": "Benchmarks against classical methods."},
            {"id": "realistic_timeline", "text": "Sets realistic expectations about hardware timelines."},
            {"id": "deliverables", "text": "Defines concrete deliverables: a feasibility report, proof of concept, resource estimates, or a skills plan."},
        ],
    },
]

PROMPTS_BY_ID = {p["id"]: p for p in EXPLAIN_PROMPTS + DESIGN_PROMPTS}


def public_prompt(prompt):
    """What the client sees. The rubric is shown after answering, not before."""
    return {"id": prompt["id"], "prompt": prompt["prompt"]}


def for_path(prompts, path):
    matching = [p for p in prompts if not p["paths"] or path in p["paths"]]
    return matching or prompts
