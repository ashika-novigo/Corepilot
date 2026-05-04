from models.asset_request import AssetRequest


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