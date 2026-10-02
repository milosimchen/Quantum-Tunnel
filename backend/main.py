from fastapi import FastAPI, HTTPException
from circuit_safety import build_circuit, CircuitInputError, MAX_QUBITS
from pydantic import BaseModel
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from simplify import simplify_fully, circuit_to_gate_list, gate_list_to_circuit
from motifs import find_motifs
from targets import find_matching_target, TARGETS, NAMED_CIRCUITS, instantiate_named_circuit, find_closest_target, find_single_gate_completion

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
import os
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from equivalence import circuits_equivalent, is_fully_entangled, format_dirac_notation
from qiskit.quantum_info import Statevector

import re
load_dotenv()
llm_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

app.add_middleware(
    CORSMiddleware,
    # Comma-separated list, e.g. "http://localhost:5173,https://quantum-studio.vercel.app"
    allow_origins=[
        origin.strip()
        for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
CIRCUIT_ANALYSIS_TOOL = {
    "name": "report_circuit_analysis",
    "description": "Report a structured analysis of the verified circuit simplification data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "step_summaries": {
                "type": "array",
                "description": "One entry per simplification step, in order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_number": {"type": "integer"},
                        "rule_applied": {"type": "string"},
                    },
                    "required": ["step_number", "rule_applied"],
                },
            },
            "interpretation": {
                "type": "string",
                "description": "Free-form reasoning, comparisons, or notes. Must NOT contain any numbers -- refer to steps only by their step_number.",
            },
            "limitations": {
                "type": "string",
                "description": "What this analysis does not check or guarantee.",
            },
        },
        "required": ["step_summaries", "interpretation", "limitations"],
    },
}

CHAT_ANSWER_TOOL = {
    "name": "answer_circuit_question",
    "description": "Answer a question about verified circuit data using placeholders for any numeric value, never literal numbers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "can_answer": {
                "type": "boolean",
                "description": "Whether the verified data contains enough information to answer the question.",
            },
            "answer_template": {
                "type": "string",
                "description": (
                    "The answer text. Every numeric value MUST be written as a "
                    "placeholder like {field_name} referencing one of the valid "
                    "fields -- NEVER write a literal number directly. Plain text "
                    "like 'Step 2' or 'the S^4 rule' is fine and not a placeholder."
                ),
            },
            "fields_used": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Every field_name placeholder used in answer_template, listed exactly as written.",
            },
        },
        "required": ["can_answer", "answer_template", "fields_used"],
    },
}
VERIFICATION_TOOL = {
    "name": "verify_claims",
    "description": "Check every comparative or qualitative claim in a draft answer against the actual raw data for ALL steps, not just the one being discussed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "consistent": {
                "type": "boolean",
                "description": "True only if every comparative/qualitative claim in the draft is fully supported by the raw data for every step it mentions or implicitly compares.",
            },
            "issues": {
    "type": "array",
    "items": {"type": "string"},
    "description": "ONLY genuine factual inconsistencies. If a claim is correct, do NOT mention it here at all -- do not include confirmations, explanations of why something is fine, or reasoning that concludes 'this is accurate'. This array must contain ONLY problems, or be empty.",
},
        },
        "required": ["consistent", "issues"],
    },
}

CIRCUIT_GENERATION_TOOL = {
    "name": "generate_circuit",
    "description": "Interpret a natural-language circuit-building request and return either a named pattern to instantiate, or an explicit gate list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "can_fulfill": {
                "type": "boolean",
                "description": "Whether the request can be fulfilled at all.",
            },
            "clarification_needed": {
                "type": "string",
                "description": "If can_fulfill is false, explain what's missing or ambiguous. Empty string otherwise.",
            },
            "action": {
                "type": "string",
                "enum": ["replace", "append"],
                "description": "'append' if the request implies adding to the existing circuit (e.g. 'add', 'also', 'then', 'now add'). 'replace' if it implies starting fresh (e.g. 'build', 'make', 'start over', or the circuit is currently empty).",
            },
            "request_type": {
                 "type": "string",
                    "enum": ["named_pattern", "explicit_gates", "goal_directed"],
                    "description": "'named_pattern' if a known circuit is named. 'explicit_gates' if gates are specified directly with no properties to verify. 'goal_directed' if the request describes properties/goals the circuit must satisfy (entanglement, gate count, Clifford-only, equivalence to a target, measurement probability, etc.) -- propose a circuit in explicit_gate_list AND fill in the goals field for independent verification.",
            },
            "pattern_name": {
                "type": "string",
                "description": "For named_pattern requests: the exact registry key (e.g. 'bell_state', 'ghz_state', 'swap_gate'). Empty string for explicit_gates.",
            },
            "target_qubits": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "For named_pattern requests: which real qubit indices to place the pattern on, in order.",
            },
            "explicit_gate_list": {
                "type": "array",
                "description": "For explicit_gates requests: the gates to build, in order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "qubits": {"type": "array", "items": {"type": "integer"}},
                        "params": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["name", "qubits", "params"],
                },
            },
            "goals": {
                 "type": "object",
                 "description": "Only used when request_type is 'goal_directed'. Explicitly declare every goal you are targeting.",
                "properties": {
                    "gate_count": {"type": "integer"},
                     "min_gate_count": {"type": "integer"},
                     "max_gate_count": {"type": "integer"},
                     "depth": {"type": "integer"},
                        "min_depth": {"type": "integer"},
                     "max_depth": {"type": "integer"},
                     "allowed_gates": {"type": "array", "items": {"type": "string"}, "description": "Use ['h','s','cx','x','y','z'] for 'Clifford', add 't' for 'Clifford+T'."},
                        "forbidden_gates": {"type": "array", "items": {"type": "string"}},
                        "distinct_gate_types": {"type": "integer"},
                        "fully_entangled": {"type": "boolean"},
                        "equivalent_to_target": {"type": "string"},
                        "measurement_probability": {
                            "type": "object",
                            "properties": {
                                "qubit": {"type": "integer"},
                                "outcome": {"type": "string", "enum": ["0", "1"]},
                                "comparator": {"type": "string", "enum": ["gt", "lt", "gte", "lte", "eq"]},
                                "probability": {"type": "number"},
                            },
                        },
                    },
                },
        },
        "required": ["can_fulfill", "clarification_needed", "action", "request_type", "pattern_name", "target_qubits", "explicit_gate_list"],
    },
}

GOAL_CIRCUIT_TOOL = {
    "name": "propose_goal_circuit",
    "description": "Propose a quantum circuit satisfying stated structural goals, to be independently verified before acceptance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "can_fulfill": {"type": "boolean"},
            "clarification_needed": {"type": "string"},
            "num_qubits": {"type": "integer"},
            "gate_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "qubits": {"type": "array", "items": {"type": "integer"}},
                        "params": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["name", "qubits", "params"],
                },
            },
            "goals": {
                "type": "object",
                "description": "Explicitly declare every goal you are targeting, extracted from the request. Omit any goal type not mentioned or implied.",
                "properties": {
                    "gate_count": {"type": "integer", "description": "Exact gate count, if requested."},
                    "min_gate_count": {"type": "integer"},
                    "max_gate_count": {"type": "integer"},
                    "depth": {"type": "integer", "description": "Exact depth, if requested."},
                    "min_depth": {"type": "integer"},
                    "max_depth": {"type": "integer"},
                    "allowed_gates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "If the request restricts to a gate set. Use ['h','s','cx','x','y','z'] for 'Clifford', and add 't' for 'Clifford+T'.",
                    },
                    "forbidden_gates": {"type": "array", "items": {"type": "string"}},
                    "distinct_gate_types": {"type": "integer", "description": "Exact count of unique gate types used, if requested."},
                    "fully_entangled": {"type": "boolean"},
                    "equivalent_to_target": {
                        "type": "string",
                        "description": "If the request asks for equivalence to a known named circuit, its exact registry key.",
                    },
                    "measurement_probability": {
                        "type": "object",
                        "properties": {
                            "qubit": {"type": "integer"},
                            "outcome": {"type": "string", "enum": ["0", "1"]},
                            "comparator": {"type": "string", "enum": ["gt", "lt", "gte", "lte", "eq"]},
                            "probability": {"type": "number"},
                        },
                        "description": "If the request specifies a measurement outcome probability constraint on a specific qubit.",
                    },
                },
            },
        },
        "required": ["can_fulfill", "clarification_needed", "num_qubits", "gate_list", "goals"],
    },
}


