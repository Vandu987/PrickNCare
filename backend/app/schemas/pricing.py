"""Pricing schemas — task 7.3."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class Priority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class PricingRequest(BaseModel):
    client_id: uuid.UUID
    package_ids: list[uuid.UUID] = Field(..., min_length=1)
    priority: Priority = Priority.NORMAL


class PackageLineItem(BaseModel):
    package_id: uuid.UUID
    package_name: str
    package_code: str
    fee: float


class PricingBreakdown(BaseModel):
    packages: list[PackageLineItem]
    first_collection_fee: float
    additional_collection_fees: float
    priority_fee: float
    total: float
