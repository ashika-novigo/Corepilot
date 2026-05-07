"""
hr_agent.py  —  Agentic HR assistant with session memory.

Design
------
* history   : list of {"role": "user"|"assistant", "content": str}
              The caller owns this list and records completed exchanges.
              The agent only reads it for context.

* Agentic leave application flow:
    1. User says "apply leave" (possibly with partial info).
    2. Agent asks clarifying questions for anything missing
       (leave_type, start_date, end_date, reason).
    3. Once all fields are collected, agent shows a confirmation summary.
    4. User confirms → leave is applied.

* All other actions (approve/reject, cancel, status, balance, history,
  policy questions) remain intact.
"""

from datetime import date, timedelta, datetime
import re

import dateparser
from dateparser.search import search_dates

from app.config.company import CEO_NAME, COMPANY_NAME
from app.services.hr_ai_service import extract_hr_action
from app.services.leave_service import (
    apply_leave,
    get_leave_history,
    get_pending_leaves,
    get_leave_balance,
    cancel_leave,
    get_pending_leaves_for_manager,
    approve_leave_by_manager,
    reject_leave_by_manager,
)
from app.services.calendar_service import get_non_working_days_between, get_working_days
from app.services.date_service import get_today, get_today_text
from app.rag.retriever import retrieve_docs
from ai.groq_client import get_llm
from ai.state import AgentSessionState, normalize_history
from models.employee import Employee
from models.leave import LeaveRequest
from app.services.email_service import send_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_role(user, allowed_roles: list) -> bool:
    return user.role in allowed_roles


def _is_insufficient_balance(result) -> bool:
    return isinstance(result, dict) and result.get("status") == "insufficient_balance"


def _is_non_working_leave(result) -> bool:
    return isinstance(result, dict) and result.get("status") == "non_working_days"


def _insufficient_balance_reply(result) -> str:
    leave_type = result.get("leave_type", "casual")
    remaining = result.get("remaining", 0)
    if remaining == 0:
        alternatives = [item for item in ("sick", "casual", "earned") if item != leave_type]
        return (
            f"You have 0 {leave_type} leaves remaining. "
            f"You may apply {'/'.join(alternatives)} leave if available."
        )
    return f"You only have {remaining} {leave_type} leaves remaining. Please choose another leave type or reduce days."


def _format_leave_balance(balance: dict, user_name: str) -> str:
    lines = [f"📊 **Leave Balance for {user_name}:**"]
    for leave_type in ("sick", "casual", "earned"):
        item = balance.get(leave_type, {"used": 0, "total": 0, "remaining": 0})
        lines.append(
            f"• {leave_type.capitalize()}: "
            f"{item['used']}/{item['total']} used | {item['remaining']} remaining"
        )
    return "\n".join(lines)


def _set_last_action(
    session_state: AgentSessionState | None,
    action: str,
    status: str = "success",
    tool_used: str = "hr_agent",
) -> None:
    if session_state:
        session_state.metadata["last_action"] = action
        session_state.metadata["last_status"] = status
        session_state.metadata["last_tool"] = tool_used


def _debug_action(message: str, action: str, leave_id=None, confirmed: bool = False) -> None:
    print(f"[HR_AGENT] message={message!r}, action={action}, leave_id={leave_id}, confirmed={confirmed}")


def _to_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()

    return value

def _parse_iso_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _text_month_number(month_text: str) -> int | None:
    months = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }
    return months.get(month_text.lower())


def _validate_textual_dates(message: str) -> str | None:
    month_pattern = (
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )
    patterns = (
        rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{month_pattern})\s+(?P<year>\d{{4}})\b",
        rf"\b(?P<month>{month_pattern})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:,)?\s+(?P<year>\d{{4}})\b",
    )

    for pattern in patterns:
        for match in re.finditer(pattern, message, flags=re.IGNORECASE):
            day = int(match.group("day"))
            month = _text_month_number(match.group("month"))
            year = int(match.group("year"))
            if not month:
                continue
            try:
                date(year, month, day)
            except ValueError:
                return f"Invalid date: {year:04d}-{month:02d}-{day:02d}"

    return None


def _next_weekday(target_weekday: int, today: date | None = None) -> date:
    today = today or get_today()
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _explicit_weekday_date(message: str) -> date | None:
    msg = (message or "").lower()
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    for name, weekday in weekdays.items():
        if re.search(rf"\b(?:on\s+|next\s+|this\s+)?{name}\b", msg):
            return _next_weekday(weekday)
    return None