DISPLAY_NAMES = {
    "bell_state": "Bell state",
    "ghz_state": "GHZ state",
    "ghz_state_3": "GHZ state",
    "teleportation": "quantum teleportation",
    "bell_pair": "Bell pair",
    "swap_gate": "SWAP gate",
    "cz_via_hadamard": "CZ (via Hadamard identity)",
    "repetition_code": "repetition code",
    "teleportation_prep": "teleportation prep",
}

def display_name(internal_name):
    return DISPLAY_NAMES.get(internal_name, internal_name)


# --- Request shape ---
# A circuit is described as: how many qubits, and a list of gates.
# Each gate is a name (e.g. "h", "cx"), which qubit(s) it acts on,
# and optional params (e.g. an angle for rotation gates).

class GateInstruction(BaseModel):
    name: str
    qubits: list[int]
    params: list[float] = []


class CircuitRequest(BaseModel):
    num_qubits: int
    gates: list[GateInstruction]

class ChatRequest(BaseModel):
    num_qubits: int
    gates: list[GateInstruction]
    question: str

class GenerateCircuitRequest(BaseModel):
    request: str
    current_gates: list[GateInstruction] = []

class GoalCircuitRequest(BaseModel):
    request: str


JOBS_PER_PAGE = 20


class JobSearchRequest(BaseModel):
    query: str = ""
    location: str = ""
    page: int = 1
    sort: str = "date"
    quantum_titles_only: bool = True
    max_days_old: int | None = None
    full_time_only: bool = False


def build_circuit_from_request(circuit_request: CircuitRequest) -> QuantumCircuit:
    """Convert untrusted request data into a Qiskit circuit (validated; see circuit_safety.py)."""
    try:
        return build_circuit(
            [(g.name, g.qubits, g.params) for g in circuit_request.gates],
            circuit_request.num_qubits,
        )
    except CircuitInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
def root():
    return {"status": "Quantum Studio backend is running"}


@app.post("/simulate")
def simulate(circuit_request: CircuitRequest):
    qc = build_circuit_from_request(circuit_request)

    qc_measured = qc.copy()
    qc_measured.measure_all()

    simulator = AerSimulator()
    result = simulator.run(qc_measured, shots=1000).result()
    counts = result.get_counts()

    return {
        "gate_count": len(qc.data),
        "measurement_counts": counts,
    }


@app.post("/scan")
def scan(circuit_request: CircuitRequest):
    qc = build_circuit_from_request(circuit_request)

    simplified_circuit, simplification_steps = simplify_fully(qc)
    motif_matches = find_motifs(qc)
    target_match = find_matching_target(qc)

    return {
        "original_gate_count": len(qc.data),
        "simplified_gate_count": len(simplified_circuit.data),
        "simplification_steps": simplification_steps,
        "motifs_found": [
            {"motif": m["motif"], "qubits": list(m["qubits"])}
            for m in motif_matches
        ],
        "target_match": target_match,
    }




