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


def route_query(message: str):
    llm = get_llm()

    prompt = f"""
You are a strict routing agent.

Classify the user query into EXACTLY one category:

* "hr" → ANY leave request, leave application, leave dates, leave history, vacation, time off
* "it" → ANY technical issue including laptop issues, password reset, wifi/network issues, system errors, login problems, ticket creation, ticket status, asset request, asset request status/history, monitor, keyboard, mouse, vpn token, software license
* "finance" → salary, expenses, reimbursements
* "general" → anything else

IMPORTANT:

* If the message contains dates and words like leave, vacation, time off → ALWAYS return "hr"
* Be strict. Do NOT return "general" for leave-related queries.
* If message contains "asset", "monitor", "keyboard", "mouse", "vpn token", or "software license" → ALWAYS return "it"
* If message contains "ticket" → ALWAYS return "it"

Return ONLY JSON:
{{
"agent": "hr" or "it" or "finance" or "general"
}}

Message:
{message}
"""

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        cleaned = _clean_json(raw)
        data = json.loads(cleaned)
        return data.get("agent", "general")

    except Exception as e:
        print(f"[router_agent] routing failed: {e}")
        return "general"