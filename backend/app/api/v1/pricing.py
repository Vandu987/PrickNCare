"""Pricing calculation endpoint — task 7.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.clients import Client
from app.models.packages import Package
from app.models.users import User
from app.schemas.pricing import PricingBreakdown, PricingRequest
from app.services.pricing import PricingEngine

router = APIRouter(prefix="/pricing", tags=["pricing"])

_allowed = require_roles("client_user", "city_admin", "super_admin")


@router.post("/calculate", response_model=PricingBreakdown)
async def calculate_pricing(
    body: PricingRequest,
    user: User = Depends(_allowed),
    db: AsyncSession = Depends(get_db),
) -> PricingBreakdown:
    """Calculate real-time pricing quote for a set of packages."""

    # Validate client exists and is active
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {body.client_id} not found",
        )
    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client {body.client_id} is not active",
        )

    # Validate all packages exist and are active
    result = await db.execute(select(Package).where(Package.id.in_(body.package_ids)))
    packages = result.scalars().all()

    found_ids = {p.id for p in packages}
    missing = set(body.package_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Packages not found: {[str(m) for m in missing]}",
        )

    inactive = [p for p in packages if not p.is_active]
    if inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inactive packages: {[str(p.id) for p in inactive]}",
        )

    # Delegate to pricing engine
    engine = PricingEngine(db)
    return await engine.calculate_order_amount(
        client_id=body.client_id,
        package_ids=body.package_ids,
        priority=body.priority,
    )