@app.post("/explain")
def explain(circuit_request: CircuitRequest):
    qc = build_circuit_from_request(circuit_request)

    simplified_circuit, simplification_steps = simplify_fully(qc)
    motif_matches = find_motifs(qc)
    target_match = find_matching_target(qc)


    closest_target_info = None
    if target_match is None:
        closest = find_closest_target(qc)
        if closest is not None:
            distance, closest_name, diff_ops = closest
            diff_summary = "; ".join(
                f"{op[0]} {op[1][0].upper()} on q{list(op[1][1])}" if len(op) == 2
                else f"substitute {op[1][0].upper()} on q{list(op[1][1])} -> {op[2][0].upper()} on q{list(op[2][1])}"
                for op in diff_ops if op[0] != "match"
            )
            closest_target_info = {
                "name": closest_name,
                "distance": distance,
                "diff_summary": diff_summary or "no differing operations",
            }

    single_gate_completion = find_single_gate_completion(qc)
    single_gate_completion_info = None
    if single_gate_completion is not None:
        completion_target_name, gate_to_add = single_gate_completion
        single_gate_completion_info = {
            "target_name": completion_target_name,
            "gate_name": gate_to_add[0],
            "gate_qubits": list(gate_to_add[1]),
        }

    final_circuit_gates = [
        {"name": name, "qubits": list(qubits), "params": list(params)}
        for name, qubits, params in circuit_to_gate_list(simplified_circuit)
    ]

    steps_detail = "\n".join(
        f"- Step {i+1}: {s['rule']} | gates {s['before_gate_count']}->{s['after_gate_count']}, "
        f"depth {s['before_depth']}->{s['after_depth']}"
        for i, s in enumerate(simplification_steps)
    ) or "None found."

    verified_summary = f"""
Original: {len(qc.data)} gates, depth {qc.depth()}
Final: {len(simplified_circuit.data)} gates, depth {simplified_circuit.depth()}
Simplification steps (in order applied):
{steps_detail}
Motifs recognized: {[f"{display_name(m['motif'])} on qubits {m['qubits']}" for m in motif_matches] if motif_matches else 'none'}
Target match: {display_name(target_match) if target_match else 'none'}
{f"Closest known target (no exact match found): '{closest_target_info['name']}', edit distance {closest_target_info['distance']} (lower is closer; report this number honestly rather than always implying closeness). Specific differences: {closest_target_info['diff_summary']}" if closest_target_info else ""}
{f"Single-gate completion available: adding {single_gate_completion_info['gate_name'].upper()} on qubits {single_gate_completion_info['gate_qubits']} would EXACTLY complete a match to '{display_name(single_gate_completion_info['target_name'])}'. This is a confirmed, verified fact -- state it directly and specifically as a concrete next step, not a vague suggestion." if single_gate_completion_info else ""}
"""

    response = llm_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        tools=[CIRCUIT_ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "report_circuit_analysis"},
        system=(
            "You are analyzing pre-verified quantum circuit simplification "
            "data for an experienced quantum computing practitioner. Do NOT "
            "use encouraging or congratulatory language. You must call the "
            "report_circuit_analysis tool, and you MUST include all three "
            "required fields: step_summaries, interpretation, and "
            "limitations -- never omit any of them, even for complex "
            "circuits with many steps. Do not include any numbers in "
            "the interpretation field -- refer to steps only by step_number. "
            "Do not use markdown tables (pipe/dash syntax) in the "
            "interpretation field; use plain sentences or a simple bulleted "
            "list instead. Never invent claims beyond the data given. "
            "Motif recognition and simplification are independent systems: "
            "motifs identify structural patterns, while simplification "
            "finds redundant gates. A motif being present does not imply "
            "the circuit should or could be simplified, and the absence of "
            "simplification is not evidence of a problem with motif "
            "detection or vice versa. Do not speculate about a "
            "relationship between them or describe their co-occurrence as "
            "a mismatch, tension, or anomaly. If a 'closest known target' is "
            "provided in the verified data (meaning no exact target match was "
            "found), you may mention it, but you must communicate the actual "
            "edit distance honestly -- a distance of 1-2 genuinely suggests "
            "the circuit is close to that pattern, but a larger distance "
            "(roughly half or more of the target's own gate count) means the "
            "circuit does NOT meaningfully resemble that target, and you "
            "should say so plainly rather than framing it as 'you're close.' "
            "Do not soften or hide a large distance."
        ),
        messages=[
            {"role": "user", "content": f"Verified results:\n{verified_summary}\n\nAnalyze this."}
        ]
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    structured_result = tool_use_block.input

    # Defensive: never assume any "required" schema field actually exists.
    step_summaries = structured_result.get("step_summaries", [])
    interpretation_text = structured_result.get("interpretation")
    limitations_text = structured_result.get(
        "limitations", "No limitations were provided by the analysis."
    )

    for step_summary in step_summaries:
        step_index = step_summary.get("step_number", 0) - 1
        if 0 <= step_index < len(simplification_steps):
            real_step = simplification_steps[step_index]
            step_summary["before_gate_count"] = real_step["before_gate_count"]
            step_summary["after_gate_count"] = real_step["after_gate_count"]
            step_summary["before_depth"] = real_step["before_depth"]
            step_summary["after_depth"] = real_step["after_depth"]

    biggest_depth_reduction_step = None
    if simplification_steps:
        biggest_depth_reduction_step = max(
            range(len(simplification_steps)),
            key=lambda i: simplification_steps[i]["before_depth"] - simplification_steps[i]["after_depth"]
        ) + 1

    interpretation_check = verify_interpretation_against_data(
        interpretation_text or "", simplification_steps, motif_matches, target_match,
        len(qc.data), qc.depth(), len(simplified_circuit.data), simplified_circuit.depth(), closest_target_info
    )

    final_interpretation = interpretation_text

    is_consistent = interpretation_check.get("consistent", False)

    if not is_consistent:
        issues_found = interpretation_check.get("issues", ["No specific issues were returned by the verification check."])

        retry_response = llm_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            tools=[CIRCUIT_ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "report_circuit_analysis"},
            system=(
                "You are analyzing pre-verified quantum circuit simplification "
                "data. Your previous interpretation contained factual errors. "
                "Correct them precisely. You MUST include all three required "
                "fields: step_summaries, interpretation, and limitations. Do "
                "not use encouraging language. Do not include any numbers in "
                "the interpretation field -- refer to steps only by step_number. "
                "Never invent claims beyond the data given."
            ),
            messages=[
                {"role": "user", "content": f"Verified results:\n{verified_summary}\n\nAnalyze this."},
                {"role": "assistant", "content": [{"type": "tool_use", "id": tool_use_block.id, "name": "report_circuit_analysis", "input": structured_result}]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": tool_use_block.id, "content": "Your interpretation had errors."},
                    {"type": "text", "text": f"Specific issues found: {issues_found}. Please correct your interpretation field, fixing exactly these issues, and call the tool again."}
                ]}
            ]
        )
        retry_tool_block = next(
            block for block in retry_response.content if block.type == "tool_use"
        )
        retry_result = retry_tool_block.input
        retry_interpretation = retry_result.get("interpretation")

        retry_check = verify_interpretation_against_data(
            retry_interpretation or "", simplification_steps, motif_matches, target_match,
            len(qc.data), qc.depth(), len(simplified_circuit.data), simplified_circuit.depth(), closest_target_info
        )

        if retry_check.get("consistent", False) and retry_interpretation is not None:
            final_interpretation = retry_interpretation
            interpretation_check = retry_check
            # Also refresh step_summaries/limitations from the retry, since
            # a corrected response should be treated as the authoritative one.
            step_summaries = retry_result.get("step_summaries", step_summaries)
            limitations_text = retry_result.get("limitations", limitations_text)
            for step_summary in step_summaries:
                step_index = step_summary.get("step_number", 0) - 1
                if 0 <= step_index < len(simplification_steps):
                    real_step = simplification_steps[step_index]
                    step_summary["before_gate_count"] = real_step["before_gate_count"]
                    step_summary["after_gate_count"] = real_step["after_gate_count"]
                    step_summary["before_depth"] = real_step["before_depth"]
                    step_summary["after_depth"] = real_step["after_depth"]
        else:
            final_interpretation = None
            interpretation_check = retry_check

    step_lines = "\n".join(
        f"Step {s.get('step_number', '?')}: {s.get('rule_applied', 'unknown rule')} "
        f"(gates {s.get('before_gate_count', '?')}->{s.get('after_gate_count', '?')}, "
        f"depth {s.get('before_depth', '?')}->{s.get('after_depth', '?')})"
        for s in step_summaries
    )

    step_section = f"{step_lines}\n\n" if step_lines else ""

    if final_interpretation is not None:
        explanation_text = (
            f"{step_section}"
            f"Interpretation: {final_interpretation}\n\n"
            f"Limitations: {limitations_text}"
        )
    else:
        explanation_text = (
            f"{step_section}"
            f"Interpretation: [Suppressed -- could not be verified against "
            f"the underlying data after one correction attempt. Only "
            f"verified step-by-step data is shown above.]\n\n"
            f"Limitations: {limitations_text}"
        )

    return {
        "original_gate_count": len(qc.data),
        "original_depth": qc.depth(),
        "simplified_gate_count": len(simplified_circuit.data),
        "simplified_depth": simplified_circuit.depth(),
        "simplification_steps": simplification_steps,
        "step_summaries": step_summaries,
        "interpretation": final_interpretation,
        "limitations": limitations_text,
        "biggest_depth_reduction_step": biggest_depth_reduction_step,
        "interpretation_check": interpretation_check,
        "final_circuit_gates": final_circuit_gates,
        "motifs_found": [
            {"motif": m["motif"], "qubits": list(m["qubits"])}
            for m in motif_matches
        ],
        "target_match": target_match,
        "single_gate_completion": single_gate_completion_info,
        "explanation": explanation_text,
    }


@app.post("/chat")
def chat(chat_request: ChatRequest):
    circuit_request = CircuitRequest(
        num_qubits=chat_request.num_qubits,
        gates=chat_request.gates,
    )
    qc = build_circuit_from_request(circuit_request)

    simplified_circuit, simplification_steps = simplify_fully(qc)
    motif_matches = find_motifs(qc)
    target_match = find_matching_target(qc)

    steps_detail = "\n".join(
        f"- Step {i+1}: {s['rule']} | gates {s['before_gate_count']}->{s['after_gate_count']}, "
        f"depth {s['before_depth']}->{s['after_depth']}"
        for i, s in enumerate(simplification_steps)
    ) or "None found."

    verified_summary = f"""
Original: {len(qc.data)} gates, depth {qc.depth()}
Final: {len(simplified_circuit.data)} gates, depth {simplified_circuit.depth()}
Simplification steps (in order applied):
{steps_detail}
Motifs recognized: {[f"{display_name(m['motif'])} on qubits {m['qubits']}" for m in motif_matches] if motif_matches else 'none'}
Target match: {display_name(target_match) if target_match else 'none'}
"""

    verified_data = {
        "original_gate_count": len(qc.data),
        "original_depth": qc.depth(),
        "simplified_gate_count": len(simplified_circuit.data),
        "simplified_depth": simplified_circuit.depth(),
    }
    for i, step in enumerate(simplification_steps[:3], start=1):
        verified_data[f"step_{i}_before_gate_count"] = step["before_gate_count"]
        verified_data[f"step_{i}_after_gate_count"] = step["after_gate_count"]
        verified_data[f"step_{i}_before_depth"] = step["before_depth"]
        verified_data[f"step_{i}_after_depth"] = step["after_depth"]

    valid_fields_list = ", ".join(verified_data.keys())

    response = llm_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        tools=[CHAT_ANSWER_TOOL],
        tool_choice={"type": "tool", "name": "answer_circuit_question"},
        system=(
            "You are answering a question about pre-verified quantum circuit "
            "analysis results, for an experienced quantum computing "
            "practitioner. You must call the answer_circuit_question tool. "
            f"Valid field names you may reference as placeholders: {valid_fields_list}. "
            "Never write a literal number in answer_template -- always use "
            "{field_name} placeholders for any numeric value. If the data "
            "doesn't answer the question, set can_answer to false and explain "
            "what's missing in answer_template (with no placeholders needed). "
            "Never invent claims beyond the data given. Be precise and terse."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Verified results for the current circuit:\n{verified_summary}\n\nQuestion: {chat_request.question}"
            }
        ]
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    result = tool_use_block.input

    final_answer = result["answer_template"]
    invalid_fields = []
    for field_name in result["fields_used"]:
        if field_name in verified_data:
            final_answer = final_answer.replace(f"{{{field_name}}}", str(verified_data[field_name]))
        else:
            invalid_fields.append(field_name)

    verification = verify_interpretation_against_data(
        final_answer, simplification_steps, motif_matches, target_match,
        len(qc.data), qc.depth(), len(simplified_circuit.data), simplified_circuit.depth()
    )

    return {
        "answer": final_answer,
        "can_answer": result["can_answer"],
        "invalid_fields_referenced": invalid_fields,
        "verification": verification,
    }

