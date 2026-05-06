import json
import re
from ai.groq_client import get_llm


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def extract_intent_and_entities(message: str):
    llm = get_llm()

    prompt = f"""
You are an AI assistant for an HR system.

Extract intent, leave type, and dates from the user message.

Return ONLY valid JSON:

{{
  "intent": "apply_leave" or "other",
  "leave_type": "casual" or "sick" or "earned" or "other",
  "start_date": "YYYY-MM-DD" or null,
  "end_date": "YYYY-MM-DD" or null
}}

Examples:

Message: apply sick leave tomorrow
Output:
{{"intent":"apply_leave","leave_type":"sick","start_date":null,"end_date":null}}

Message: apply casual leave from 2026-05-10 to 2026-05-12
Output:
{{"intent":"apply_leave","leave_type":"casual","start_date":"2026-05-10","end_date":"2026-05-12"}}

Message: what is leave policy
Output:
{{"intent":"other","leave_type":"other","start_date":null,"end_date":null}}

Message:
{message}
"""

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        cleaned = _clean_json(raw)
        data = json.loads(cleaned)

        start_date = data.get("start_date")
        end_date   = data.get("end_date")

        # Groq sometimes returns the string "null" instead of JSON null
        if start_date == "null":
            start_date = None
        if end_date == "null":
            end_date = None

        return {
            "intent":     data.get("intent", "other"),
            "leave_type": data.get("leave_type", "casual"),
            "start_date": start_date,
            "end_date":   end_date,
        }

    except Exception as e:
        print(f"[ai_service] extract_intent_and_entities failed: {e}")
        return {
            "intent":     "other",
            "leave_type": "casual",
            "start_date": None,
            "end_date":   None,
        }