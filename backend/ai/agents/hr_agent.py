from app.services.ai_service import extract_intent_and_entities
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
import re
from app.rag.retriever import retrieve_docs
from ai.groq_client import get_llm
import dateparser 
from datetime import date, timedelta
from models.employee import Employee
from app.services.email_service import send_email



def extract_leave_id(message: str):
    match = re.search(r"\d+", message)
    if match:
        return int(match.group())
    return None



def hr_agent(message: str, db, user):
    msg_lower = message.lower()

# Manager: view pending approvals
    if "pending" in msg_lower and "approval" in msg_lower:
        if user.role not in ["manager", "hr", "admin"]:
            return "Access denied. Only managers can view pending approvals."

        leaves = get_pending_leaves_for_manager(db, user.id)

        if not leaves:
            return "No pending leave approvals found."

        response = "Pending leave approvals:\n"

        for leave in leaves:
            response += (
                f"\nLeave ID: {leave.id}"
                f"\nEmployee ID: {leave.employee_id}"
                f"\nType: {leave.leave_type}"
                f"\nDates: {leave.start_date} to {leave.end_date}"
                f"\nDays: {leave.total_days}"
                f"\nStatus: {leave.status}\n"
            )

        return response


    # Manager: approve leave
    if "approve" in msg_lower and "leave" in msg_lower:
        if user.role not in ["manager", "hr", "admin"]:
            return "Access denied. Only managers can approve leave."

        leave_id = extract_leave_id(message)

        if not leave_id:
            return "Please provide leave ID. Example: approve leave 12"

        leave = approve_leave_by_manager(db, leave_id, user.id)

        if not leave:
            return "Leave not found, already processed, or not assigned to you."

        return f"✅ Leave #{leave.id} approved successfully."


    # Manager: reject leave
    if "reject" in msg_lower and "leave" in msg_lower:
        if user.role not in ["manager", "hr", "admin"]:
            return "Access denied. Only managers can reject leave."

        leave_id = extract_leave_id(message)

        if not leave_id:
            return "Please provide leave ID. Example: reject leave 12"

        leave = reject_leave_by_manager(db, leave_id, user.id)

        if not leave:
            return "Leave not found, already processed, or not assigned to you."

        return f"❌ Leave #{leave.id} rejected successfully."

   

    result = extract_intent_and_entities(message)
    
    
    intent = result.get("intent")
    start_date = result.get("start_date")
    end_date = result.get("end_date")
    leave_type = result.get("leave_type")

    if "sick" in msg_lower:
        leave_type = "sick"
    elif "earned" in msg_lower:
        leave_type = "earned"
    elif "casual" in msg_lower:
        leave_type = "casual"
    
    dates = []

    if start_date is None or end_date is None:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", message)

    

    if len(dates) >= 2:
        start_date = dates[0]
        end_date = dates[1]


        # ✅ Natural date fallback: tomorrow, today, next Monday
    if start_date is None or end_date is None:
        parsed_date = None

        if "tomorrow" in msg_lower:
            parsed_date = date.today() + timedelta(days=1)
        elif "today" in msg_lower:
            parsed_date = date.today()
        else:
            parsed = dateparser.parse(message)
            if parsed:
                parsed_date = parsed.date()

        if parsed_date:
            start_date = parsed_date
            end_date = parsed_date

    # 🧠 Debug (keep for now)
    print("HR AGENT:", intent, start_date, end_date)
    print("EXTRACT RESULT:", result)

    msg_lower = message.lower()

    if "apply" in msg_lower or "take leave" in msg_lower:
        intent = "apply_leave"
    
    # ✅ Apply Leave
    if intent == "apply_leave":
        if start_date is None or end_date is None:
            return "Please provide leave dates like: 2026-05-10 to 2026-05-12"

        leave = apply_leave(
            db=db,
            employee_id=user.id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
        )

        # ✅ Send email to manager after leave is created
        manager = db.query(Employee).filter(
            Employee.id == user.manager_id
        ).first()

        if manager:
            send_email(
                to=manager.email,
                subject="Leave Approval Required",
                body=(
                    f"Hello {manager.name},\n\n"
                    f"{user.name} has applied for {leave.leave_type} leave.\n\n"
                    f"Leave ID: #{leave.id}\n"
                    f"Dates: {leave.start_date} to {leave.end_date}\n"
                    f"Status: {leave.status}\n\n"
                    f"Please login to the AI Copilot and approve or reject this leave.\n\n"
                    f"Example commands:\n"
                    f"approve leave {leave.id}\n"
                    f"reject leave {leave.id}"
                )
            )
        else:
            print("No manager assigned for this employee")

        return (
            f"✅ {leave.leave_type.capitalize()} leave applied.\n"
            f"Leave ID: #{leave.id}\n"
            f"Dates: {leave.start_date} to {leave.end_date}\n"
            f"Status: {leave.status}\n"
            f"Manager has been notified."
        )
    
    # ✅ Leave History
    if "history" in msg_lower or "my leaves" in msg_lower:
        leaves = get_leave_history(db, user.id)
    
        if not leaves:
            return "No leave history found."
    
        return "\n".join([
            f"{l.start_date} to {l.end_date} → {l.status}"
            for l in leaves
        ])
        # ✅ Leave Balance
    if "balance" in msg_lower:
        balance = get_leave_balance(db, user.id)

        return (
            f"Leave Balance:\n"
            f"Total: {balance['total']} days\n"
            f"Used: {balance['used']} days\n"
            f"Remaining: {balance['remaining']} days"
        )

    # ✅ Pending Leave Requests
    if "pending" in msg_lower:
        leaves = get_pending_leaves(db, user.id)

        if not leaves:
            return "You have no pending leave requests."

        return "\n".join([
            f"Leave #{l.id}: {l.start_date} to {l.end_date} → {l.status}"
            for l in leaves
        ])

    # ✅ Cancel Leave
    if "cancel" in msg_lower:
        match = re.search(r"\d+", message)
        leave_id = int(match.group()) if match else None

        if not leave_id:
            return "Please mention the leave request ID to cancel."

        cancelled = cancel_leave(db, user.id, leave_id)

        if cancelled is None:
            return f"Leave request #{leave_id} not found."

        if cancelled == "not_allowed":
            return "Only pending leave requests can be cancelled."

        return f"✅ Leave request #{cancelled.id} has been cancelled."
    
    # ✅ Check Leave Status
    if "status" in msg_lower and "leave" in msg_lower:
        leave_id = extract_leave_id(message)
    
        if not leave_id:
            return "Please provide leave ID. Example: status of leave 12"
    
        leave = db.query(LeaveRequest).filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.employee_id == user.id
        ).first()
    
        if not leave:
            return "Leave not found."
    
        return (
            f"Leave #{leave.id}\n"
            f"Type: {leave.leave_type}\n"
            f"Dates: {leave.start_date} to {leave.end_date}\n"
            f"Status: {leave.status}"
        )
    

        # ✅ RAG Policy / Document Q&A
    docs = retrieve_docs(message)

    if not docs:
        return "I could not find relevant policy information in the uploaded documents."

    context = "\n\n---\n\n".join(docs)

    llm = get_llm()

    prompt = f"""
You are an enterprise HR policy assistant.

You must answer using ONLY the provided document context.
Do not guess.
If the answer is not clearly available in the context, say:
"I could not find this information in the uploaded policy documents."

Document context:
{context}

User question:
{message}

Answer in a clear, professional way.
Mention the relevant policy points if available.
"""

    response = llm.invoke(prompt)
    return response.content
    

    # ❌ DO NOT call LLM here
    return "I can help with leave requests. Try: apply leave from YYYY-MM-DD to YYYY-MM-DD"
    
    