def verify_facts_section(response_text, verified_data):
    """
    Rigorously check the FACTS section of a response:
    1. Every bracketed citation must match the exact format [field = number].
       Anything else in brackets is an automatic failure (not skipped).
    2. The field must exist in verified_data (exact dotted path).
    3. The cited value must numerically match the real value.
    4. Any number appearing in the FACTS section with NO citation at all
       is also a failure.
    Returns a list of failure descriptions (empty list = fully verified).
    """
    failed = []

    # Only check the FACTS section, not the INTERPRETATION section
    if "FACTS:" not in response_text:
        return ["No FACTS: section found in response"]

    facts_section = response_text.split("FACTS:")[1]
    if "INTERPRETATION:" in facts_section:
        facts_section = facts_section.split("INTERPRETATION:")[0]

    # Flatten verified_data into dotted paths -> numeric values only
    def flatten(d, prefix=""):
        flat = {}
        for key, value in d.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(flatten(value, path))
            elif isinstance(value, (int, float)):
                flat[path] = value
            # non-numeric fields (like 'rule' text) are intentionally excluded --
            # only numbers require citation under this scheme
        return flat

    allowed_fields = flatten(verified_data)

    # Step 1: find every bracketed segment, however it's formatted
    bracket_contents = re.findall(r'\[([^\]]*)\]', facts_section)

    # Track which character positions were inside brackets, so we can
    # separately check for un-cited numbers later
    cited_spans = []
    for match in re.finditer(r'\[([^\]]*)\]', facts_section):
        cited_spans.append((match.start(), match.end()))

    strict_citation_pattern = re.compile(r'^\s*([\w\.]+)\s*=\s*(-?\d+(?:\.\d+)?)\s*$')

    for content in bracket_contents:
        match = strict_citation_pattern.match(content)
        if not match:
            failed.append(f"Malformed citation: [{content}] does not match 'field = number' format")
            continue

        field_path, claimed_value_str = match.groups()

        if field_path not in allowed_fields:
            failed.append(f"Unknown field cited: '{field_path}' is not a real verified field")
            continue

        actual_value = allowed_fields[field_path]
        try:
            if float(claimed_value_str) != float(actual_value):
                failed.append(
                    f"Value mismatch: [{field_path} = {claimed_value_str}] "
                    f"but actual value is {actual_value}"
                )
        except ValueError:
            failed.append(f"Could not parse claimed value '{claimed_value_str}' as a number")

    # Step 2: check for numbers stated with NO citation at all
    text_without_citations = re.sub(r'\[[^\]]*\]', '', facts_section)
    # Ignore "Step 1", "Step 2" etc. -- these are labels, not data claims
    text_without_step_labels = re.sub(r'\bStep\s+\d+\b', '', text_without_citations)
    uncited_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text_without_step_labels)

    if uncited_numbers:
        failed.append(
            f"Uncited number(s) found in FACTS section with no bracket "
            f"reference: {uncited_numbers}"
        )

    return failed

def verify_interpretation_against_data(
    draft_text,
    simplification_steps,
    motif_matches=None,
    target_match=None,
    original_gate_count=None,
    original_depth=None,
    simplified_gate_count=None,
    simplified_depth=None,
    closest_target_info=None,
):
    """
    Second-pass check: ask the LLM to verify a draft's comparative/qualitative
    claims against the FULL raw context (not just whichever step the draft
    focuses on). This must include EVERY category of data the original
    interpretation was allowed to reference -- steps, motifs, target match,
    AND overall gate count/depth totals -- otherwise the checker will
    falsely flag true claims it simply wasn't shown. This is a narrower,
    more checkable task than the original open-ended generation, so it
    catches errors that slip through the first pass -- though it is a
    reduction in error rate, not a proof.
    """
    if (
        not simplification_steps
        and not motif_matches
        and not target_match
        and original_gate_count is None
        and original_depth is None
    ):
        return {"consistent": True, "issues": []}

    raw_data_lines = "\n".join(
        f"Step {i+1}: rule={s['rule']}, gates {s['before_gate_count']}->{s['after_gate_count']}, "
        f"depth {s['before_depth']}->{s['after_depth']}"
        for i, s in enumerate(simplification_steps)
    ) or "No simplification steps."

    motif_lines = (
        ", ".join(f"{m['motif']} on qubits {m['qubits']}" for m in motif_matches)
        if motif_matches else "None detected."
    )

    target_line = target_match if target_match else "No target match."
    closest_target_line = (
        f"Closest known target (no exact match): '{closest_target_info['name']}', "
        f"edit distance {closest_target_info['distance']}. Differences: {closest_target_info['diff_summary']}"
        if closest_target_info else "No closest-target information provided."
    )

    overall_lines = (
        f"Overall original: {original_gate_count} gates, depth {original_depth}\n"
        f"Overall final: {simplified_gate_count} gates, depth {simplified_depth}"
    )

    full_context = (
        f"{overall_lines}\n\n"
        f"Simplification steps:\n{raw_data_lines}\n\n"
        f"Motifs detected: {motif_lines}\n\n"
        f"Target match: {target_line}"
        f"{closest_target_line}"
    )

    response = llm_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        tools=[VERIFICATION_TOOL],
        tool_choice={"type": "tool", "name": "verify_claims"},
        system=(
            "You are a strict fact-checker. You will be given the COMPLETE "
            "raw verified data available (overall gate count/depth, "
            "simplification steps, motifs detected, and target match), and "
            "a draft answer that makes claims about it.\n\n"
            "Mark a claim 'inconsistent' ONLY if it does one of these two "
            "things:\n"
            "1. States a number, comparison, or ranking that contradicts the "
            "actual data (e.g. wrong depth value, wrong 'which step was "
            "biggest', wrong gate count).\n"
            "2. Describes something (a motif, a target match, a step, an "
            "overall gate count or depth) that does not exist anywhere in "
            "the data at all.\n\n"
            "Do NOT mark a claim inconsistent merely because it uses different "
            "wording, a synonym, an informal name for a rule (e.g. 'phase-gate "
            "redundancy' for S^4 = I), or a paraphrase of something that IS "
            "supported by the data. Different phrasing of a true statement is "
            "still consistent.\n\n"
            "If uncertain whether a claim falls into category 1 or 2 above, "
            "err toward flagging it as inconsistent -- but wording choice "
            "alone is never sufficient grounds.\n\n"
            "Only add an entry to 'issues' if it describes an actual "
            "inconsistency. Never add an entry that concludes a claim is "
            "correct or accurate -- if every claim checks out, issues must "
            "be an empty list. You must call the verify_claims tool."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Complete raw verified data:\n{full_context}\n\nDraft answer to check:\n{draft_text}"
            }
        ]
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    result = tool_use_block.input

    issues = result.get("issues", [])
    return {"consistent": len(issues) == 0, "issues": issues}