def _extract_reason_hint(message: str) -> str | None:
    msg = (message or "").strip()
    lower = msg.lower()

    duration_match = re.search(r"\bfor\s+\d+\s+days?\b", lower)
    if not duration_match:
        for_match = re.search(r"\bfor\s+(.+)$", msg, flags=re.IGNORECASE)
        if for_match:
            reason = for_match.group(1).strip(" .")
            if reason and not re.search(r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", reason.lower()):
                return reason

    for pattern in (
        r"\bi\s+have\s+(?:a|an)?\s*(.+)$",
        r"\bbecause\s+(.+)$",
        r"\breason\s+(?:is\s+)?(.+)$",
    ):
        match = re.search(pattern, msg, flags=re.IGNORECASE)
        if match:
            reason = match.group(1).strip(" .")
            if reason:
                if pattern.startswith(r"\bi\s+have"):
                    return f"I have {reason}"
                return reason

    return None


def parse_flexible_dates(message: str) -> dict:
    """
    Structured date fallback for leave extraction.

    Returns ISO strings for start_date/end_date and a date_error string when an
    explicitly supplied ISO date is impossible.
    """
    msg = message or ""
    msg_lower = msg.lower()
    today = get_today()

    iso_dates = []
    for iso_text in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", msg):
        try:
            parsed = _parse_iso_date(iso_text)
        except ValueError:
            return {
                "start_date": None,
                "end_date": None,
                "date_error": f"Invalid date: {iso_text}",
            }
        iso_dates.append(parsed)

    if len(iso_dates) >= 2:
        return {
            "start_date": iso_dates[0].isoformat(),
            "end_date": iso_dates[1].isoformat(),
            "date_error": None,
        }
    if len(iso_dates) == 1:
        return {
            "start_date": iso_dates[0].isoformat(),
            "end_date": iso_dates[0].isoformat(),
            "date_error": None,
        }

    textual_date_error = _validate_textual_dates(msg)
    if textual_date_error:
        return {
            "start_date": None,
            "end_date": None,
            "date_error": textual_date_error,
        }

    manual_date = None
    weekday_date = None
    if "day after tomorrow" in msg_lower:
        manual_date = today + timedelta(days=2)
    elif re.search(r"\btomorrow\b", msg_lower):
        manual_date = today + timedelta(days=1)
    elif re.search(r"\btoday\b", msg_lower):
        manual_date = today
    else:
        weekday_date = _explicit_weekday_date(msg)
        manual_date = weekday_date

    duration_match = re.search(
        r"\bfor\s+(\d+)\s+days?\s+(?:from|starting|start(?:ing)?\s+from)\s+(.+)",
        msg_lower,
    )

    weekday_range = re.search(
        r"\b(to|until|through)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d)",
        msg_lower,
    )
    if manual_date and not duration_match and (weekday_date or not re.search(r"\b(to|until|through)\b", msg_lower)) and not weekday_range:
        return {
            "start_date": manual_date.isoformat(),
            "end_date": manual_date.isoformat(),
            "date_error": None,
        }

    settings = {
        "RELATIVE_BASE": datetime.combine(today, datetime.min.time()),
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }

    found_dates = []
    if manual_date:
        found_dates.append(manual_date)

    search_text = duration_match.group(2) if duration_match else msg
    results = search_dates(search_text, settings=settings) or []
    for _, parsed_dt in results:
        parsed_date = parsed_dt.date()
        if parsed_date not in found_dates:
            found_dates.append(parsed_date)

    if duration_match:
        days = int(duration_match.group(1))
        if found_dates and days > 0:
            start = found_dates[0]
            end = start + timedelta(days=days - 1)
            return {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "date_error": None,
            }

    if not found_dates:
        parsed = dateparser.parse(msg, settings=settings)
        if parsed:
            found_dates.append(parsed.date())

    if len(found_dates) >= 2:
        return {
            "start_date": found_dates[0].isoformat(),
            "end_date": found_dates[1].isoformat(),
            "date_error": None,
        }

    if len(found_dates) == 1:
        return {
            "start_date": found_dates[0].isoformat(),
            "end_date": found_dates[0].isoformat(),
            "date_error": None,
        }

    return {"start_date": None, "end_date": None, "date_error": None}


def _normalize_dates(message: str, start_date, end_date):
    """Fall back to flexible date parsing when the LLM could not resolve dates."""
    if start_date and end_date:
        return start_date, end_date

    parsed = parse_flexible_dates(message)
    if parsed.get("date_error"):
        return start_date, end_date

    return (
        start_date or parsed.get("start_date"),
        end_date or parsed.get("end_date"),
    )


def _invalid_date_reply(date_error: str | None = None) -> str:
    return "That date is invalid. Please provide a valid calendar date."


def _date_validation_error(ctx: dict) -> str | None:
    try:
        start = _to_date(ctx.get("start_date"))
        end = _to_date(ctx.get("end_date"))
    except ValueError:
        return _invalid_date_reply()

    if start and start < get_today():
        return "You cannot apply leave for a past date. Please choose today or a future date."
    if start and end and end < start:
        return "End date cannot be before start date."

    return None


def _format_excluded_days(days: list[dict]) -> str:
    if not days:
        return "None"
    return ", ".join(f"{item['date'].isoformat()} ({item['reason']})" for item in days)


def _enrich_working_day_context(ctx: dict, db) -> str | None:
    try:
        start = _to_date(ctx.get("start_date"))
        end = _to_date(ctx.get("end_date"))
    except ValueError:
        return _invalid_date_reply()

    if not start or not end:
        return None

    excluded = get_non_working_days_between(start, end, db)
    working_days = get_working_days(db, start, end)
    if not working_days:
        return "This date falls on a weekend/holiday, so leave is not required."

    ctx["working_leave_days"] = len(working_days)
    ctx["excluded_non_working_days"] = _format_excluded_days(excluded)
    return None


def _balance_validation_error(ctx: dict, db, user) -> str | None:
    leave_type = (ctx.get("leave_type") or "").lower()
    working_days = ctx.get("working_leave_days")
    if leave_type not in {"sick", "casual", "earned"} or not working_days:
        return None

    balance = get_leave_balance(db, user.id)
    remaining = balance.get(leave_type, {}).get("remaining", 0)
    if working_days > remaining:
        return _insufficient_balance_reply({
            "leave_type": leave_type,
            "remaining": remaining,
        })

    return None


def _answer_policy_question(message: str, history: list) -> str:
    """RAG-based policy answer with conversation context."""
    docs = retrieve_docs(message)

    if not docs:
        return "I could not find relevant policy information in the uploaded documents."

    context = "\n\n---\n\n".join(docs)
    llm = get_llm()

    history_text = ""
    if history:
        turns = [
            f"{t['role'].capitalize()}: {t['content']}"
            for t in history[-6:]
        ]
        history_text = "\n".join(turns)

    prompt = f"""
You are an enterprise HR policy assistant.

Today/date awareness: {get_today_text()}.
Company: {COMPANY_NAME}
CEO: {CEO_NAME}

Answer using ONLY the provided document context and company constants above.
Never invent company facts.
If answer is not in RAG, say "I could not find this in company documents."
For company name and CEO, use company.py constants.
Do not mention any legacy or incorrect company names.

{"Conversation history:\\n" + history_text if history_text else ""}

Document context:
{context}

User question:
{message}
"""
    response = llm.invoke(prompt)
    return response.content.strip()


def _pending_info_questions(missing: list) -> str:
    """Build a natural-language question asking for missing fields."""
    field_questions = {
        "leave_type": "What **type** of leave? (casual / sick / earned / other)",
        "start_date": "What is the **start date**? (e.g. 2026-05-10 or 'next Monday')",
        "end_date":   "What is the **end date**? (e.g. 2026-05-12 or 'same day')",
        "reason":     "Could you share a brief **reason** for the leave?",
    }
    questions = [field_questions[f] for f in missing if f in field_questions]
    if not questions:
        return ""
    return "I need a few more details:\n" + "\n".join(f"• {q}" for q in questions)

def _pending_leave_questions(ctx: dict, missing: list) -> str:
    if missing == ["reason"] and ctx.get("leave_type") and ctx.get("start_date") and ctx.get("end_date"):
        leave_type = str(ctx["leave_type"]).capitalize()
        if ctx["start_date"] == ctx["end_date"]:
            return f"I found {leave_type} leave for {ctx['start_date']}. Could you share a brief reason?"
        return (
            f"I found {leave_type} leave from {ctx['start_date']} to {ctx['end_date']}. "
            "Could you share a brief reason?"
        )

    return _pending_info_questions(missing)


def _explicit_leave_type_in_message(message: str) -> str | None:
    msg = (message or "").lower()
    if re.search(r"\bsick\s+leave\b|\bsick\s+day\b|\bsick\b", msg):
        return "sick"
    if re.search(r"\bcasual\s+leave\b|\bcasual\b", msg):
        return "casual"
    if re.search(r"\bearned\s+leave\b|\bannual\s+leave\b|\bvacation\b", msg):
        return "earned"
    if re.search(r"\bother\s+leave\b", msg):
        return "other"
    return None


def _normalize_extracted_leave_type(message: str, leave_type: str | None, pending: dict | None = None) -> str | None:
    if not leave_type:
        return None

    leave_type = leave_type.lower()
    explicit_type = _explicit_leave_type_in_message(message)
    if explicit_type:
        return explicit_type

    # In a pending flow, a bare "sick"/"casual"/"earned" can be the answer to
    # the assistant's leave-type question. Outside that narrow case, do not let
    # the LLM infer a type the user did not say.
    if pending and "leave_type" in (pending.get("_missing") or []):
        if message.strip().lower() in {"sick", "casual", "earned", "other"}:
            return leave_type

    return None


def _is_leave_advice_question(message: str) -> bool:
    msg = message.lower()
    has_leave_word = any(
        word in msg
        for word in ("leave", "time off", "vacation", "sick day")
    )
    asks_for_choice = any(
        phrase in msg
        for phrase in (
            "what leave",
            "which leave",
            "what type",
            "which type",
            "should i put",
            "should i apply",
            "can i put",
            "can i apply",
        )
    )
    return has_leave_word and asks_for_choice


def _answer_leave_advice_question(message: str, history: list) -> str:
    msg = message.lower()

    if any(word in msg for word in ("not feeling well", "unwell", "sick", "fever", "ill")):
        return (
            "You should apply for **sick leave**. If you want, I can help you apply it."
        )

    if "can i" in msg and "leave" in msg:
        parsed = parse_flexible_dates(message)
        if parsed.get("date_error"):
            return _invalid_date_reply(parsed.get("date_error"))
        when = "for that date"
        if parsed.get("start_date") and parsed.get("start_date") == parsed.get("end_date"):
            when = f"for {parsed['start_date']}"
        elif parsed.get("start_date") and parsed.get("end_date"):
            when = f"from {parsed['start_date']} to {parsed['end_date']}"
        return (
            f"Yes, you can apply leave {when} if you have sufficient balance and there are "
            "no overlapping approved or pending leave requests. Tell me the leave type and "
            "reason if you want me to apply it."
        )

    return _answer_policy_question(message, history)


def _deterministic_hr_route(message: str) -> dict | None:
    msg = (message or "").lower().strip()

    patterns = (
        (r"\bconfirm\s+approve\s+leave\s+#?(\d+)\b", "approve_leave", True),
        (r"\bapprove\s+leave\s+#?(\d+)\b", "approve_leave", False),
        (r"\bconfirm\s+reject\s+leave\s+#?(\d+)\b", "reject_leave", True),
        (r"\breject\s+leave\s+#?(\d+)\b", "reject_leave", False),
        (r"\bcancel\s+leave\s+#?(\d+)\b", "cancel_leave", False),
    )
    for pattern, action, confirmed in patterns:
        match = re.search(pattern, msg)
        if match:
            return {
                "action": action,
                "leave_type": None,
                "start_date": None,
                "end_date": None,
                "leave_id": int(match.group(1)),
                "reason": None,
                "missing_info": [],
                "date_error": None,
                "confirmed": confirmed,
            }

    status_match = (
        re.search(r"\b(?:status|check).*(?:leave)\s+#?(\d+)\b", msg)
        or re.search(r"\bleave\s+#?(\d+).*\bstatus\b", msg)
    )
    if status_match:
        return {
            "action": "leave_status",
            "leave_type": None,
            "start_date": None,
            "end_date": None,
            "leave_id": int(status_match.group(1)),
            "reason": None,
            "missing_info": [],
            "date_error": None,
            "confirmed": False,
        }

    if re.search(r"\b(show|view|check)\b.*\bleave\s+balance\b|\bmy\s+leave\s+balance\b", msg):
        return {"action": "leave_balance", "leave_id": None, "confirmed": False}
    if re.search(r"\b(show|view|check)\b.*\bleave\s+history\b|\bmy\s+leave\s+history\b", msg):
        return {"action": "leave_history", "leave_id": None, "confirmed": False}
    if re.search(r"\b(show|view|check)\b.*\bpending\s+approvals\b", msg):
        return {"action": "pending_approvals", "leave_id": None, "confirmed": False}
    if re.search(r"\b(show|view|check)\b.*\bpending\s+leaves\b|\bmy\s+pending\s+leaves\b", msg):
        return {"action": "pending_leaves", "leave_id": None, "confirmed": False}
    if re.search(r"\bwhat\s+day\s+is\s+today\b|\btoday'?s\s+date\b|\bwhat\s+is\s+today\b", msg):
        return {"action": "date_question", "leave_id": None, "confirmed": False}
    if re.search(r"\bwho\s+is\s+(?:the\s+)?ceo\b|\bcompany\s+name\b|\borganization\s+name\b|\borganisation\s+name\b", msg):
        return {"action": "company_info", "leave_id": None, "confirmed": False}
    if "leave" in msg and re.search(r"\b(policy|rule|rules|entitlement|eligible|eligibility)\b", msg):
        return {"action": "leave_policy_question", "leave_id": None, "confirmed": False}
    if "leave" in msg and re.search(r"^\s*(what\s+if|if\s+i|can\s+i|what\s+happens)", msg):
        return {"action": "leave_advice", "leave_id": None, "confirmed": False}

    return None


def _complete_action_data(data: dict) -> dict:
    return {
        "action": data.get("action", "general_hr_question"),
        "leave_type": data.get("leave_type"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "leave_id": data.get("leave_id"),
        "reason": data.get("reason"),
        "missing_info": data.get("missing_info") or [],
        "date_error": data.get("date_error"),
        "confirmed": bool(data.get("confirmed", False)),
    }


def _looks_like_pending_leave_update(message: str, pending: dict) -> bool:
    msg = message.lower().strip()
    missing = set(pending.get("_missing") or [])

    if not msg:
        return False

    if "leave_type" in missing and (msg in ("casual", "sick", "earned", "other") or _explicit_leave_type_in_message(message)):
        return True

    if "reason" in missing and not _is_leave_advice_question(message):
        unrelated_words = (
            "balance",
            "history",
            "policy",
            "status",
            "pending",
            "approve",
            "reject",
            "cancel",
            "what",
            "which",
            "how",
            "can i",
            "should i",
        )
        if any(word in msg for word in unrelated_words):
            return False
        return True

    if {"start_date", "end_date"} & missing:
        date_words = (
            "today",
            "tomorrow",
            "day after tomorrow",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "same day",
            "jan",
            "january",
            "feb",
            "february",
            "mar",
            "march",
            "apr",
            "april",
            "may",
            "jun",
            "june",
            "jul",
            "july",
            "aug",
            "august",
            "sep",
            "september",
            "oct",
            "october",
            "nov",
            "november",
            "dec",
            "december",
        )
        if re.search(r"\d{4}-\d{2}-\d{2}", msg):
            return True
        if re.search(r"\b\d{1,2}(?:st|nd|rd|th)?(?:[/-]\d{1,2}(?:[/-]\d{2,4})?)?\b", msg):
            return True
        if any(word in msg for word in date_words):
            return True

    return False


# ---------------------------------------------------------------------------
# Pending-leave context stored in hidden session state
# ---------------------------------------------------------------------------

_PENDING_KEY = "hr_leave"


def _get_pending(history: list = None, session_state: AgentSessionState | None = None) -> dict | None:
    """Return the most recent pending leave context from history, or None."""
    if session_state:
        pending = session_state.get_pending(_PENDING_KEY)
        if pending:
            return pending

    for turn in reversed(history or []):
        if turn.get("role") == "_system" and _PENDING_KEY in turn:
            return turn[_PENDING_KEY]
    return None


def _set_pending(
    history: list = None,
    ctx: dict | None = None,
    session_state: AgentSessionState | None = None,
):
    """Set pending leave context in hidden session state, with history fallback."""
    ctx = ctx or {}

    if session_state:
        session_state.set_pending(_PENDING_KEY, ctx)
        session_state.set_agent("hr")
        return

    if history is not None:
        history[:] = [
            t for t in history
            if not (t.get("role") == "_system" and _PENDING_KEY in t)
        ]
        history.append({"role": "_system", _PENDING_KEY: ctx})


def _clear_pending(history: list = None, session_state: AgentSessionState | None = None):
    if session_state:
        session_state.clear_pending(_PENDING_KEY)
        session_state.set_agent(None)
        return

    if history is not None:
        history[:] = [
            t for t in history
            if not (t.get("role") == "_system" and _PENDING_KEY in t)
        ]


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def hr_agent(
    message: str,
    db,
    user,
    history: list = None,
    session_state: AgentSessionState | None = None,
) -> str:
    """
    Process one user message and return the assistant reply.

    The caller owns history persistence. This agent reads prior turns and
    stores hidden multi-turn flow data in session_state when available.

    Parameters
    ----------
    message : str   — raw user text
    db              — SQLAlchemy session
    user            — authenticated Employee ORM object
    history : list  — mutable list of chat turns (see module docstring)

    Returns
    -------
    str  — assistant response to display
    """
    if session_state:
        history = session_state.history
        session_state.set_agent("hr")

    return _process(
        message,
        db,
        user,
        history if history is not None else [],
        session_state=session_state,
    )


# ---------------------------------------------------------------------------
# Internal dispatcher
# ---------------------------------------------------------------------------

def _conversation_with_current(
    history: list,
    message: str,
    session_state: AgentSessionState | None = None,
) -> list:
    if session_state:
        return session_state.prompt_history(limit=10)

    return normalize_history(history)[-10:]


def _process(
    message: str,
    db,
    user,
    history: list,
    session_state: AgentSessionState | None = None,
    ignore_pending: bool = False,
) -> str:
    deterministic = _deterministic_hr_route(message)

    # -----------------------------------------------------------------------
    # Step 1 — Check if we are mid-flow for a pending leave application
    # -----------------------------------------------------------------------
    pending = None if ignore_pending else _get_pending(history, session_state=session_state)

    if pending and pending.get("flow") == "apply_leave" and deterministic:
        _clear_pending(history, session_state=session_state)
        pending = None

    if pending and pending.get("flow") == "apply_leave":
        msg_lower = message.lower().strip()

        # User said "cancel" or "no" → abort
        if msg_lower in ("cancel", "no", "nope", "abort", "stop", "never mind", "nevermind"):
            _clear_pending(history, session_state=session_state)
            return "Leave application cancelled."

        # User confirmed → apply the leave
        if msg_lower in ("yes", "confirm", "ok", "okay", "sure", "proceed", "apply"):
            return _apply_pending_leave(pending, db, user, history, session_state=session_state)

        if pending.get("_awaiting_confirm") and re.search(r"\b(one|1|single)\s+day\b", msg_lower):
            updated = dict(pending)
            if updated.get("start_date"):
                updated["end_date"] = updated["start_date"]
            updated.pop("_awaiting_confirm", None)
            date_validation_error = _date_validation_error(updated)
            if date_validation_error:
                return date_validation_error
            calendar_error = _enrich_working_day_context(updated, db)
            if calendar_error:
                return calendar_error
            _set_pending(history, {**updated, "flow": "apply_leave", "_missing": [], "_awaiting_confirm": True}, session_state=session_state)
            return _confirmation_summary(updated)

        # User is answering follow-up questions — merge new info into pending
        if _is_leave_advice_question(message):
            _clear_pending(history, session_state=session_state)
            return _answer_leave_advice_question(message, history)

        if not _looks_like_pending_leave_update(message, pending):
            _clear_pending(history, session_state=session_state)
            return _process(
                message,
                db,
                user,
                history,
                session_state=session_state,
                ignore_pending=True,
            )

        prompt_history = _conversation_with_current(history, message, session_state)
        updated = _merge_pending_with_new_message(pending, message, prompt_history)
        if updated.get("_date_error"):
            return _invalid_date_reply(updated.get("_date_error"))
        date_validation_error = _date_validation_error(updated)
        if date_validation_error:
            return date_validation_error
        calendar_error = _enrich_working_day_context(updated, db)
        if calendar_error:
            return calendar_error
        balance_error = _balance_validation_error(updated, db, user)
        if balance_error:
            return balance_error
        _set_pending(history, updated, session_state=session_state)
        return _advance_pending_flow(updated, db=db)

    if pending and not ignore_pending:
        _clear_pending(history, session_state=session_state)
        pending = None

    if not pending and message.lower().strip() in ("no", "nope"):
        return "Okay, no action taken."

    # -----------------------------------------------------------------------
    # Step 2 — Extract intent from the current message (with full history)
    # -----------------------------------------------------------------------
    prompt_history = _conversation_with_current(history, message, session_state)
    if not deterministic and _is_leave_advice_question(message):
        return _answer_leave_advice_question(message, prompt_history)

    data = _complete_action_data(deterministic or extract_hr_action(message, history=prompt_history))

    action      = data["action"]
    leave_type  = data["leave_type"]
    start_date  = data["start_date"]
    end_date    = data["end_date"]
    leave_id    = data["leave_id"]
    reason      = data["reason"]
    missing     = data["missing_info"]
    confirmed   = data.get("confirmed", False)
    leave_type = _normalize_extracted_leave_type(message, leave_type)
    reason = reason or _extract_reason_hint(message)

    if data.get("date_error"):
        return _invalid_date_reply(data.get("date_error"))

    _debug_action(message, action, leave_id, confirmed)

    if action == "date_question":
        _set_last_action(session_state, "date_question_answered")
        return get_today_text()

    if action == "company_info":
        _set_last_action(session_state, "company_info_answered")
        return f"CEO: {CEO_NAME}\nCompany: {COMPANY_NAME}"

    if action == "leave_advice":
        return _answer_leave_advice_question(message, prompt_history)

    if action == "leave_policy_question":
        _set_last_action(session_state, "leave_policy_answered")
        return _answer_policy_question(message, prompt_history)

    # -----------------------------------------------------------------------
    # 1. Apply leave — agentic multi-turn flow
    # -----------------------------------------------------------------------
    if action == "apply_leave":
        if not start_date or not end_date:
            fallback = parse_flexible_dates(message)
            if fallback.get("date_error"):
                return _invalid_date_reply(fallback.get("date_error"))
            start_date = start_date or fallback.get("start_date")
            end_date = end_date or fallback.get("end_date")

        ctx = {
            "leave_type": leave_type,
            "start_date": str(start_date) if start_date else None,
            "end_date":   str(end_date)   if end_date   else None,
            "reason":     reason,
        }

        date_validation_error = _date_validation_error(ctx)
        if date_validation_error:
            return date_validation_error
        calendar_error = _enrich_working_day_context(ctx, db)
        if calendar_error:
            return calendar_error
        balance_error = _balance_validation_error(ctx, db, user)
        if balance_error:
            return balance_error

        # Work out what is still missing
        still_missing = []
        if not ctx["leave_type"] or ctx["leave_type"] == "other":
            still_missing.append("leave_type")
        if not ctx["start_date"]:
            still_missing.append("start_date")
        if not ctx["end_date"]:
            still_missing.append("end_date")
        if not ctx["reason"]:
            still_missing.append("reason")

        if still_missing:
            _set_pending(history, {**ctx, "flow": "apply_leave", "_missing": still_missing}, session_state=session_state)
            return _pending_leave_questions(ctx, still_missing)

        validation_error = _validate_leave_context(ctx, db=db)
        if validation_error:
            return validation_error

        # All info present — ask for confirmation
        _set_pending(history, {**ctx, "flow": "apply_leave", "_missing": [], "_awaiting_confirm": True}, session_state=session_state)
        return _confirmation_summary(ctx)

    # -----------------------------------------------------------------------
    # 2. Leave balance
    # -----------------------------------------------------------------------
    if action == "leave_balance":
        balance = get_leave_balance(db, user.id)
        return _format_leave_balance(balance, user.name)

    # -----------------------------------------------------------------------
    # 3. Leave history
    # -----------------------------------------------------------------------
    if action == "leave_history":
        if user.role == "admin":
            leaves = db.query(LeaveRequest).all()
        else:
            leaves = get_leave_history(db, user.id)
        if not leaves:
            return "You have no leave history yet."
        lines = [
            f"• Leave #{l.id}: {l.leave_type.capitalize()} | "
            f"{l.start_date} → {l.end_date} | **{l.status}**"
            for l in leaves
        ]
        return "📋 **Your Leave History:**\n" + "\n".join(lines)

    # -----------------------------------------------------------------------
    # 4. Pending leaves (employee's own)
    # -----------------------------------------------------------------------
    if action == "pending_leaves":
        leaves = get_pending_leaves(db, user.id)
        if not leaves:
            return "You have no pending leave requests."
        lines = [
            f"• Leave #{l.id}: {l.leave_type.capitalize()} | "
            f"{l.start_date} → {l.end_date} | {l.status}"
            for l in leaves
        ]
        return "⏳ **Your Pending Leaves:**\n" + "\n".join(lines)

    # -----------------------------------------------------------------------
    # 5. Manager — pending approvals
    # -----------------------------------------------------------------------
    if action == "pending_approvals":
        if not _require_role(user, ["manager", "hr", "admin"]):
            _set_last_action(session_state, "access_denied", "access_denied")
            return "⛔ Access denied. Only managers can view pending approvals."
        leaves = get_pending_leaves_for_manager(db, user.id)
        if not leaves:
            return "No pending leave approvals for your team."
        lines = [
            f"• Leave #{l.id}: Employee {l.employee_id} | "
            f"{l.leave_type.capitalize()} | {l.start_date} → {l.end_date} | {l.status}"
            for l in leaves
        ]
        return "📥 **Pending Approvals:**\n" + "\n".join(lines)

    # -----------------------------------------------------------------------
    # 6. Approve leave
    # -----------------------------------------------------------------------
    if action == "approve_leave":
        if not _require_role(user, ["manager", "hr", "admin"]):
            _set_last_action(session_state, "access_denied", "access_denied")
            return "⛔ Access denied. Only managers can approve leave."
        if not leave_id:
            return "Please provide the leave ID. Example: `approve leave 12`"
        if not confirmed:
            return (
                f"Please confirm: approve leave #{leave_id}?\n"
                f"Reply: confirm approve leave {leave_id}"
            )
        leave = approve_leave_by_manager(db, leave_id, user.id)
        if _is_insufficient_balance(leave):
            _set_last_action(session_state, "leave_approved", "insufficient_balance")
            return _insufficient_balance_reply(leave)
        if not leave:
            return "Leave not found, already processed, or not under your authority."
        _set_last_action(session_state, "leave_approved")
        return f"✅ Leave **#{leave.id}** approved successfully."

    # -----------------------------------------------------------------------
    # 7. Reject leave
    # -----------------------------------------------------------------------
    if action == "reject_leave":
        if not _require_role(user, ["manager", "hr", "admin"]):
            _set_last_action(session_state, "access_denied", "access_denied")
            return "⛔ Access denied. Only managers can reject leave."
        if not leave_id:
            return "Please provide the leave ID. Example: `reject leave 12`"
        if not confirmed:
            return (
                f"Please confirm: reject leave #{leave_id}?\n"
                f"Reply: confirm reject leave {leave_id}"
            )
        leave = reject_leave_by_manager(db, leave_id, user.id)
        if not leave:
            return "Leave not found, already processed, or not under your authority."
        _set_last_action(session_state, "leave_rejected")
        return f"❌ Leave **#{leave.id}** rejected successfully."

    # -----------------------------------------------------------------------
    # 8. Cancel leave
    # -----------------------------------------------------------------------
    if action == "cancel_leave":
        if not leave_id:
            return "Please mention the leave ID to cancel. Example: `cancel leave 7`"
        result = cancel_leave(db, user.id, leave_id)
        if result is None:
            return f"Leave request **#{leave_id}** not found."
        if result == "not_allowed":
            return "Only **pending** leave requests can be cancelled."
        _set_last_action(session_state, "leave_cancelled")
        return f"✅ Leave request **#{result.id}** has been cancelled."

    # -----------------------------------------------------------------------
    # 9. Leave status
    # -----------------------------------------------------------------------
    if action == "leave_status":
        if not leave_id:
            return "Please provide the leave ID. Example: `status of leave 12`"
        leave = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.id == leave_id, LeaveRequest.employee_id == user.id)
            .first()
        )
        if not leave:
            return f"Leave **#{leave_id}** not found or does not belong to you."
        return (
            f"**Leave #{leave.id}**\n"
            f"• Type:   {leave.leave_type.capitalize()}\n"
            f"• Dates:  {leave.start_date} → {leave.end_date}\n"
            f"• Status: **{leave.status}**"
        )

    # -----------------------------------------------------------------------
    # 10. Policy question (default)
    # -----------------------------------------------------------------------
    _set_last_action(session_state, "policy_question_answered")
    return _answer_policy_question(message, history)


