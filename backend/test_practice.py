"""
Regression tests for Interview Prep (practice.py, interview_questions.py and
their endpoints). No LLM calls, so this is free and fast to run:

    python test_practice.py
"""

import numpy as np
from fastapi.testclient import TestClient
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from main import app
from practice import CHALLENGES, CHALLENGES_BY_ID, check_attempt, reveal_solution, public_challenge
from interview_questions import QUESTIONS, QUESTIONS_BY_ID

client = TestClient(app)
results = []


def check(description, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {description}")
    results.append(bool(condition))


def gates(*items):
    return [(name, tuple(qubits), ()) for name, qubits in items]


# --- Every challenge is solvable, and its published solution passes ---------

for challenge in [c for c in CHALLENGES if c.get("kind") != "numeric"]:
    solution = [(g["name"], tuple(g["qubits"]), tuple(g["params"])) for g in reveal_solution(challenge["id"])["gates"]]
    check(f"{challenge['id']}: published solution passes", check_attempt(challenge["id"], solution)["passed"])
    check(f"{challenge['id']}: empty circuit fails", not check_attempt(challenge["id"], [])["passed"])
    public = public_challenge(challenge)
    check(
        f"{challenge['id']}: answer fields are not sent to the client",
        not {"reference", "solution", "setup", "teardown", "target_override", "explanation"} & set(public),
    )

# --- Wrong answers fail for the right reason ---------------------------------

def failed_labels(challenge_id, attempt):
    return [c["label"] for c in check_attempt(challenge_id, attempt)["checks"] if not c["passed"]]

check("Bell: two independent H's is not entangled",
      failed_labels("bell_phi_plus", gates(("h", [0]), ("h", [1]))) == ["Produces the target state (up to global phase)"])
check("Bell: right state but too many gates fails only the gate limit",
      failed_labels("bell_phi_plus", gates(("h", [0]), ("cx", [0, 1]), ("z", [0]), ("z", [0]))) == ["At most 2 gates"])
check("SWAP: using the SWAP gate itself is rejected by the gate-set rule",
      "Only uses CX" in failed_labels("swap_from_cx", gates(("swap", [0, 1]))))
check("SWAP: three same-direction CNOTs is not a SWAP",
      not check_attempt("swap_from_cx", gates(("cx", [0, 1]), ("cx", [0, 1]), ("cx", [0, 1])))["passed"])
check("GHZ-4: a CNOT chain is correct but too deep",
      failed_labels("ghz4_shallow", gates(("h", [0]), ("cx", [0, 1]), ("cx", [1, 2]), ("cx", [2, 3]))) == ["Depth at most 3"])
check("Superdense: gates on Bob's qubit are rejected",
      "Only touches qubit(s) 0" in failed_labels("superdense_11", gates(("x", [1]), ("z", [1]))))
check("|+i>: H, S, Z gives |-i>, not |+i>",
      not check_attempt("plus_i", gates(("h", [0]), ("s", [0]), ("z", [0])))["passed"])
check("Out-of-range qubit is reported, not crashed on",
      failed_labels("flip", gates(("x", [1]))) == ["Qubits in range"])

# --- Alternative correct answers are accepted --------------------------------

check("Bell on the other control qubit is accepted",
      check_attempt("bell_phi_plus", gates(("h", [1]), ("cx", [1, 0])))["passed"])
check("|->: H then Z is accepted as well as X then H",
      check_attempt("minus", gates(("h", [0]), ("z", [0])))["passed"])
check("Superdense: Z then X (differs only by global phase) is accepted",
      check_attempt("superdense_11", gates(("z", [0]), ("x", [0])))["passed"])
check("CZ via H on qubit 0 instead of 1 is accepted (CZ is symmetric)",
      check_attempt("cz_from_cx", gates(("h", [0]), ("cx", [1, 0]), ("h", [0])))["passed"])

# --- Results contain plain Python types (JSON-safe) --------------------------

sample = check_attempt("bell_phi_plus", gates(("h", [0]), ("h", [1])))
check("check_attempt returns plain bools, not numpy bools",
      type(sample["passed"]) is bool and all(type(c["passed"]) is bool for c in sample["checks"]))

# --- Endpoints ----------------------------------------------------------------

listing = client.get("/practice/challenges").json()
check("/practice/challenges lists every challenge", len(listing["challenges"]) == len(CHALLENGES))

response = client.post("/practice/check", json={
    "challenge_id": "bell_phi_plus",
    "gates": [{"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [0, 1]}],
})
check("/practice/check grades a correct Bell pair", response.status_code == 200 and response.json()["passed"])

response = client.post("/practice/check", json={"challenge_id": "bell_phi_plus", "gates": [{"name": "cx", "qubits": [0, 0]}]})
check("/practice/check rejects a CX with the same control and target", response.status_code == 400)

response = client.post("/practice/check", json={"challenge_id": "nope", "gates": []})
check("/practice/check returns 404 for an unknown challenge", response.status_code == 404)

questions = client.get("/interview/questions").json()["questions"]
check("/interview/questions hides answers", all("answer" not in q and "explanation" not in q for q in questions))

first = QUESTIONS[0]
answer = client.post("/interview/answer", json={"question_id": first["id"], "choice": first["answer"]}).json()
check("/interview/answer marks the right choice correct", answer["correct"] is True)

# --- /state (Study's live output readout) ----------------------------------------

state = client.post("/state", json={"num_qubits": 2, "gates": [{"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [0, 1]}]}).json()
check("/state computes the Bell state exactly", state["probabilities"] == {"00": 0.5, "11": 0.5})
check("/state refuses more than 5 qubits", client.post("/state", json={"num_qubits": 6, "gates": []}).status_code == 400)

# --- /jobs_search request building and dedupe (Adzuna mocked, no network) -------

import main as main_module


class FakeAdzunaResponse:
    def raise_for_status(self):
        pass

    def json(self):
        job = {"id": 1, "title": "Quantum Engineer", "company": {"display_name": "Acme"},
               "location": {"display_name": "Boston"}, "salary_min": 100000, "salary_max": 120000,
               "salary_is_predicted": "1", "redirect_url": "https://example.com", "created": "2026-10-01T00:00:00Z"}
        return {"count": 45, "results": [job, {**job, "id": 2}, {**job, "id": 3, "title": "Quantum Physicist", "salary_is_predicted": "0"}]}


captured = {}
real_get = main_module.requests.get
real_env = {k: main_module.os.environ.get(k) for k in ("ADZUNA_APP_ID", "ADZUNA_APP_KEY")}
main_module.os.environ["ADZUNA_APP_ID"] = main_module.os.environ.get("ADZUNA_APP_ID") or "test"
main_module.os.environ["ADZUNA_APP_KEY"] = main_module.os.environ.get("ADZUNA_APP_KEY") or "test"
main_module.requests.get = lambda url, params, timeout: captured.update(url=url, params=params) or FakeAdzunaResponse()
try:
    jobs = client.post("/jobs_search", json={"query": "software", "max_days_old": 7, "page": 2}).json()
finally:
    main_module.requests.get = real_get
    for k, v in real_env.items():
        if v is None:
            main_module.os.environ.pop(k, None)

check("/jobs_search filters to 'quantum' in the title by default", captured["params"].get("title_only") == "quantum")
check("/jobs_search passes keywords, age and page through", captured["params"].get("what") == "software" and captured["params"].get("max_days_old") == 7 and captured["url"].endswith("/2"))
check("/jobs_search drops duplicate listings of the same posting", [j["id"] for j in jobs["jobs"]] == ["1", "3"])
check("/jobs_search flags Adzuna-estimated salaries", jobs["jobs"][0]["salary_is_estimate"] is True and jobs["jobs"][1]["salary_is_estimate"] is False)
check("/jobs_search reports total pages", jobs["total_pages"] == 3)

# --- Real hardware track ------------------------------------------------------------

import math
from practice import check_numeric

def pgates(*items):
    return [(name, tuple(qubits), tuple(params)) for name, qubits, params in items]

check("HW: native H via RZ(π/2)·SX·RZ(π/2) passes",
      check_attempt("hw_native_h", pgates(("rz", [0], [math.pi / 2]), ("sx", [0], []), ("rz", [0], [math.pi / 2])))["passed"])
check("HW: using H itself is rejected by the native gate rule",
      "Only uses RZ, SX" in failed_labels("hw_native_h", gates(("h", [0]))))
check("HW: a wrong RZ angle fails equivalence",
      not check_attempt("hw_native_h", pgates(("rz", [0], [math.pi / 4]), ("sx", [0], []), ("rz", [0], [math.pi / 2])))["passed"])
check("HW: CX(0,2) on Line-3 is rejected as unconnected",
      any("connected qubits" in l for l in failed_labels("hw_route_cx", gates(("cx", [0, 2])))))
check("HW: SWAP routing that forgets to swap back fails equivalence",
      not check_attempt("hw_route_cx", gates(("swap", [0, 1]), ("cx", [1, 2])))["passed"])
check("HW: SWAP routing blows the 4 two-qubit-gate budget (SWAP = 3)",
      failed_labels("hw_cx_no_swap", gates(("swap", [0, 1]), ("cx", [1, 2]), ("swap", [0, 1]))) == ["At most 4 two-qubit gates (SWAP = 3)"])
chain5 = gates(("h", [0]), ("cx", [0, 1]), ("cx", [1, 2]), ("cx", [2, 3]), ("cx", [3, 4]))
chain_result = check_attempt("hw_ghz5_fidelity", chain5)
check("HW: GHZ-5 chain from the end is correct but below the fidelity bar",
      not chain_result["passed"] and chain_result["fidelity"] < 0.912 and [l for l in failed_labels("hw_ghz5_fidelity", chain5)] == ["Fidelity at least 0.912 under the chip's noise"])
check("HW: GHZ-5 grown from the middle clears the fidelity bar",
      check_attempt("hw_ghz5_fidelity", gates(("h", [2]), ("cx", [2, 1]), ("cx", [2, 3]), ("cx", [1, 0]), ("cx", [3, 4])))["passed"])
check("HW: GHZ-3 with an unconnected CX isn't simulated for fidelity",
      check_attempt("hw_ghz3_line", gates(("h", [0]), ("cx", [0, 1]), ("cx", [0, 2])))["fidelity"] is None)
check("HW: calculation answers are graded against computed values",
      check_numeric("hw_readout_mitigation", 0.294)["passed"] and not check_numeric("hw_readout_mitigation", 0.30)["passed"])
check("HW: numeric challenges don't leak their solver or answer",
      all("numeric" not in public_challenge(c) and "tolerance" not in public_challenge(c) for c in CHALLENGES))
response = client.post("/practice/check", json={"challenge_id": "hw_zne", "value": 0.88})
check("/practice/check grades a calculation answer", response.status_code == 200 and response.json()["passed"])
response = client.post("/practice/check", json={"challenge_id": "hw_route_cx", "gates": [{"name": "swap", "qubits": [0, 1]}, {"name": "cx", "qubits": [1, 2]}, {"name": "swap", "qubits": [0, 1]}]})
check("/practice/check accepts SWAP for routing challenges", response.status_code == 200 and response.json()["passed"])

# --- Copilot trust boundary (copilot.py; no LLM call) ------------------------------

from copilot import build_messages, build_user_data, validate_links

copilot_context = {
    "signed_in": True,
    "profile": {"display_name": "Milo", "experience_level": "some", "goal": "interview"},
    "lesson_catalog": [{"id": "bell-states", "title": "Bell states", "track": "Entanglement"}],
    "progress": {"lessons_completed": ["bell-states", "not-a-lesson"], "challenges_solved": ["bell_phi_plus"],
                 "challenges_attempted": ["bell_phi_plus", "ghz3"]},
    "saved_jobs": [{"job_id": "123", "title": "Quantum Software Intern", "company": "IBM", "status": "applied", "description": "x" * 5000}],
    "page": {"kind": "challenge", "challenge_id": "ghz3", "gates": [{"name": "h", "qubits": [0]}],
             "last_check": {"passed": False, "checks": [{"label": "Produces the target state", "passed": False}], "your_state": "0.7071|000⟩ + 0.7071|001⟩"}},
}
links = validate_links([
    {"kind": "lesson", "id": "bell-states"},
    {"kind": "lesson", "id": "made-up-lesson"},
    {"kind": "challenge", "id": "ghz3"},
    {"kind": "challenge", "id": "teleport_everything"},
    {"kind": "quiz_topic", "id": "Hardware"},
    {"kind": "saved_job", "id": "999"},
    {"kind": "lesson", "id": "bell-states"},
], copilot_context)
check("Copilot links: invented lesson/challenge/job ids are dropped, duplicates removed",
      [(l["kind"], l["id"]) for l in links] == [("lesson", "bell-states"), ("challenge", "ghz3"), ("quiz_topic", "Hardware")])
check("Copilot links: each link gets a real route", links[1]["path"] == "/interview/challenge/ghz3")

user_data = build_user_data(copilot_context)
check("Copilot data: unknown lesson ids aren't counted as progress", user_data["progress"]["completed_lesson_titles"] == ["Bell states"])
check("Copilot data: attempted-but-unsolved is derived, not asserted", user_data["progress"]["attempted_but_unsolved"] == ["Three-way entanglement"])
check("Copilot data: grader result is passed through for the current challenge",
      user_data["current_page"]["last_check_result_from_grader"]["passed"] is False)
check("Copilot data: long job descriptions are truncated", len(user_data["saved_jobs"][0]["description_snippet"]) <= 600)

turns = build_messages("interview", "hint?", [{"role": "assistant", "content": "orphan"}, {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}], copilot_context)
check("Copilot messages: history starts with a user turn and ends with this turn",
      turns[0] == {"role": "user", "content": "hi"} and turns[-1]["role"] == "user" and turns[-1]["content"].endswith("hint?"))

response = client.post("/copilot", json={"module": "study", "message": "   "})
check("/copilot rejects an empty message without calling the AI", response.status_code == 400)

# --- Advanced track ----------------------------------------------------------------------

from qiskit.circuit.library import QFTGate
qft_ref = QuantumCircuit(2)
qft_ref.append(QFTGate(2), [0, 1])
qft_ours = QuantumCircuit(2)
qft_ours.h(1)
qft_ours.cp(math.pi / 2, 0, 1)
qft_ours.h(0)
qft_ours.swap(0, 1)
check("ADV: the QFT reference matches Qiskit's QFTGate", Operator(qft_ours).equiv(Operator(qft_ref)))
check("ADV: QFT without the final SWAP is rejected",
      not check_attempt("adv_qft2", pgates(("h", [1], []), ("cp", [0, 1], [math.pi / 2]), ("h", [0], [])))["passed"])
syndrome_cheat = gates(("cx", [0, 3]), ("cx", [0, 4]))
check("ADV: copying one data qubit to both ancillas doesn't count as a syndrome",
      not check_attempt("adv_bitflip_syndrome", syndrome_cheat)["passed"])
check("ADV: parity checks in a different order still pass",
      check_attempt("adv_bitflip_syndrome", gates(("cx", [1, 3]), ("cx", [0, 3]), ("cx", [2, 4]), ("cx", [1, 4])))["passed"])
check("ADV: QPE may only touch the eigenstate qubit with CP",
      any("qubit rules" in l for l in failed_labels("adv_qpe_s", gates(("swap", [0, 2])))))
check("ADV: a Grover oracle without diffusion is rejected",
      not check_attempt("adv_grover2", gates(("cz", [0, 1])))["passed"])
check("ADV: RZZ with the wrong rotation sign is rejected",
      not check_attempt("adv_rzz", pgates(("cx", [0, 1], []), ("rz", [1], [-math.pi / 2]), ("cx", [0, 1], [])))["passed"])
response = client.post("/practice/check", json={"challenge_id": "adv_qft2", "gates": [
    {"name": "h", "qubits": [1]}, {"name": "cp", "qubits": [0, 1], "params": [math.pi / 2]},
    {"name": "h", "qubits": [0]}, {"name": "swap", "qubits": [0, 1]}]})
check("/practice/check accepts CP gates with an angle", response.status_code == 200 and response.json()["passed"])

# --- OpenQASM answers -----------------------------------------------------------------

QH = 'OPENQASM 3.0;\ninclude "stdgates.inc";\n'

def qasm_check(challenge_id, program):
    return client.post("/practice/check", json={"challenge_id": challenge_id, "qasm": program})

r = qasm_check("bell_phi_plus", QH + "qubit[2] q;\nh q[0];\ncx q[0], q[1];\n")
check("QASM: a builder challenge can be answered in OpenQASM 3", r.status_code == 200 and r.json()["passed"])
check("QASM: the response includes the parsed gates for drawing", r.json()["parsed_gates"] == [{"name": "h", "qubits": [0], "params": []}, {"name": "cx", "qubits": [0, 1], "params": []}])
r = qasm_check("bell_phi_plus", 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n')
check("QASM: OpenQASM 2 is accepted too", r.status_code == 200 and r.json()["passed"])
r = qasm_check("bell_phi_plus", QH + "gate bell a, b { h a; cx a, b; }\nqubit[2] q;\nbell q[0], q[1];\n")
check("QASM: user-defined gates are expanded before grading", r.status_code == 200 and r.json()["passed"])
r = qasm_check("bell_phi_plus", QH + "qubit[2] q;\nbit[2] c;\nh q[0];\ncx q[0], q[1];\nc = measure q;\n")
check("QASM: final measurements are ignored", r.status_code == 200 and r.json()["passed"])
r = qasm_check("bell_phi_plus", QH + "qubit[2] q;\nbit[1] c;\nh q[0];\nc[0] = measure q[0];\ncx q[0], q[1];\n")
check("QASM: gates after a measurement are rejected with a message", r.status_code == 400 and "after a measurement" in r.json()["detail"])
r = qasm_check("bell_phi_plus", QH + "qubit[2] q;\nh q[0]\ncx q[0], q[1];\n")
check("QASM: a syntax error returns a 400 with a hint", r.status_code == 400 and "semicolon" in r.json()["detail"])
r = qasm_check("bell_phi_plus", QH + "qubit[3] q;\nh q[0];\n")
check("QASM: declaring more qubits than the challenge has is rejected", r.status_code == 400)
r = qasm_check("bell_phi_plus", "h q[0];")
check("QASM: a missing version line is explained", r.status_code == 400 and "OPENQASM" in r.json()["detail"])
check("QASM: the Fix-the-Bell starter program fails as written",
      not qasm_check("code_fix_bell", CHALLENGES_BY_ID["code_fix_bell"]["starter"]).json()["passed"])
check("QASM: the fixed program passes",
      qasm_check("code_fix_bell", CHALLENGES_BY_ID["code_fix_bell"]["starter"].replace("cx q[1], q[0];", "cx q[0], q[1];")).json()["passed"])
check("QASM: the wrong-angle starter fails and the corrected angle passes",
      not qasm_check("code_native_angle", CHALLENGES_BY_ID["code_native_angle"]["starter"]).json()["passed"]
      and qasm_check("code_native_angle", CHALLENGES_BY_ID["code_native_angle"]["starter"].replace("rz(pi/4)", "rz(pi/2)")).json()["passed"])
check("QASM: the QFT written as code passes",
      qasm_check("code_qft2", QH + "qubit[2] q;\nh q[1];\ncp(pi/2) q[0], q[1];\nh q[0];\nswap q[0], q[1];\n").json()["passed"])
check("QASM: every code challenge ships a starter program",
      all(c.get("starter") for c in CHALLENGES if c.get("track") == "code"))

# --- Code-reading answer keys: run the code and compare ---------------------------------

from qiskit import qasm3 as _qasm3
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.primitives import StatevectorSampler, StatevectorEstimator
from qiskit_aer import AerSimulator

def answer_text(qid):
    q = QUESTIONS_BY_ID[qid]
    return q["choices"][q["answer"]]

bell_prog = _qasm3.loads(QUESTIONS_BY_ID["code_bell_counts"]["code"])
bell_counts = StatevectorSampler().run([bell_prog], shots=1000).result()[0].data.c.get_counts()
check("Code key: Bell program gives only 00 and 11", set(bell_counts) == {"00", "11"} and "00 and 11" in answer_text("code_bell_counts"))

order = QuantumCircuit(2)
order.x(0)
order.measure_all()
order_counts = StatevectorSampler().run([order], shots=10).result()[0].data.meas.get_counts()
check("Code key: flipping qubit 0 shows up as '01'", list(order_counts) == ["01"] and answer_text("code_bit_order") == "'01'")

minus = QuantumCircuit(1)
minus.x(0)
minus.h(0)
check("Code key: X then H is |−⟩", Statevector(minus).equiv(Statevector([1, -1]) / np.sqrt(2)) and answer_text("code_minus_state") == "|−⟩")

swapped = _qasm3.loads(QUESTIONS_BY_ID["code_swap_label"]["code"])
check("Code key: X then SWAP leaves |10⟩", Statevector(swapped).probabilities_dict() == {"10": 1.0} and answer_text("code_swap_label") == "|10⟩")

bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
zi = StatevectorEstimator().run([(bell, SparsePauliOp("ZI"))]).result()[0].data.evs
check("Code key: <ZI> on a Bell state is 0", abs(float(zi)) < 1e-9 and answer_text("code_estimator_zi") == "0")

rz_prog = _qasm3.loads(QUESTIONS_BY_ID["code_rz_pi"]["code"])
z_gate = QuantumCircuit(1)
z_gate.z(0)
check("Code key: RZ(π) equals Z up to phase", Operator(rz_prog).equiv(Operator(z_gate)) and answer_text("code_rz_pi") == "Z")

reset_prog = QuantumCircuit(1, 1)
reset_prog.h(0)
reset_prog.measure(0, 0)
with reset_prog.if_test((reset_prog.clbits[0], 1)):
    reset_prog.x(0)
reset_prog.measure(0, 0)
reset_counts = AerSimulator().run(reset_prog, shots=200, seed_simulator=7).result().get_counts()
check("Code key: measure-and-flip always ends in |0>", set(reset_counts) == {"0"} and answer_text("code_dynamic_reset") == "|0⟩")

# --- Mock interviews (no AI calls) ---------------------------------------------------

from interview_prompts import EXPLAIN_PROMPTS, DESIGN_PROMPTS

mock = client.get("/interview/mock?path=software").json()
check("Mock: three concept questions without answers", len(mock["questions"]) == 3 and all("answer" not in q for q in mock["questions"]))
check("Mock: questions match the path's topics", all(q["topic"] in ("Gates", "Code reading", "Advanced") for q in mock["questions"]))
check("Mock: the code round has a starter program", mock["code_challenge"]["starter"].startswith("OPENQASM"))
check("Mock: open prompts don't reveal their rubric", "rubric" not in mock["explain"] and "rubric" not in mock["design"])
check("Mock: an unknown path still builds a session", client.get("/interview/mock?path=nonsense").status_code == 200)
short = client.post("/interview/rubric_feedback", json={"prompt_id": EXPLAIN_PROMPTS[0]["id"], "answer": "Because noise."}).json()
check("Mock: a too-short answer is declined without an AI call", short["assessed"] is False and len(short["rubric"]) == 4)
check("Mock: every rubric has unique criterion ids",
      all(len({c["id"] for c in p["rubric"]}) == len(p["rubric"]) for p in EXPLAIN_PROMPTS + DESIGN_PROMPTS))
check("Mock: every path has at least one explain and one design prompt",
      all(any(path in p["paths"] for p in EXPLAIN_PROMPTS) and any(path in p["paths"] for p in DESIGN_PROMPTS) for path in ("software", "hardware", "research", "business")))
check("Mock: every mock code challenge exists and is a circuit task",
      all(cid in CHALLENGES_BY_ID and CHALLENGES_BY_ID[cid].get("kind") != "numeric" for cid in sum(main_module.MOCK_CODE_CHALLENGES.values(), [])))

# --- Portfolio re-verification ---------------------------------------------------------

v = client.post("/practice/verify", json={"items": [
    {"challenge_id": "bell_phi_plus", "gates": [{"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [0, 1]}]},
    {"challenge_id": "bell_phi_plus", "gates": [{"name": "h", "qubits": [0]}]},
    {"challenge_id": "bell_phi_plus", "gates": []},
    {"challenge_id": "hw_zne", "gates": [{"name": "h", "qubits": [0]}]},
    {"challenge_id": "nope", "gates": [{"name": "h", "qubits": [0]}]},
    {"challenge_id": "bell_phi_plus", "gates": [{"name": "draw", "qubits": [0]}]},
]}).json()["results"]
check("Verify: a genuine solution verifies", v[0]["verified"] is True)
check("Verify: a fake 'passed' row with a wrong circuit doesn't", v[1]["verified"] is False)
check("Verify: rows without a circuit, calculations, unknown ids and junk gates don't verify",
      [r["verified"] for r in v[2:]] == [False, False, False, False])
check("Verify: batches are capped", client.post("/practice/verify", json={"items": [{"challenge_id": "plus"}] * 101}).status_code == 400)

# --- Rate limits ------------------------------------------------------------------------

import rate_limit
rate_limit.reset_for_tests()
statuses = [client.post("/copilot", json={"module": "study", "message": " "}).status_code for _ in range(rate_limit.PER_IP_BURST + 1)]
check("Rate limit: AI endpoints allow a burst, then return 429", statuses[:-1].count(400) == rate_limit.PER_IP_BURST and statuses[-1] == 429)
check("Rate limit: the 429 explains itself", "wait" in client.post("/copilot", json={"module": "study", "message": " "}).json()["detail"])
check("Rate limit: non-AI endpoints aren't limited", client.post("/state", json={"num_qubits": 1, "gates": []}).status_code == 200)
rate_limit.reset_for_tests()

# --- Input safety (circuit_safety.py) --------------------------------------------------

bad_requests = {
    "a non-gate QuantumCircuit method": {"num_qubits": 2, "gates": [{"name": "draw", "qubits": [0], "params": []}]},
    "a dunder name": {"num_qubits": 1, "gates": [{"name": "__class__", "qubits": [0]}]},
    "too many qubits": {"num_qubits": 40, "gates": []},
    "zero qubits": {"num_qubits": 0, "gates": []},
    "a qubit out of range": {"num_qubits": 2, "gates": [{"name": "h", "qubits": [5]}]},
    "a wrong parameter count": {"num_qubits": 1, "gates": [{"name": "rz", "qubits": [0], "params": []}]},
    "too many gates": {"num_qubits": 1, "gates": [{"name": "x", "qubits": [0]}] * 201},
}
for label, body in bad_requests.items():
    check(f"/simulate rejects {label} with a 400", client.post("/simulate", json=body).status_code == 400)
check("/simulate still accepts a normal circuit",
      client.post("/simulate", json={"num_qubits": 2, "gates": [{"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [0, 1]}]}).status_code == 200)

# --- Question bank sanity --------------------------------------------------------

check("Every question's answer index is valid", all(0 <= q["answer"] < len(q["choices"]) for q in QUESTIONS))
check("Question ids are unique", len({q["id"] for q in QUESTIONS}) == len(QUESTIONS))

# Facts in the answer key that can be checked numerically.
X = np.array([[0, 1], [1, 0]])
Y = np.array([[0, -1j], [1j, 0]])
Z = np.array([[1, 0], [0, -1]])
check("Answer key: XZ = -ZX", np.allclose(X @ Z, -(Z @ X)))
check("Answer key: XZ = -iY", np.allclose(X @ Z, -1j * Y))

T = np.diag([1, np.exp(1j * np.pi / 4)])
check("Answer key: T^2 = S", np.allclose(T @ T, np.diag([1, 1j])))

flipped = QuantumCircuit(2)
flipped.h([0, 1])
flipped.cx(0, 1)
flipped.h([0, 1])
reversed_cx = QuantumCircuit(2)
reversed_cx.cx(1, 0)
check("Answer key: H⊗H · CX(0→1) · H⊗H = CX(1→0)", Operator(flipped).equiv(Operator(reversed_cx)))

print(f"\n{sum(results)} / {len(results)} tests passed.")
if not all(results):
    raise SystemExit(1)
