from app.services.ai_service import extract_intent_and_entities
from app.services.leave_service import apply_leave, get_leave_history
import re
from app.rag.retriever import retrieve_docs
from ai.groq_client import get_llm

def hr_agent(message: str, db):
    result = extract_intent_and_entities(message)
    
    
    intent = result.get("intent")
    start_date = result.get("start_date")
    end_date = result.get("end_date")
    
    if start_date is None or end_date is None:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", message)

    if len(dates) >= 2:
        start_date = dates[0]
        end_date = dates[1]

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
            employee_id="Graph_USER",
            start_date=start_date,
            end_date=end_date
        )
    
        return f"✅ Leave applied from {leave.start_date} to {leave.end_date}"
    
    # ✅ Leave History
    if "history" in msg_lower or "my leaves" in msg_lower:
        leaves = get_leave_history(db, "Graph_USER")
    
        if not leaves:
            return "No leave history found."
    
        return "\n".join([
            f"{l.start_date} to {l.end_date} → {l.status}"
            for l in leaves
        ])
    
    docs = retrieve_docs(message)

    if docs:
        context = "\n".join(docs)

    llm = get_llm()

    prompt = f"""

    You are an HR assistant.

    Answer the question using ONLY the context below.

    Context:
    {context}

    Question:
    {message}

    Give a clear and professional answer.
    """

    response = llm.invoke(prompt)
    return response.content
    

    

    # ❌ DO NOT call LLM here
    return "I can help with leave requests. Try: apply leave from YYYY-MM-DD to YYYY-MM-DD"
    
    