SUPPORTED_GATES = [
    {"name": "h", "num_params": 0, "num_qubits": 1},
    {"name": "x", "num_params": 0, "num_qubits": 1},
    {"name": "y", "num_params": 0, "num_qubits": 1},
    {"name": "z", "num_params": 0, "num_qubits": 1},
    {"name": "s", "num_params": 0, "num_qubits": 1},
    {"name": "t", "num_params": 0, "num_qubits": 1},
    {"name": "cx", "num_params": 0, "num_qubits": 2},
    {"name": "cz", "num_params": 0, "num_qubits": 2},
    {"name": "rx", "num_params": 1, "num_qubits": 1},
    {"name": "ry", "num_params": 1, "num_qubits": 1},
    {"name": "rz", "num_params": 1, "num_qubits": 1},
    
]


@app.get("/targets")
def list_targets():
    return {
        "targets": [
            {"name": name, "fixed_qubits": info["fixed_qubits"]}
            for name, info in TARGETS.items()
        ]
    }


@app.get("/gates")
def list_gates():
    return {"gates": SUPPORTED_GATES}

@app.post("/generate_circuit")
def generate_circuit(generate_request: GenerateCircuitRequest):
    OPTIMALITY_KEYWORDS = ["minimal", "minimum", "optimal", "smallest possible", "fewest possible", "shortest possible", "most efficient possible"]
    if any(kw in generate_request.request.lower() for kw in OPTIMALITY_KEYWORDS):
        return {
            "success": False,
            "message": (
                "Proving a circuit is truly minimal or optimal isn't something this tool can verify -- "
                "doing so would require either an exhaustive search over every smaller circuit or a formal "
                "optimality proof, neither of which is feasible here. I can build a circuit satisfying your "
                "other stated goals (gate count, depth, entanglement, etc.) instead."
            ),
            "gates": [],
            "num_qubits": 0,
        }
    
    valid_gate_names = {g["name"] for g in SUPPORTED_GATES}
    gate_param_counts = {g["name"]: g["num_params"] for g in SUPPORTED_GATES}
    gate_qubit_counts = {g["name"]: g["num_qubits"] for g in SUPPORTED_GATES}

    named_circuit_list = "\n".join(
        f"- {name} (aliases: {', '.join(info['aliases'])}) "
        f"[{'fixed ' + str(info['fixed_qubits']) + ' qubits' if info['fixed_qubits'] is not None else 'scalable to any qubit count >= 2'}]"
        for name, info in NAMED_CIRCUITS.items()
    )

    current_gates_dicts = [
        {"name": g.name, "qubits": g.qubits, "params": g.params}
        for g in generate_request.current_gates
    ]

    if current_gates_dicts:
        current_summary = (
            f"Current circuit has {len(current_gates_dicts)} gate(s): "
            + ", ".join(f"{g['name'].upper()} on q{g['qubits']}" for g in current_gates_dicts)
        )
    else:
        current_summary = "Current circuit is empty."

    response = llm_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        tools=[CIRCUIT_GENERATION_TOOL],
        tool_choice={"type": "tool", "name": "generate_circuit"},
        system=(
            "You interpret natural-language quantum circuit building requests. "
            "You must call the generate_circuit tool.\n\n"
            f"{current_summary}\n\n"
            f"Known named circuit patterns:\n{named_circuit_list}\n\n"
            "Determine 'action': 'append' if the request implies adding to "
            "the existing circuit, 'replace' if it implies starting fresh. "
            "If the current circuit is empty, action must be 'replace'.\n\n"
            "If the request names one of the known patterns (or a close "
            "synonym), set request_type to 'named_pattern', give the exact "
            "registry key as pattern_name, and specify target_qubits. Leave "
            "explicit_gate_list empty.\n\n"
            "If the request specifies gates directly, set request_type to "
            "'explicit_gates' and fill in explicit_gate_list, each gate with "
            "a name, qubits, and params (empty list if none). Leave "
            f"pattern_name empty and target_qubits empty.\n\nValid gate "
            f"names: {', '.join(sorted(valid_gate_names))}.\n\n"
            "If the request is ambiguous, impossible, or unclear, set "
            "can_fulfill to false and explain what's missing in "
            "clarification_needed. Never invent a pattern name that isn't "
            "in the list above."
        ),
        messages=[
            {"role": "user", "content": f"Request: {generate_request.request}"}
        ]
    )

    tool_use_block = next(
        block for block in response.content if block.type == "tool_use"
    )
    result = tool_use_block.input

    can_fulfill = result.get("can_fulfill", False)
    clarification_needed = result.get("clarification_needed", "")

    if not can_fulfill:
        return {
            "success": False,
            "message": clarification_needed or "The request could not be fulfilled.",
            "gates": current_gates_dicts,
            "num_qubits": max((q for g in current_gates_dicts for q in g["qubits"]), default=-1) + 1,
        }

    action = result.get("action", "replace")
    request_type = result.get("request_type")

    def error_result(message):
        return {
            "success": False,
            "message": message,
            "gates": current_gates_dicts,
            "num_qubits": max((q for g in current_gates_dicts for q in g["qubits"]), default=-1) + 1,
        }

    new_gates = []

    if request_type == "named_pattern":
        pattern_name = result.get("pattern_name", "")
        target_qubits = result.get("target_qubits", [])

        if pattern_name not in NAMED_CIRCUITS:
            return error_result(f"'{pattern_name}' is not a known circuit pattern.")

        try:
            gate_list = instantiate_named_circuit(pattern_name, target_qubits)
        except ValueError as e:
            return error_result(str(e))

        new_gates = [
            {"name": name, "qubits": list(qubits), "params": list(params)}
            for name, qubits, params in gate_list
        ]
        action_message = f"Built '{pattern_name}' on qubits {target_qubits}."

    elif request_type == "explicit_gates":
        explicit_gate_list = result.get("explicit_gate_list", [])

        for gate in explicit_gate_list:
            name = gate.get("name", "")
            qubits = gate.get("qubits", [])
            params = gate.get("params", [])

            if name not in valid_gate_names:
                return error_result(f"'{name}' is not a valid gate. Valid gates: {', '.join(sorted(valid_gate_names))}.")

            expected_qubit_count = gate_qubit_counts[name]
            if len(qubits) != expected_qubit_count:
                return error_result(f"'{name}' requires exactly {expected_qubit_count} qubit(s), but got {len(qubits)}.")

            if any(q < 0 for q in qubits):
                return error_result(f"Qubit indices must be non-negative, got {qubits}.")

            expected_param_count = gate_param_counts[name]
            if len(params) != expected_param_count:
                return error_result(f"'{name}' requires exactly {expected_param_count} parameter(s), but got {len(params)}.")

            new_gates.append({"name": name, "qubits": qubits, "params": params})

        action_message = "Built the requested gates."
    elif request_type == "goal_directed":
        proposed_gate_list = result.get("explicit_gate_list", [])
        proposed_num_qubits = result.get("num_qubits", 0)
        goals = dict(result.get("goals", {}))

        request_lower_check = generate_request.request.lower()
        if "entangl" in request_lower_check and "fully_entangled" not in goals:
            goals["fully_entangled"] = True

        def build_and_check(candidate_gate_list, candidate_num_qubits):
            gate_tuples = [
                (g.get("name", ""), tuple(g.get("qubits", [])), tuple(g.get("params", [])))
                for g in candidate_gate_list
            ]
            actual_max_qubit = max(
                (q for _, qubits, _ in gate_tuples for q in qubits),
                default=-1
            )
            safe_num_qubits = max(candidate_num_qubits, actual_max_qubit + 1)
            candidate_circuit = gate_list_to_circuit(gate_tuples, safe_num_qubits)
            return candidate_circuit, verify_goal_circuit(candidate_circuit, goals)

        try:
            _, failures = build_and_check(proposed_gate_list, proposed_num_qubits)
        except Exception as e:
            return error_result(f"Failed to construct proposed circuit: {e}")

        if failures:
            retry_response = llm_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                tools=[CIRCUIT_GENERATION_TOOL],
                tool_choice={"type": "tool", "name": "generate_circuit"},
                system=f"Your previous proposal failed verification: {failures}. Propose a corrected circuit satisfying the same goals.",
                messages=[
                    {"role": "user", "content": f"Request: {generate_request.request}"}
                ]
            )
            retry_block = next(b for b in retry_response.content if b.type == "tool_use")
            retry_result = retry_block.input
            proposed_gate_list = retry_result.get("explicit_gate_list", [])
            proposed_num_qubits = retry_result.get("num_qubits", 0)

            try:
                _, retry_failures = build_and_check(proposed_gate_list, proposed_num_qubits)
            except Exception as e:
                return error_result(f"Retry failed to construct: {e}")

            if retry_failures:
                return error_result(f"Could not verify the requested goal(s) even after retrying: {retry_failures}")

        new_gates = [
            {"name": g.get("name", ""), "qubits": g.get("qubits", []), "params": g.get("params", [])}
            for g in proposed_gate_list
        ]
        action_message = "Built and verified a circuit satisfying the stated goal(s)."
    else:
        return error_result("Could not determine the request type.")

    if action == "append":
        final_gates = current_gates_dicts + new_gates
        message = f"{action_message} (appended to existing circuit.)"
    else:
        final_gates = new_gates
        message = action_message

    num_qubits = max((q for g in final_gates for q in g["qubits"]), default=-1) + 1

    return {
        "success": True,
        "message": message,
        "gates": final_gates,
        "num_qubits": num_qubits,
    }



