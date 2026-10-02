# Quantum Tunnel

**Practice quantum computing the way you'll be tested.** Build circuits from memory, get graded by exact math, and walk into quantum computing interviews knowing your weak spots.

Quantum Tunnel is to quantum circuits what coding-practice platforms are to algorithms: a hands-on loop with instant, *verified* feedback. Every grade comes from exact unitary or statevector comparison in Qiskit. An AI layer explains and coaches on top of that, but never decides whether something is correct.

**Live site:** [quantum-tunnel-sok7.vercel.app](https://quantum-tunnel-sok7.vercel.app)

## What's in it

| Module | What it does |
|---|---|
| **Studio** | Build circuits, then scan them: rule-based simplifications (gate cancellation, commutation, power identities), motif recognition and target matching, each verified by unitary equivalence before it's shown. Natural-language circuit generation with schema-validated output. |
| **Study** | 30 lessons from qubits to the surface code and the Qiskit stack. Example circuits are live: their output state is computed by Qiskit, never typed into the lesson. |
| **Interview Prep** | 35 graded circuit challenges across four tracks (fundamentals, simulated noisy hardware, advanced algorithms and QEC, OpenQASM debugging), 37 concept questions, and 25-minute mock interviews with a scorecard. |
| **Opportunities** | Live quantum job search (Adzuna) with saved-job tracking and a per-job prep plan built from transparent keyword rules. |
| **Copilot** | One assistant across all modules, with a thread per module, aware of the user's progress, career path and current page. |
| **Portfolio** | Verified solutions exported as a runnable Jupyter notebook, or published as a public page that re-verifies every circuit on view. |

## Design principle: verify, then show

The core rule (from the [requirements doc](backend/quantum_studio_requirements.md)): **the system never presents an unverified claim**.

- **Grading is deterministic.** Challenges are checked by exact operator equivalence up to global phase, exact statevector comparison, or, for the hardware track, density-matrix simulation of a noise model with gate, readout and idle errors. Calculation tasks are graded against answers computed from the question's parameters.
- **The AI narrates, it doesn't decide.** Copilot answers are structured outputs; any lesson or challenge they reference is validated against the real catalog, and invented IDs are dropped. Studio explanations pass a second, independent consistency check before display. Mock-interview feedback marks fixed, pre-written rubric criteria, and the score is counted in code.
- **Nothing is trusted that a browser can forge.** Progress rows are written client-side, so the public portfolio re-runs each saved circuit through the grader on every view.
- **Every hard-coded fact is tested.** Lesson captions were checked against Qiskit, Qiskit snippets were executed, code-reading answer keys are verified by running the code, and noise thresholds are tested from both sides (a well-routed circuit passes, a naive one fails).

## Stack

- **Backend:** Python, FastAPI, Qiskit 2.x, Qiskit Aer, the Anthropic API ([`backend/`](backend))
- **Frontend:** React 19, Vite, React Router, KaTeX ([`frontend/`](frontend))
- **Accounts and data:** Supabase (Postgres with row-level security), see [`supabase/`](supabase)
- **Hosting:** Render (API) and Vercel (frontend)

## Running it locally

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your ANTHROPIC_API_KEY (Adzuna keys optional)
uvicorn main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
cp .env.example .env.local      # Supabase keys optional: without them it runs in guest mode
npm run dev                     # http://localhost:5173
```

To set up accounts, create a Supabase project and run [`supabase/schema.sql`](supabase/schema.sql) in its SQL editor.

## Tests

```bash
cd backend && python test_practice.py      # 199 checks, no AI calls
cd frontend && npm run check:lessons       # formulas, answer keys, links between modules
```

`backend/test_all.py` covers the Studio engine and AI layer end to end (it makes real API calls).

## Scope and limits

Exact verification scales as 2ⁿ × 2ⁿ, so circuits are capped at 10 qubits by design. Motif recognition is exact-unitary only (local-unitary equivalence is a stated future goal). Simulated hardware is illustrative of current superconducting devices, not a model of any vendor's machine. AI-generated text is always labelled as such.
