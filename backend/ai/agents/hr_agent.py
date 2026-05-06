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


def _insufficient_balance_reply(result) -> str:
    leave_type = result.get("leave_type", "casual")
    remaining = result.get("remaining", 0)
    return (
        f"You only have {remaining} {leave_type} leaves remaining. "
        "Please choose another leave type or reduce days."
    )


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


def _to_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()

    return value

def _normalize_dates(message: str, start_date, end_date):
    """Fall back to dateparser when the LLM could not resolve dates."""
    if start_date and end_date:
        return start_date, end_date

    msg = message.lower()
    parsed_date = None

    if "tomorrow" in msg:
        parsed_date = date.today() + timedelta(days=1)
    elif "today" in msg:
        parsed_date = date.today()
    else:
        parsed = dateparser.parse(message)
        if parsed:
            parsed_date = parsed.date()

    if parsed_date:
        return parsed_date, parsed_date

    return start_date, end_date


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

Answer using ONLY the provided document context. Do not guess.

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
            "If you are not feeling well, **sick leave** is usually the right leave type. "
            "When you are ready to apply, tell me the date or dates and a brief reason."
        )

    return _answer_policy_question(message, history)


def _looks_like_pending_leave_update(message: str, pending: dict) -> bool:
    msg = message.lower().strip()
    missing = set(pending.get("_missing") or [])

    if not msg:
        return False

    if "leave_type" in missing and msg in ("casual", "sick", "earned", "other"):
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
        )
        if re.search(r"\d{4}-\d{2}-\d{2}", msg):
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

    return _process(message, db, user, history or [], session_state=session_state)


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

    # -----------------------------------------------------------------------
    # Step 1 — Check if we are mid-flow for a pending leave application
    # -----------------------------------------------------------------------
    pending = None if ignore_pending else _get_pending(history, session_state=session_state)

    if pending:
        msg_lower = message.lower().strip()

        # User said "cancel" or "no" → abort
        if msg_lower in ("cancel", "no", "nope", "abort", "stop"):
            _clear_pending(history, session_state=session_state)
            return "Leave application cancelled. Let me know if you need anything else."

        # User confirmed → apply the leave
        if msg_lower in ("yes", "confirm", "ok", "okay", "sure", "proceed", "apply"):
            return _apply_pending_leave(pending, db, user, history, session_state=session_state)

        # User is answering follow-up questions — merge new info into pending
        if _is_leave_advice_question(message):
            return _answer_leave_advice_question(message, history)

        if not _looks_like_pending_leave_update(message, pending):
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
        _set_pending(history, updated, session_state=session_state)
        return _advance_pending_flow(updated)

    # -----------------------------------------------------------------------
    # Step 2 — Extract intent from the current message (with full history)
    # -----------------------------------------------------------------------
    prompt_history = _conversation_with_current(history, message, session_state)
    if _is_leave_advice_question(message):
        return _answer_leave_advice_question(message, prompt_history)

    data = extract_hr_action(message, history=prompt_history)

    action      = data["action"]
    leave_type  = data["leave_type"]
    start_date  = data["start_date"]
    end_date    = data["end_date"]
    leave_id    = data["leave_id"]
    reason      = data["reason"]
    missing     = data["missing_info"]

    # Date normalisation fallback
    start_date, end_date = _normalize_dates(message, start_date, end_date)

    print(f"[hr_agent] action={action} | missing={missing} | data={data}")

    # -----------------------------------------------------------------------
    # 1. Apply leave — agentic multi-turn flow
    # -----------------------------------------------------------------------
    if action == "apply_leave":
        ctx = {
            "leave_type": leave_type,
            "start_date": str(start_date) if start_date else None,
            "end_date":   str(end_date)   if end_date   else None,
            "reason":     reason,
        }

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
            _set_pending(history, {**ctx, "_missing": still_missing}, session_state=session_state)
            return _pending_info_questions(still_missing)

        # All info present — ask for confirmation
        _set_pending(history, {**ctx, "_missing": [], "_awaiting_confirm": True}, session_state=session_state)
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
        if "confirm" not in message.lower():
            return (
                f"Please confirm: approve leave **#{leave_id}**?\n"
                f"Reply: `confirm approve leave {leave_id}`"
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
        if "confirm" not in message.lower():
            return (
                f"Please confirm: reject leave **#{leave_id}**?\n"
                f"Reply: `confirm reject leave {leave_id}`"
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

    if not merged.get("leave_type") or merged.get("leave_type") == "other":
        if new["leave_type"] and new["leave_type"] != "other":
            merged["leave_type"] = new["leave_type"]

    if not merged.get("start_date") and new["start_date"]:
        merged["start_date"] = new["start_date"]

    if not merged.get("end_date") and new["end_date"]:
        # If user said "same day" or only gave one date, mirror start
        merged["end_date"] = new["end_date"] or merged.get("start_date")

    if not merged.get("reason") and new["reason"]:
        merged["reason"] = new["reason"]

    # Also try dateparser on the raw message as a fallback for dates
    start, end = _normalize_dates(
        message,
        merged.get("start_date"),
        merged.get("end_date"),
    )
    merged["start_date"] = str(start) if start else merged.get("start_date")
    merged["end_date"]   = str(end)   if end   else merged.get("end_date")

    return merged


def _advance_pending_flow(ctx: dict) -> str:
    """
    Decide next step: ask for more info, or present confirmation summary.
    """
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
        return _pending_info_questions(still_missing)

    ctx["_awaiting_confirm"] = True
    return _confirmation_summary(ctx)


def _confirmation_summary(ctx: dict) -> str:
    return (
        f"📋 **Leave Application Summary:**\n"
        f"• Type:   {str(ctx.get('leave_type', '')).capitalize()}\n"
        f"• From:   {ctx.get('start_date')}\n"
        f"• To:     {ctx.get('end_date')}\n"
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

    start = _to_date(ctx.get("start_date"))
    end = _to_date(ctx.get("end_date"))
    lt = ctx.get("leave_type", "casual")
    
    if not start or not end:
        return "I couldn't determine the leave dates. Please start over and provide the dates clearly."

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