def verify_goal_circuit(qc, goals):
    """
    Independently check every stated goal against the actual constructed
    circuit. Returns a list of failure descriptions (empty = all goals met).
    Never trusts the LLM's own claim that a goal was satisfied.
    """
    failures = []

    if "gate_count" in goals:
        actual = len(qc.data)
        if actual != goals["gate_count"]:
            failures.append(f"Requested exactly {goals['gate_count']} gates, but circuit has {actual}.")

    if "min_gate_count" in goals:
        actual = len(qc.data)
        if actual < goals["min_gate_count"]:
            failures.append(f"Requested at least {goals['min_gate_count']} gates, but circuit has only {actual}.")

    if "max_gate_count" in goals:
        actual = len(qc.data)
        if actual > goals["max_gate_count"]:
            failures.append(f"Requested at most {goals['max_gate_count']} gates, but circuit has {actual}.")

    if "depth" in goals:
        actual = qc.depth()
        if actual != goals["depth"]:
            failures.append(f"Requested depth {goals['depth']}, but circuit has depth {actual}.")

    if "min_depth" in goals:
        actual = qc.depth()
        if actual < goals["min_depth"]:
            failures.append(f"Requested minimum depth {goals['min_depth']}, but circuit has depth {actual}.")

    if "max_depth" in goals:
        actual = qc.depth()
        if actual > goals["max_depth"]:
            failures.append(f"Requested maximum depth {goals['max_depth']}, but circuit has depth {actual}.")

    if "allowed_gates" in goals and goals["allowed_gates"]:
        allowed = set(goals["allowed_gates"])
        used = {instruction.operation.name for instruction in qc.data}
        disallowed = used - allowed
        if disallowed:
            failures.append(f"Circuit uses disallowed gate(s): {disallowed}. Allowed: {allowed}.")

    if "forbidden_gates" in goals and goals["forbidden_gates"]:
        forbidden = set(goals["forbidden_gates"])
        used = {instruction.operation.name for instruction in qc.data}
        violating = used & forbidden
        if violating:
            failures.append(f"Circuit uses forbidden gate(s): {violating}.")

    if "distinct_gate_types" in goals:
        used_types = {instruction.operation.name for instruction in qc.data}
        expected = goals["distinct_gate_types"]
        if len(used_types) != expected:
            failures.append(f"Requested exactly {expected} distinct gate type(s), but circuit uses {len(used_types)}: {used_types}.")

    if goals.get("fully_entangled"):
        if not is_fully_entangled(qc):
            failures.append("Requested full entanglement, but not every qubit is entangled with the rest.")

    if goals.get("equivalent_to_target"):
        target_name = goals["equivalent_to_target"]
        if target_name not in NAMED_CIRCUITS:
            failures.append(f"'{target_name}' is not a known named circuit to compare against.")
        else:
            info = NAMED_CIRCUITS[target_name]
            fixed_qubits = info["fixed_qubits"]
            if fixed_qubits is not None and qc.num_qubits != fixed_qubits:
                failures.append(
                    f"Requested equivalence to '{target_name}', which requires "
                    f"{fixed_qubits} qubits, but circuit has {qc.num_qubits}."
                )
            else:
                target_circuit = (
                    info["builder"]() if fixed_qubits is not None else info["builder"](qc.num_qubits)
                )
                if not circuits_equivalent(qc, target_circuit):
                    failures.append(f"Circuit is not equivalent to '{target_name}'.")

    if goals.get("measurement_probability"):
        mp = goals["measurement_probability"]
        try:
            actual_prob = marginal_qubit_probability(qc, mp["qubit"], mp["outcome"])
            threshold = mp["probability"]
            comparator = mp["comparator"]
            comparisons = {
                "gt": actual_prob > threshold,
                "lt": actual_prob < threshold,
                "gte": actual_prob >= threshold,
                "lte": actual_prob <= threshold,
                "eq": abs(actual_prob - threshold) < 1e-6,
            }
            if not comparisons.get(comparator, False):
                failures.append(
                    f"Requested P(qubit {mp['qubit']}={mp['outcome']}) {comparator} {threshold}, "
                    f"but actual probability is {actual_prob:.4f}."
                )
        except (KeyError, IndexError) as e:
            failures.append(f"Could not evaluate measurement_probability goal: {e}")

    return failures

