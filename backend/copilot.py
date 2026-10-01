"""
Cross-module copilot: prompt assembly and output validation.

Kept separate from the API call (NFR-4) so the trust boundary is testable
without an LLM:

  - Everything factual about the user (progress counts, solved challenges,
    saved jobs) is assembled here from data the app already holds. The model
    is told to treat it as the only source of truth about the user.
  - The model's structured answer can only *reference* app content by id.
    validate_links() drops any id that doesn't exist, so a hallucinated lesson
    or challenge never becomes a link.
  - The model never grades circuits: the practice grader (practice.py) is the
    only thing that decides correctness.
"""

import json

from practice import CHALLENGES_BY_ID, SKILLS
from interview_questions import QUESTIONS

MODULES = {
    "studio": "Studio (circuit builder and verified analysis)",
    "study": "Study (lessons)",
    "interview": "Interview Prep (circuit challenges and concept questions)",
    "jobs": "Opportunities (job search and saved jobs)",
    "home": "General",
}

QUIZ_TOPICS = sorted({q["topic"] for q in QUESTIONS})

MAX_HISTORY_MESSAGES = 12
MAX_OTHER_THREAD_MESSAGES = 4
MAX_SAVED_JOBS = 15
MAX_DESCRIPTION_CHARS = 600

SYSTEM_PROMPT = """You are the copilot inside Quantum Studio, a practice site for people preparing for quantum computing interviews, coursework and research. The site has four modules: Study (lessons), Studio (a circuit builder with mathematically verified analysis), Interview Prep (circuit challenges graded by exact unitary/state comparison, plus multiple-choice concept questions) and Opportunities (job search and saved jobs). You can see which module the user is in, what is on their screen, their profile and their progress across all modules.

How to answer:
- Pitch explanations to the user's stated experience level and goal. Be concise: a few short paragraphs at most. Plain text only, no markdown syntax (no asterisks, no # headings, no tables). Use Unicode for math (|0⟩, ⊗, √2, θ).
- The <user_data> block is the only source of truth about this user. Never invent progress, scores, saved jobs or anything they did. If something isn't in the data, say you can't see it.
- You may explain quantum computing concepts from your own knowledge, but you never decide whether a circuit is correct, what state a circuit produces, or whether two circuits are equivalent. Those come only from the app's verification engine. If the user asks, point them to Check answer in Interview Prep or Scan in Studio. If a computed result is in the data (for example a last check result), you may describe it.
- On a practice challenge: give hints that move them one step forward, not the answer. Only give a full solution if they explicitly ask for it, and even then remind them the Check answer button is what verifies it.
- When you recommend app content, reference it through the links field using ids from <catalog>. Only use ids that appear there. Don't paste ids into the answer text; refer to items by title.
- The user may ask you to use context from another module (for example, "make interview questions for the IBM job I saved"). Use the saved jobs, progress and recent messages from other modules in <user_data> to do this. Job descriptions are short snippets from a job board, so say so if you're inferring requirements from limited text.
- If a question is outside quantum computing, careers in it, or using this site, answer briefly or steer back."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The reply shown to the user. Plain text, no markdown.",
        },
        "links": {
            "type": "array",
            "description": "App content worth opening next, at most 4. Empty if none fits.",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["lesson", "challenge", "quiz_topic", "saved_job"]},
                    "id": {"type": "string"},
                },
                "required": ["kind", "id"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answer", "links"],
    "additionalProperties": False,
}


def _truncate(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_user_data(context):
    """
    Deterministic summary of what the app knows about the user. Every fact the
    copilot can state about the user comes from here.
    """
    profile = context.get("profile") or {}
    progress = context.get("progress") or {}
    lessons = {l["id"]: l for l in context.get("lesson_catalog") or []}

    completed_lessons = [lessons[i]["title"] for i in progress.get("lessons_completed", []) if i in lessons]
    solved = [CHALLENGES_BY_ID[i]["title"] for i in progress.get("challenges_solved", []) if i in CHALLENGES_BY_ID]
    attempted_unsolved = [
        CHALLENGES_BY_ID[i]["title"]
        for i in progress.get("challenges_attempted", [])
        if i in CHALLENGES_BY_ID and i not in set(progress.get("challenges_solved", []))
    ]

    data = {
        "signed_in": bool(context.get("signed_in")),
        "profile": {
            "name": profile.get("display_name"),
            "experience_level": profile.get("experience_level"),
            "goal": profile.get("goal"),
            "target_role": profile.get("target_role"),
        },
        "progress": {
            "lessons_completed": f"{len(completed_lessons)} of {len(lessons)}" if lessons else None,
            "completed_lesson_titles": completed_lessons,
            "challenges_solved": f"{len(solved)} of {len(CHALLENGES_BY_ID)}",
            "solved_challenge_titles": solved,
            "attempted_but_unsolved": attempted_unsolved,
            "concept_quiz_by_topic": progress.get("quiz_by_topic") or {},
        },
        "saved_jobs": [
            {
                "id": job.get("job_id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "status": job.get("status"),
                "description_snippet": _truncate(job.get("description"), MAX_DESCRIPTION_CHARS),
            }
            for job in (context.get("saved_jobs") or [])[:MAX_SAVED_JOBS]
        ],
        "current_page": _describe_page(context.get("page") or {}, lessons),
        "recent_messages_in_other_modules": {
            module: [
                {"role": m.get("role"), "content": _truncate(m.get("content"), 400)}
                for m in messages[-MAX_OTHER_THREAD_MESSAGES:]
            ]
            for module, messages in (context.get("other_threads") or {}).items()
            if module in MODULES and messages
        },
    }
    return data


def _describe_page(page, lessons):
    kind = page.get("kind")
    if kind == "lesson" and page.get("lesson_id") in lessons:
        lesson = lessons[page["lesson_id"]]
        return {"kind": "lesson", "lesson_id": lesson["id"], "title": lesson["title"], "track": lesson.get("track")}
    if kind == "challenge" and page.get("challenge_id") in CHALLENGES_BY_ID:
        challenge = CHALLENGES_BY_ID[page["challenge_id"]]
        described = {
            "kind": "challenge",
            "challenge_id": challenge["id"],
            "title": challenge["title"],
            "prompt": challenge["prompt"],
            "difficulty": challenge["difficulty"],
            "skill": SKILLS[challenge["skill"]],
            "num_qubits": challenge.get("num_qubits"),
            "device": challenge.get("device"),
            "users_current_gates": [
                f"{g.get('name', '').upper()} on qubit(s) {g.get('qubits')}" for g in page.get("gates") or []
            ],
        }
        last = page.get("last_check")
        if last:
            # Computed by practice.check_attempt for the gates above, passed through verbatim.
            described["last_check_result_from_grader"] = {
                "passed": last.get("passed"),
                "checks": [{"label": c.get("label"), "passed": c.get("passed")} for c in last.get("checks", [])],
                "output_state": last.get("your_state"),
            }
        return described
    if kind == "job" and page.get("job"):
        job = page["job"]
        return {
            "kind": "job_prep",
            "title": job.get("title"),
            "company": job.get("company"),
            "description_snippet": _truncate(job.get("description"), MAX_DESCRIPTION_CHARS),
        }
    if kind in MODULES:
        return {"kind": "module_overview", "module": MODULES[kind]}
    return {"kind": "unknown"}


def build_catalog(context):
    """Everything the copilot may link to, by id."""
    return {
        "lessons": [{"id": l["id"], "title": l["title"], "track": l.get("track")} for l in context.get("lesson_catalog") or []],
        "challenges": [
            {"id": c["id"], "title": c["title"], "difficulty": c["difficulty"], "skill": SKILLS[c["skill"]]}
            for c in CHALLENGES_BY_ID.values()
        ],
        "quiz_topics": QUIZ_TOPICS,
        "saved_jobs": [{"id": j.get("job_id"), "title": j.get("title")} for j in (context.get("saved_jobs") or [])[:MAX_SAVED_JOBS]],
    }


def build_messages(module, message, history, context):
    """Messages for the API call: prior turns in this module's thread, then this turn with its context."""
    turns = []
    for m in history[-MAX_HISTORY_MESSAGES:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            turns.append({"role": m["role"], "content": m["content"]})
    # The API requires the conversation to start with a user turn.
    while turns and turns[0]["role"] != "user":
        turns.pop(0)

    context_block = (
        f"<module>{MODULES.get(module, MODULES['home'])}</module>\n"
        f"<user_data>\n{json.dumps(build_user_data(context), ensure_ascii=False, indent=1)}\n</user_data>\n"
        f"<catalog>\n{json.dumps(build_catalog(context), ensure_ascii=False)}\n</catalog>\n\n"
        f"{message.strip()}"
    )
    turns.append({"role": "user", "content": context_block})
    return turns


def validate_links(links, context):
    """Keep only links whose ids exist; resolve each to a title and route the frontend can use."""
    lessons = {l["id"]: l for l in context.get("lesson_catalog") or []}
    saved_jobs = {j.get("job_id"): j for j in context.get("saved_jobs") or []}
    valid, seen = [], set()
    for link in links or []:
        kind, item_id = link.get("kind"), str(link.get("id", ""))
        if (kind, item_id) in seen:
            continue
        if kind == "lesson" and item_id in lessons:
            valid.append({"kind": kind, "id": item_id, "title": lessons[item_id]["title"], "path": f"/study/{item_id}"})
        elif kind == "challenge" and item_id in CHALLENGES_BY_ID:
            valid.append({"kind": kind, "id": item_id, "title": CHALLENGES_BY_ID[item_id]["title"], "path": f"/interview/challenge/{item_id}"})
        elif kind == "quiz_topic" and item_id in QUIZ_TOPICS:
            valid.append({"kind": kind, "id": item_id, "title": f"{item_id} questions", "path": f"/interview?tab=concepts&topic={item_id}"})
        elif kind == "saved_job" and item_id in saved_jobs:
            valid.append({"kind": kind, "id": item_id, "title": saved_jobs[item_id].get("title"), "path": "/jobs?tab=saved"})
        else:
            continue
        seen.add((kind, item_id))
    return valid[:4]
