from models.asset_request import AssetRequest
from app.services.inventory_service import reserve_inventory
from app.services.email_service import send_email
from models.employee import Employee

def create_asset_request(db, user_id: str, asset_type: str, reason: str | None = None):
    request = AssetRequest(
        user_id=user_id,
        asset_type=asset_type,
        reason=reason,
        manager_status="pending",
        it_status="pending",
        inventory_status="pending",
        final_status="pending"
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


def get_asset_requests(db, user_id: str):
    return db.query(AssetRequest).filter(
        AssetRequest.user_id == user_id
    ).all()




def get_pending_asset_requests_for_manager(db, manager_id):
    from models.employee import Employee

    return db.query(AssetRequest).join(
        Employee,
        AssetRequest.user_id == Employee.email
    ).filter(
        Employee.manager_id == manager_id,
        AssetRequest.manager_status == "pending"
    ).all()


def approve_asset_by_manager(db, request_id, manager_id):
    from models.employee import Employee

    request = db.query(AssetRequest).join(
        Employee,
        AssetRequest.user_id == Employee.email
    ).filter(
        AssetRequest.id == request_id,
        Employee.manager_id == manager_id,
        AssetRequest.manager_status == "pending"
    ).first()

    if not request:
        return None

    request.manager_status = "approved"
    request.final_status = "pending_it_approval"

    db.commit()
    db.refresh(request)

    send_email(
    to="ashika.shridhar@novigosolutions.com",
    subject="Asset Request Pending IT Approval",
    body=(
        f"Hello IT Team,\n\n"
        f"An asset request has been approved by the manager.\n\n"
        f"Request ID: #{request.id}\n"
        f"Asset: {request.asset_type}\n"
        f"Employee: {request.user_id}\n\n"
        f"Please login to Corepilot and approve/reject.\n\n"
        f"Commands:\n"
        f"it approve asset {request.id}\n"
        f"it reject asset {request.id}"
    )
)

    return request


def reject_asset_by_manager(db, request_id, manager_id):
    from models.employee import Employee

    request = db.query(AssetRequest).join(
        Employee,
        AssetRequest.user_id == Employee.email
    ).filter(
        AssetRequest.id == request_id,
        Employee.manager_id == manager_id,
        AssetRequest.manager_status == "pending"
    ).first()

    if not request:
        return None

    request.manager_status = "rejected"
    request.final_status = "rejected"

    db.commit()
    db.refresh(request)

    return request


def get_pending_assets_for_it(db):
    return db.query(AssetRequest).filter(
        AssetRequest.manager_status == "approved",
        AssetRequest.it_status == "pending"
    ).all()


def approve_asset_by_it(db, request_id):
    request = db.query(AssetRequest).filter(
        AssetRequest.id == request_id,
        AssetRequest.manager_status == "approved",
        AssetRequest.it_status == "pending"
    ).first()

    if not request:
        return None

    inventory = reserve_inventory(db, request.asset_type)

    if inventory is None:
        request.it_status = "rejected"
        request.inventory_status = "not_found"
        request.final_status = "rejected"

        db.commit()
        db.refresh(request)

        return "inventory_not_found"

    if inventory == "unavailable":
        request.it_status = "approved"
        request.inventory_status = "unavailable"
        request.final_status = "waiting_for_stock"

        db.commit()
        db.refresh(request)

        return "inventory_unavailable"

    request.it_status = "approved"
    request.inventory_status = "available"
    request.final_status = "fulfilled"

    db.commit()
    db.refresh(request)

    employee = db.query(Employee).filter(
        Employee.email == request.user_id
    ).first()

    if employee:
        send_email(
            to=employee.email,
            subject="Asset Request Fulfilled",
            body=(
                f"Hello {employee.name},\n\n"
                f"Your asset request has been fulfilled.\n\n"
                f"Request ID: #{request.id}\n"
                f"Asset: {request.asset_type}\n"
                f"Final Status: {request.final_status}\n\n"
                f"Please contact IT for collection."
            )
        )

    return request

def reject_asset_by_it(db, request_id):
    request = db.query(AssetRequest).filter(
        AssetRequest.id == request_id,
        AssetRequest.manager_status == "approved",
        AssetRequest.it_status == "pending"
    ).first()

    if not request:
        return None

    request.it_status = "rejected"
    request.final_status = "rejected"

    db.commit()
    db.refresh(request)

    return request