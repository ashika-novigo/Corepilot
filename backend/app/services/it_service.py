from models.ticket import Ticket


OPEN_STATUSES = ["open", "in_progress"]


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


def update_ticket_status(db, ticket_id: int, status: str):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()


    if not ticket:
        return None

    ticket.status = status
    db.commit()
    db.refresh(ticket)

    return ticket