# ---------------------------------------------------------------------------
# Pending-leave helpers
# ---------------------------------------------------------------------------

def _merge_pending_with_new_message(pending: dict, message: str, history: list) -> dict:
    """
    Re-run extraction on the latest message but seed with what we already know.
    Then merge: only overwrite nulls in the pending context.
    """
    new = extract_hr_action(message, history=history)

    merged = dict(pending)  # copy
    if new.get("date_error"):
        merged["_date_error"] = new.get("date_error")
        return merged

    new_leave_type = _normalize_extracted_leave_type(message, new["leave_type"], pending=merged)
    if not merged.get("leave_type") or merged.get("leave_type") == "other":
        if new_leave_type and new_leave_type != "other":
            merged["leave_type"] = new_leave_type

    if not merged.get("start_date") and new["start_date"]:
        merged["start_date"] = new["start_date"]

    if not merged.get("end_date") and new["end_date"]:
        # If user said "same day" or only gave one date, mirror start
        merged["end_date"] = new["end_date"] or merged.get("start_date")

    reason_hint = new["reason"] or _extract_reason_hint(message)
    if not merged.get("reason") and reason_hint:
        merged["reason"] = reason_hint

    fallback = parse_flexible_dates(message)
    if fallback.get("date_error"):
        merged["_date_error"] = fallback.get("date_error")
        return merged

    if not merged.get("start_date") and fallback.get("start_date"):
        merged["start_date"] = fallback.get("start_date")
    if not merged.get("end_date") and fallback.get("end_date"):
        merged["end_date"] = fallback.get("end_date")

    return merged


