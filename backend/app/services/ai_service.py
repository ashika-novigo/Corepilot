import json
from ai.groq_client import get_llm

def extract_intent_and_entities(message: str):
    llm = get_llm()
    
    
    prompt = f"""
You are an AI assistant for an HR system.

Your job is to extract intent and leave dates.

Rules:

* If user mentions leave, vacation, or time off → intent MUST be "apply_leave"
* Even if phrasing is natural (e.g., "I need leave", "I want off", etc.)
* If no leave intent → return "other"

Return ONLY valid JSON:

{{
"intent": "apply_leave" or "other",
"start_date": "YYYY-MM-DD" or null,
"end_date": "YYYY-MM-DD" or null
}}

Examples:

Message: apply leave from 2026-05-10 to 2026-05-12
Output:
{{"intent":"apply_leave","start_date":"2026-05-10","end_date":"2026-05-12"}}

Message: I need leave tomorrow
Output:
{{"intent":"apply_leave","start_date":null,"end_date":null}}

Message: what is AI
Output:
{{"intent":"other","start_date":null,"end_date":null}}

Message:
{message}
"""

    
    
    response = llm.invoke(prompt)
    
    try:
        data = json.loads(response.content)
        # ✅ Fix "null" string issue 
        start_date = data.get("start_date") 
        end_date = data.get("end_date") 
        if start_date == "null": 
            start_date = None 
        if end_date == "null": 
            end_date = None
        return data
    except:
        return {
            "intent": "other",
            "start_date": None,
            "end_date": None
        }
    
    