from ai.groq_client import get_llm
from app.services.it_service import create_ticket, get_user_tickets
from app.services.it_service import update_ticket_status
from app.services.asset_service import create_asset_request, get_asset_requests

import json
import re

# 🧠 AI extraction

def extract_it_details(message: str):
    llm = get_llm()

    prompt = f"""


    You are an IT assistant.

    Extract details from the user message.

    Return ONLY valid JSON:

    {{
    "issue_type": "laptop | vpn | outlook | printer | network | software | general",
    "priority": "low | medium | high | critical"
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

        return {
            "issue_type": data.get("issue_type", "general"),
            "priority": data.get("priority", "medium")
        }

    except:
        return {
            "issue_type": "general",
            "priority": "medium"
        }


# 🔁 Rule fallback (safety)

def detect_issue_type(message: str) -> str:
    msg = message.lower()


    if "laptop" in msg or "system" in msg:
        return "laptop"
    if "vpn" in msg:
        return "vpn"
    if "outlook" in msg or "email" in msg:
        return "outlook"
    if "printer" in msg:
        return "printer"
    if "wifi" in msg or "network" in msg:
        return "network"
    if "software" in msg or "install" in msg:
        return "software"

    return "general"


def detect_priority(message: str) -> str:
    msg = message.lower()


    if "urgent" in msg or "critical" in msg or "blocked" in msg:
        return "critical"
    if "not working" in msg or "unable" in msg:
        return "high"

    return "medium"


def extract_ticket_update(message: str):
    msg = message.lower()

    # extract ticket id
    match = re.search(r"\d+", msg)
    ticket_id = int(match.group()) if match else None

    # detect status
    if "resolved" in msg or "close" in msg:
        status = "resolved"
    elif "progress" in msg:
        status = "in_progress"
    else:
        status = None

    return ticket_id, status



    # 🚀 Final IT Agent

def it_agent(message: str, db):
    msg = message.lower()

    # 🔹 Ticket status
    if "ticket" in msg and ("status" in msg or "history" in msg or "my tickets" in msg):
        tickets = get_user_tickets(db, "AI_USER")

        if not tickets:
            return "No IT tickets found."

        return "\n".join([
            f"Ticket #{t.id}: {t.issue_type} → {t.status}"
            for t in tickets
        ])

    # 🔥 Ticket update (FIXED)
    if "ticket" in msg and ("resolve" in msg or "close" in msg or "progress" in msg):

        ticket_id, status = extract_ticket_update(message)

        if not ticket_id or not status:
            return "Please specify ticket ID and status clearly."

        ticket = update_ticket_status(db, ticket_id, status)

        if not ticket:
            return f"Ticket #{ticket_id} not found."

        return f"✅ Ticket #{ticket.id} updated to {ticket.status}"



        # 🔹 Asset request status/history
    if "asset" in msg and ("status" in msg or "history" in msg):
        requests = get_asset_requests(db, "AI_USER")

        if not requests:
            return "No asset requests found."

        return "\n".join([
            f"Asset Request #{r.id}: {r.asset_type} → {r.final_status}"
            for r in requests
        ])

    # 🔹 Create asset request
    asset_keywords = ["monitor", "keyboard", "mouse", "vpn token", "software license", "laptop"]

    if any(asset in msg for asset in asset_keywords):
        asset_type = "general"

        for asset in asset_keywords:
            if asset in msg:
                asset_type = asset
                break

        request = create_asset_request(
            db=db,
            user_id="AI_USER",
            asset_type=asset_type,
            reason=message
        )

        return (
            f"🧾 Asset request created successfully.\n"
            f"Request ID: #{request.id}\n"
            f"Asset: {request.asset_type}\n"
            f"Manager Approval: {request.manager_status}\n"
            f"IT Approval: {request.it_status}\n"
            f"Final Status: {request.final_status}"
        )

    # 🧠 Step 1: AI extraction
    details = extract_it_details(message)

    issue_type = details["issue_type"]
    priority = details["priority"]

    # 🔥 Step 2: fallback if AI fails
    if issue_type == "general":
        issue_type = detect_issue_type(message)

    if priority == "medium":
        priority = detect_priority(message)

    # 🔹 Step 3: create ticket
    if issue_type != "general":

        ticket, duplicate = create_ticket(
            db=db,
            user_id="AI_USER",
            issue_type=issue_type,
            description=message,
            priority=priority
        )

        if duplicate:
            return (
                f"You already have an open {duplicate.issue_type} ticket "
                f"(Ticket #{duplicate.id}). Current status: {duplicate.status}."
            )

        return (
            f"🛠️ IT ticket created successfully.\n"
            f"Ticket ID: #{ticket.id}\n"
            f"Issue Type: {ticket.issue_type}\n"
            f"Priority: {ticket.priority}\n"
            f"Status: {ticket.status}"
        )
    
    # 🤖 Step 4: fallback LLM
    llm = get_llm()
    response = llm.invoke(f"Help with this IT support issue: {message}")

    return response.content

