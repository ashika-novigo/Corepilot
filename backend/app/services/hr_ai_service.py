import json
import re
from datetime import date
from ai.groq_client import get_llm


def _clean_json(raw: str) -> str:
    """Strip markdown fences and extract first JSON object from a string."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def extract_hr_action(message: str, history: list = None):
    """
    Use the LLM to extract intent and entities from the user message.

    history — list of {"role": "user"|"assistant", "content": "..."} dicts
              representing the current session.

    Returns:
        dict with keys:
            action, leave_type, start_date, end_date, leave_id,
            reason, needs_confirmation, confirmation_message, missing_info
    """
    llm = get_llm()
    today = date.today().isoformat()

    # Summarise conversation history for the prompt (last 10 turns)
    history_text = "(no prior turns)"
    if history:
        turns = []
        for turn in history[-10:]:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")
            turns.append(f"{role}: {content}")
        history_text = "\n".join(turns)

    prompt = f"""
You are an HR operations intent and entity extraction agent.

Today's date is {today}.

--- CONVERSATION HISTORY (oldest first, most recent last) ---
{history_text}
--- END HISTORY ---

Current user message: {message}

Your job:
- Understand the user's HR request, resolving any follow-up answers using history.
  Example: if the assistant previously asked "What type of leave?" and the user now
  says "sick", the action is apply_leave with leave_type=sick.
- Convert relative dates to exact YYYY-MM-DD. Rules:
    "tomorrow"                     → one day after {today}
    "day after tomorrow"           → two days after {today}
    "next monday"                  → next upcoming Monday from {today}
    "for 3 days starting tomorrow" → start=tomorrow, end=3 calendar days later (inclusive)
    Natural spelling mistakes are fine: "sik leave tomorow" = sick leave tomorrow.

Supported actions:
  apply_leave, leave_balance, leave_history, pending_leaves,
  pending_approvals, approve_leave, reject_leave, cancel_leave,
  leave_status, policy_question

Return ONLY a single valid JSON object — no markdown fences, no prose.

Schema:
{{
  "action": "<action>",
  "leave_type": "casual | sick | earned | other | null",
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null",
  "leave_id": <integer or null>,
  "reason": "<string or null>",
  "needs_confirmation": <true|false>,
  "confirmation_message": "<string or null>",
  "missing_info": ["fields still needed, e.g. start_date, leave_type, reason"]
}}

Rules:
- apply_leave: extract leave_type, start_date, end_date, reason.
  * Set missing fields to null and list them in missing_info.
  * needs_confirmation = false (the agent layer handles the confirmation step).
- Questions asking which leave type to use are policy_question, not apply_leave.
  Example: "I am not feeling well, what leave should I put?" = policy_question.
- approve_leave / reject_leave: always set needs_confirmation = true.
- Single-day leave: start_date == end_date.
- Unclear or non-HR intent: action = "policy_question", missing_info = [].
- Output NOTHING outside the JSON object.
"""

    last_error = None
    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            raw = response.content
            cleaned = _clean_json(raw)
            data = json.loads(cleaned)

            return {
                "action": data.get("action", "policy_question"),
                "leave_type": data.get("leave_type") or "casual",
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "leave_id": data.get("leave_id"),
                "reason": data.get("reason"),
                "needs_confirmation": bool(data.get("needs_confirmation", False)),
                "confirmation_message": data.get("confirmation_message"),
                "missing_info": data.get("missing_info") or [],
            }

        except Exception as e:
            last_error = e
            print(f"[hr_ai_service] Extraction attempt {attempt + 1} failed: {e}")

    print(f"[hr_ai_service] All attempts failed. Defaulting. Last error: {last_error}")
    return {
        "action": "policy_question",
        "leave_type": "other",
        "start_date": None,
        "end_date": None,
        "leave_id": None,
        "reason": None,
        "needs_confirmation": False,
        "confirmation_message": None,
        "missing_info": [],
    }
