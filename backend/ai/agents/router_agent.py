import json
from ai.groq_client import get_llm

def route_query(message: str):
    llm = get_llm()


    prompt = f"""
You are a strict routing agent.

Classify the user query into EXACTLY one category:

* "hr" → ANY leave request, leave application, leave dates, leave history, vacation, time off
* "it" → ANY technical issue including laptop issues, password reset, wifi/network issues, system errors, login problems, ticket creation, ticket status,  asset request, asset request status/history, monitor, keyboard, mouse, vpn token, software license
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



    response = llm.invoke(prompt)

    try:
        raw = response.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]

        data = json.loads(raw)
        return data.get("agent", "general")

    except:
        return "general"

