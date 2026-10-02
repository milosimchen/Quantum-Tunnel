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
from practice import CHALLENGES, check_attempt, reveal_solution, public_challenge
from interview_questions import QUESTIONS

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