@app.post("/generate_goal_circuit")
def generate_goal_circuit(goal_request: GoalCircuitRequest):
    valid_gate_names = {g["name"] for g in SUPPORTED_GATES}
    OPTIMALITY_KEYWORDS = ["minimal", "minimum", "optimal", "smallest possible", "fewest possible", "shortest possible", "most efficient possible"]
    request_lower_check = goal_request.request.lower()
    if any(kw in request_lower_check for kw in OPTIMALITY_KEYWORDS):
        return {
            "success": False,
            "message": (
                "Proving a circuit is truly minimal or optimal isn't something this tool "
                "can verify -- doing so would require either an exhaustive search over "
                "every smaller circuit or a formal optimality proof, neither of which is "
                "feasible here. I can build a circuit satisfying your other stated goals "
                "(gate count, depth, entanglement, etc.), or you can use the Scan feature "
                "on a circuit you've already built, which IS verified -- but I won't "
                "claim a result is 'optimal' since that can't be honestly checked."
            ),
            "gates": [],
            "num_qubits": 0,
        }
    def propose(extra_instruction=""):
        return llm_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            tools=[GOAL_CIRCUIT_TOOL],
            tool_choice={"type": "tool", "name": "propose_goal_circuit"},
            system=(
                "You propose a quantum circuit satisfying a natural-language "
                "goal description. You must call the propose_goal_circuit "
                "tool. If specific parameters (qubit count, gate count, etc) "
                "aren't specified in the request, use your own reasonable "
                "judgment to choose them. If the request is genuinely "
                "unfulfillable or unclear, set can_fulfill to false and "
                f"explain why.\n\nValid gate names: {', '.join(sorted(valid_gate_names))}."
                f"{extra_instruction}"
            ),
            messages=[
                {"role": "user", "content": f"Goal: {goal_request.request}"}
            ]
        )

    response = propose()
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    result = tool_use_block.input

    if not result.get("can_fulfill", False):
        return {
            "success": False,
            "message": result.get("clarification_needed", "Could not fulfill this request."),
            "gates": [],
            "num_qubits": 0,
        }

    def build_from_result(res):
        gate_list = [
            (g["name"], tuple(g["qubits"]), tuple(g.get("params", [])))
            for g in res["gate_list"]
        ]
        return gate_list_to_circuit(gate_list, res["num_qubits"])

    goals = {}
    goals = dict(result.get("goals", {}))
    if "entangl" in request_lower_check and "fully_entangled" not in goals:
        goals["fully_entangled"] = True
    request_lower = goal_request.request.lower()
    if "entangl" in request_lower:
        goals["fully_entangled"] = True

    try:
        qc = build_from_result(result)
    except Exception as e:
        return {"success": False, "message": f"Failed to construct proposed circuit: {e}", "gates": [], "num_qubits": 0}

    failures = verify_goal_circuit(qc, goals)

    if failures:
        retry_response = propose(
            f"\n\nYour previous proposal failed verification: {failures}. Propose a corrected circuit."
        )
        retry_block = next(b for b in retry_response.content if b.type == "tool_use")
        retry_result = retry_block.input

        if not retry_result.get("can_fulfill", False):
            return {
                "success": False,
                "message": "Could not construct a circuit satisfying the stated goal(s) after one retry.",
                "gates": [],
                "num_qubits": 0,
            }

        try:
            qc = build_from_result(retry_result)
        except Exception as e:
            return {"success": False, "message": f"Retry failed to construct: {e}", "gates": [], "num_qubits": 0}

        retry_failures = verify_goal_circuit(qc, goals)
        if retry_failures:
            return {
                "success": False,
                "message": f"Could not verify the requested goal(s) even after retrying: {retry_failures}",
                "gates": [],
                "num_qubits": 0,
            }
        result = retry_result

    gates_out = [
        {"name": g["name"], "qubits": list(g["qubits"]), "params": list(g.get("params", []))}
        for g in result["gate_list"]
    ]

    return {
        "success": True,
        "message": "Circuit generated and verified.",
        "gates": gates_out,
        "num_qubits": result["num_qubits"],
    }



def marginal_qubit_probability(qc, qubit_index, outcome_bit):
    """
    Exact probability of measuring a specific qubit in a specific state
    (0 or 1), computed directly from the statevector -- not sampled via
    shots, so there's no statistical noise in the check.
    """
    statevector = Statevector(qc)
    probabilities = statevector.probabilities_dict()

    total = 0.0
    for bitstring, probability in probabilities.items():
        # Qiskit's bitstring convention: leftmost character is the
        # highest-indexed qubit, so reverse it to index by qubit number.
        reversed_bits = bitstring[::-1]
        if reversed_bits[qubit_index] == outcome_bit:
            total += probability

    return total

def format_unitary_matrix(qc, tolerance=1e-6):
    """
    Format a circuit's unitary matrix as a readable string grid.
    Real computation via Qiskit's Operator, not LLM-generated.
    """
    matrix = Operator(qc).data
    rows = []
    for row in matrix:
        formatted_entries = []
        for val in row:
            real, imag = round(val.real, 3), round(val.imag, 3)
            if abs(imag) < tolerance:
                formatted_entries.append(f"{real:6.3f}")
            elif abs(real) < tolerance:
                formatted_entries.append(f"{imag:6.3f}i")
            else:
                sign = '+' if imag >= 0 else '-'
                formatted_entries.append(f"({real:.3f}{sign}{abs(imag):.3f}i)")
        rows.append("[" + ", ".join(formatted_entries) + "]")
    return "\n".join(rows)

from qiskit.quantum_info import Operator

class MathDeepDiveRequest(BaseModel):
    circuit_request: CircuitRequest


@app.post("/math_deep_dive")
def math_deep_dive(request: MathDeepDiveRequest):
    qc = build_circuit_from_request(request.circuit_request)
    num_qubits = qc.num_qubits

    unitary_available = num_qubits <= 3
    dirac_available = num_qubits <= 5

    unitary_text = format_unitary_matrix(qc) if unitary_available else None
    dirac_text = format_dirac_notation(qc) if dirac_available else None

    data_summary_parts = [f"Circuit: {num_qubits} qubits, {len(qc.data)} gates."]
    if unitary_text:
        data_summary_parts.append(f"Unitary matrix:\n{unitary_text}")
    else:
        data_summary_parts.append(f"Unitary matrix: not computed (circuit has {num_qubits} qubits; capped at 3 for readability).")
    if dirac_text:
        data_summary_parts.append(f"Resulting state (Dirac notation, from |0...0> input): {dirac_text}")
    else:
        data_summary_parts.append(f"Dirac notation: not computed (circuit has {num_qubits} qubits; capped at 5 for readability).")

    data_summary = "\n\n".join(data_summary_parts)

    response = llm_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=(
            "You are given an EXACTLY COMPUTED unitary matrix and/or Dirac "
            "notation for a quantum circuit -- these numbers are already "
            "correct and verified; you must never recompute, correct, or "
            "second-guess them. Your only job is to add brief, plain-language "
            "observations about what they show (e.g. 'this is an equal "
            "superposition', 'this state is entangled', 'this matrix is a "
            "permutation matrix'). Do not restate the raw numbers verbatim -- "
            "describe their significance. 2-4 sentences. If a representation "
            "was not computed due to size, do not speculate about what it "
            "would show. Do not use markdown formatting (no asterisks for "
            "bold/italic, no backticks, no headers) since this interface "
            "renders plain text only -- write in plain sentences."
        ),
        messages=[
            {"role": "user", "content": f"Data:\n{data_summary}\n\nProvide brief observations."}
        ]
    )

    return {
        "num_qubits": num_qubits,
        "unitary_matrix": unitary_text,
        "unitary_available": unitary_available,
        "dirac_notation": dirac_text,
        "dirac_available": dirac_available,
        "observations": response.content[0].text,
    }

