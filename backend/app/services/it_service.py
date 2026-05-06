from datetime import datetime, timezone

from models.ticket import Ticket


OPEN_STATUSES = ["open", "in_progress"]
ALLOWED_TICKET_STATUSES = ["open", "in_progress", "resolved", "closed", "rejected"]


def check_duplicate_ticket(db, user_id: str, issue_type: str):
    return db.query(Ticket).filter(
        Ticket.user_id == user_id,
        Ticket.issue_type == issue_type,
        Ticket.status.in_(OPEN_STATUSES)
    ).first()


def create_ticket(
    db,
    user_id: str,
    issue_type: str,
    description: str,
    priority: str = "medium"
):
    duplicate = check_duplicate_ticket(db, user_id, issue_type)

    if duplicate:
        return None, duplicate

    ticket = Ticket(
        user_id=user_id,
        issue_type=issue_type,
        description=description,
        priority=priority,
        status="open"
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket, None


def get_user_tickets(db, user_id: str):
    return db.query(Ticket).filter(
        Ticket.user_id == user_id
    ).all()


def get_all_tickets(db):
    return db.query(Ticket).all()


def get_open_tickets(db):
    return db.query(Ticket).filter(
        Ticket.status.in_(OPEN_STATUSES)
    ).all()


def get_tickets_by_status(db, status: str):
    return db.query(Ticket).filter(
        Ticket.status == status
    ).all()


def update_ticket_status(db, ticket_id: int, status: str):
    if status not in ALLOWED_TICKET_STATUSES:
        raise ValueError(f"Unsupported ticket status: {status}")

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()


    if not ticket:
        return None

    ticket.status = status
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)

    return ticket



