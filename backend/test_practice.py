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

for challenge in CHALLENGES:
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