@app.post("/jobs_search")
def jobs_search(request: JobSearchRequest):
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        return {"success": False, "message": "Job search is not configured.", "jobs": [], "total_count": 0}

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": JOBS_PER_PAGE,
        "sort_by": request.sort if request.sort in ("date", "relevance", "salary") else "date",
    }
    if request.query.strip():
        params["what"] = request.query.strip()
    if request.location.strip():
        params["where"] = request.location.strip()
    # Matching "quantum" anywhere also matches every role at companies with
    # "Quantum" in their name (e.g. their EHS engineers), so by default only
    # titles are matched.
    if request.quantum_titles_only:
        params["title_only"] = "quantum"
    if request.max_days_old:
        params["max_days_old"] = request.max_days_old
    if request.full_time_only:
        params["full_time"] = 1

    try:
        response = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/us/search/{max(1, request.page)}",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return {"success": False, "message": f"Job search failed: {e}", "jobs": [], "total_count": 0}

    jobs_out = []
    seen = set()
    for job in data.get("results", []):
        company = job.get("company", {}).get("display_name", "Unknown")
        location = job.get("location", {}).get("display_name", "")
        # Adzuna often lists the same posting several times (one per board it was scraped from).
        dedupe_key = (job.get("title", "").strip().lower(), company.lower(), location.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        jobs_out.append({
            "id": str(job.get("id")),
            "title": job.get("title"),
            "company": company,
            "location": location,
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            # Most Adzuna salaries are Adzuna's own estimates, not the employer's figure.
            "salary_is_estimate": str(job.get("salary_is_predicted")) == "1",
            "description": job.get("description", ""),
            "apply_url": job.get("redirect_url"),
            "posted": job.get("created"),
            "category": job.get("category", {}).get("label"),
            "contract_time": job.get("contract_time"),
        })

    total = data.get("count", 0)
    return {
        "success": True,
        "message": f"Found {total} total matches.",
        "jobs": jobs_out,
        "total_count": total,
        "page": max(1, request.page),
        "total_pages": max(1, -(-total // JOBS_PER_PAGE)),
    }

# --- Interview Prep ---
# Grading here is fully deterministic (practice.py / interview_questions.py);
# no LLM call is involved in deciding whether an answer is right.

from practice import CHALLENGES, CHALLENGES_BY_ID, SKILLS, DIFFICULTIES, TRACKS, public_challenge, check_attempt, check_numeric, reveal_solution
from interview_questions import QUESTIONS, QUESTIONS_BY_ID
from qasm_input import qasm_to_gate_list


class PracticeCheckRequest(BaseModel):
    challenge_id: str
    gates: list[GateInstruction] = []
    # For calculation challenges instead of gates.
    value: float | None = None
    # An OpenQASM 2/3 program instead of gates (any circuit challenge).
    qasm: str | None = None


# Practice also allows the hardware track's native/routing gates.
PRACTICE_GATES = SUPPORTED_GATES + [
    {"name": "sx", "num_params": 0, "num_qubits": 1},
    {"name": "swap", "num_params": 0, "num_qubits": 2},
    {"name": "cp", "num_params": 1, "num_qubits": 2},
]


class QuestionAnswerRequest(BaseModel):
    question_id: str
    choice: int


@app.get("/practice/challenges")
def list_practice_challenges():
    return {
        "skills": SKILLS,
        "difficulties": DIFFICULTIES,
        "tracks": TRACKS,
        "challenges": [public_challenge(c) for c in CHALLENGES],
    }


@app.post("/practice/check")
def check_practice_answer(request: PracticeCheckRequest):
    challenge = CHALLENGES_BY_ID.get(request.challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Unknown challenge.")
    if challenge.get("kind") == "numeric":
        if request.value is None:
            raise HTTPException(status_code=400, detail="Enter a number.")
        return check_numeric(request.challenge_id, request.value)
    parsed_gates = None
    if request.qasm is not None:
        try:
            gate_list, program_qubits = qasm_to_gate_list(request.qasm)
        except CircuitInputError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if program_qubits > challenge["num_qubits"]:
            raise HTTPException(
                status_code=400,
                detail=f"This challenge uses {challenge['num_qubits']} qubit(s), but the program declares {program_qubits}.",
            )
        parsed_gates = [{"name": n, "qubits": list(q), "params": list(p)} for n, q, p in gate_list]
        request.gates = [GateInstruction(**g) for g in parsed_gates]

    gate_specs = {g["name"]: g for g in PRACTICE_GATES}
    for gate in request.gates:
        spec = gate_specs.get(gate.name)
        if spec is None:
            raise HTTPException(status_code=400, detail=f"Unsupported gate: {gate.name}")
        if len(gate.qubits) != spec["num_qubits"] or len(gate.params) != spec["num_params"]:
            raise HTTPException(status_code=400, detail=f"Wrong number of qubits or parameters for {gate.name.upper()}.")
        if len(set(gate.qubits)) != len(gate.qubits):
            raise HTTPException(status_code=400, detail=f"{gate.name.upper()} needs two different qubits.")
    attempt = [(g.name, tuple(g.qubits), tuple(g.params)) for g in request.gates]
    result = check_attempt(request.challenge_id, attempt)
    if parsed_gates is not None:
        # Lets the editor draw the circuit the program actually describes.
        result["parsed_gates"] = parsed_gates
    return result


@app.get("/practice/solution/{challenge_id}")
def practice_solution(challenge_id: str):
    if challenge_id not in CHALLENGES_BY_ID:
        raise HTTPException(status_code=404, detail="Unknown challenge.")
    return reveal_solution(challenge_id)


@app.get("/interview/questions")
def list_interview_questions():
    # Answers and explanations stay server-side until the user commits to a choice.
    return {
        "questions": [
            {k: v for k, v in q.items() if k not in ("answer", "explanation")}
            for q in QUESTIONS
        ]
    }


@app.post("/interview/answer")
def answer_interview_question(request: QuestionAnswerRequest):
    question = QUESTIONS_BY_ID.get(request.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Unknown question.")
    return {
        "correct": request.choice == question["answer"],
        "answer": question["answer"],
        "explanation": question["explanation"],
    }


# --- Study: exact output state for lesson example circuits ---
# Lessons never hard-code "this circuit produces X"; they ask Qiskit. No LLM.

@app.post("/state")
def circuit_state(circuit_request: CircuitRequest):
    if circuit_request.num_qubits > 5:
        raise HTTPException(status_code=400, detail="State readout is limited to 5 qubits.")
    qc = build_circuit_from_request(circuit_request)
    statevector = Statevector(qc)
    probabilities = statevector.probabilities_dict()
    return {
        "dirac": format_dirac_notation(qc),
        "probabilities": {
            basis: round(float(p), 6) for basis, p in sorted(probabilities.items()) if p > 1e-9
        },
    }


# --- Cross-module copilot ---
# Prompt assembly and link validation live in copilot.py (testable without an
# LLM). The model only explains and recommends; it never grades or computes.

import json as _json
import anthropic
from copilot import SYSTEM_PROMPT, ANSWER_SCHEMA, MODULES, build_messages, validate_links

COPILOT_MODEL = os.environ.get("COPILOT_MODEL", "claude-opus-5-5")
COPILOT_EFFORT = os.environ.get("COPILOT_EFFORT", "low")


class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotRequest(BaseModel):
    module: str
    message: str
    history: list[CopilotMessage] = []
    context: dict = {}


@app.post("/copilot")
def copilot(request: CopilotRequest):
    module = request.module if request.module in MODULES else "home"
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty.")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Message is too long (4,000 characters max).")

    messages = build_messages(module, message, [m.model_dump() for m in request.history], request.context)

    try:
        response = llm_client.beta.messages.create(
            model=COPILOT_MODEL,
            max_tokens=4000,
            # Stable system prompt first so it's cached across turns and users.
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config={
                "effort": COPILOT_EFFORT,
                "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
            },
            # If a safety classifier declines, retry on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="The copilot is busy right now. Try again in a minute.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"The AI service returned an error ({e.status_code}).")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=502, detail="Couldn't reach the AI service.")

    if response.stop_reason == "refusal":
        return {"answer": "I can't help with that one. Try rephrasing, or ask about something else on the site.", "links": [], "refused": True}
    if response.stop_reason == "max_tokens":
        return {"answer": "That answer ran too long and was cut off. Try asking a narrower question.", "links": [], "truncated": True}

    text = next((block.text for block in response.content if block.type == "text"), "")
    try:
        parsed = _json.loads(text)
    except ValueError:
        return {"answer": "Something went wrong formatting that answer. Please try again.", "links": []}

    return {
        "answer": parsed.get("answer", "").strip(),
        # Any id the model invented is dropped here, so it can never become a link.
        "links": validate_links(parsed.get("links"), request.context),
    }
