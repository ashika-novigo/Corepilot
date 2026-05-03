from app.services.ai_service import extract_intent_and_entities
from app.services.leave_service import apply_leave, get_leave_history

def hr_agent(message: str, db):
    result = extract_intent_and_entities(message)
    
    
    intent = result.get("intent")
    start_date = result.get("start_date")
    end_date = result.get("end_date")
    
    # 🧠 Debug (keep for now)
    print("HR AGENT:", intent, start_date, end_date)
    
    # ✅ Apply Leave
    if intent == "apply_leave":
        if start_date is None or end_date is None:
            return "Please provide leave dates like: 2026-05-10 to 2026-05-12"
    
        leave = apply_leave(
            db=db,
            employee_id="AI_USER",
            start_date=start_date,
            end_date=end_date
        )
    
        return f"✅ Leave applied from {leave.start_date} to {leave.end_date}"
    
    # ✅ Leave History
    if "history" in message.lower():
        leaves = get_leave_history(db, "AI_USER")
    
        if not leaves:
            return "No leave history found."
    
        return "\n".join([
            f"{l.start_date} to {l.end_date} → {l.status}"
            for l in leaves
        ])
    
    # ❌ DO NOT call LLM here
    return "I can help with leave requests. Try: apply leave from YYYY-MM-DD to YYYY-MM-DD"
    
    