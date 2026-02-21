"""Pricing engine service — task 7.3."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clients import Client
from app.models.packages import Package
from app.schemas.pricing import (
    PackageLineItem,
    PricingBreakdown,
    Priority,
)


class PricingEngine:
    """Calculate order amounts based on client-specific rates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_order_amount(
        self,
        client_id: uuid.UUID,
        package_ids: list[uuid.UUID],
        priority: Priority = Priority.NORMAL,
    ) -> PricingBreakdown:
        """Return a full pricing breakdown for the given packages and client.

        Raises:
            HTTPException 404: client not found.
            HTTPException 400: empty package_ids list.
            HTTPException 422: invalid priority value.
        """
        # --- Validate inputs ------------------------------------------------
        if not package_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="package_ids must not be empty",
            )

        if not isinstance(priority, Priority):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid priority value: {priority}",
            )

        # --- Fetch client ---------------------------------------------------
        result = await self.db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found",
            )

        # --- Fetch packages -------------------------------------------------
        result = await self.db.execute(
            select(Package).where(Package.id.in_(package_ids))
        )
        packages = result.scalars().all()

        found_ids = {p.id for p in packages}
        missing = set(package_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Packages not found: {[str(m) for m in missing]}",
            )

        # --- Build pricing breakdown ----------------------------------------
        rate_first = float(client.rate_first_collection)
        rate_second = float(client.rate_second_collection)
        rate_priority = float(client.rate_priority)

        # Map packages in the order requested
        pkg_map = {p.id: p for p in packages}
        line_items: list[PackageLineItem] = []
        for idx, pid in enumerate(package_ids):
            pkg = pkg_map[pid]
            fee = rate_first if idx == 0 else rate_second
            line_items.append(
                PackageLineItem(
                    package_id=pkg.id,
                    package_name=pkg.name,
                    package_code=pkg.code,
                    fee=fee,
                )
            )

        first_collection_fee = rate_first
        additional_collection_fees = rate_second * max(0, len(package_ids) - 1)
        priority_fee = rate_priority if priority == Priority.HIGH else 0.0
        total = first_collection_fee + additional_collection_fees + priority_fee

        return PricingBreakdown(
            packages=line_items,
            first_collection_fee=first_collection_fee,
            additional_collection_fees=additional_collection_fees,
            priority_fee=priority_fee,
            total=total,
        )