def _advance_pending_flow(ctx: dict, db=None) -> str:
    """
    Decide next step: ask for more info, or present confirmation summary.
    """
    date_validation_error = _date_validation_error(ctx)
    if date_validation_error:
        return date_validation_error
    calendar_error = _enrich_working_day_context(ctx, db)
    if calendar_error:
        return calendar_error

    still_missing = []
    if not ctx.get("leave_type") or ctx.get("leave_type") == "other":
        still_missing.append("leave_type")
    if not ctx.get("start_date"):
        still_missing.append("start_date")
    if not ctx.get("end_date"):
        still_missing.append("end_date")
    if not ctx.get("reason"):
        still_missing.append("reason")

    ctx["_missing"] = still_missing

    if still_missing:
        return _pending_leave_questions(ctx, still_missing)

    ctx["_awaiting_confirm"] = True
    return _confirmation_summary(ctx)


def _validate_leave_context(ctx: dict, db=None) -> str | None:
    date_validation_error = _date_validation_error(ctx)
    if date_validation_error:
        return date_validation_error

    leave_type = (ctx.get("leave_type") or "").lower()
    if leave_type not in {"sick", "casual", "earned", "other"}:
        return "Please choose a valid leave type: sick, casual, or earned."
    if leave_type == "other":
        return "Please choose one of these leave types: sick, casual, or earned."

    try:
        start = _to_date(ctx.get("start_date"))
        end = _to_date(ctx.get("end_date"))
    except ValueError:
        return _invalid_date_reply()

    if not start or not end:
        return "Please provide the leave dates."
    calendar_error = _enrich_working_day_context(ctx, db)
    if calendar_error:
        return calendar_error
    return None


def _confirmation_summary(ctx: dict) -> str:
    return (
        f"📋 **Leave Application Summary:**\n"
        f"• Type:   {str(ctx.get('leave_type', '')).capitalize()}\n"
        f"• From:   {ctx.get('start_date')}\n"
        f"• To:     {ctx.get('end_date')}\n"
        f"• Working leave days: {ctx.get('working_leave_days') or ctx.get('total_days') or 1}\n"
        f"• Excluded non-working days: {ctx.get('excluded_non_working_days') or 'None'}\n"
        f"• Reason: {ctx.get('reason') or 'Not provided'}\n\n"
        f"Shall I go ahead and apply this leave? Reply **yes** to confirm or **cancel** to abort."
    )


def _apply_pending_leave(
    ctx: dict,
    db,
    user,
    history: list,
    session_state: AgentSessionState | None = None,
) -> str:
    """Actually create the leave record and notify the manager."""
    _clear_pending(history, session_state=session_state)

    try:
        start = _to_date(ctx.get("start_date"))
        end = _to_date(ctx.get("end_date"))
    except ValueError:
        return _invalid_date_reply()
    lt = ctx.get("leave_type", "casual")
    
    if not start or not end:
        return "I couldn't determine the leave dates. Please start over and provide the dates clearly."
    validation_error = _validate_leave_context({**ctx, "start_date": start, "end_date": end, "leave_type": lt}, db=db)
    if validation_error:
        return validation_error

    try:
        leave = apply_leave(
            db=db,
            employee_id=user.id,
            start_date=start,
            end_date=end,
            reason=ctx.get("reason") or "Applied via AI",
            leave_type=lt,
        )
    except Exception as e:
        print(f"[hr_agent] apply_leave error: {e}")
        return f"❌ Failed to apply leave: {e}"

    if _is_insufficient_balance(leave):
        _set_last_action(session_state, "leave_applied", "insufficient_balance")
        return _insufficient_balance_reply(leave)
    if _is_non_working_leave(leave):
        _set_last_action(session_state, "leave_applied", "non_working_days")
        return leave.get("message", "Selected date(s) are weekend/holiday. Leave is not required.")

    # Notify manager
    manager = db.query(Employee).filter(Employee.id == user.manager_id).first()
    if manager:
        try:
            send_email(
                to=manager.email, 
                subject="Leave Approval Required",
                body=(
                    f"Hello {manager.name},\n\n"
                    f"{user.name} has applied for {leave.leave_type} leave.\n\n"
                    f"Leave ID : #{leave.id}\n"
                    f"Dates    : {leave.start_date} to {leave.end_date}\n"
                    f"Reason   : {ctx.get('reason') or 'Not provided'}\n"
                    f"Status   : {leave.status}\n\n"
                    f"Please log in to Corepilot and take action:\n"
                    f"  confirm approve leave {leave.id}\n"
                    f"  confirm reject leave {leave.id}"
                ),
            )
        except Exception as e:
            print(f"[hr_agent] Email notification failed: {e}")

    _set_last_action(session_state, "leave_applied")
    return (
        f"✅ **{leave.leave_type.capitalize()} leave applied successfully!**\n"
        f"• Leave ID : #{leave.id}\n"
        f"• Dates    : {leave.start_date} → {leave.end_date}\n"
        f"• Status   : {leave.status}\n"
        f"• Manager  : notified via email."
    )
