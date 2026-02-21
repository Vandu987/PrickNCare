"""Order schemas — task 6.1."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class OrderCreate(BaseModel):
    client_id: uuid.UUID
    patient_title: str
    patient_name: str
    patient_age: int
    patient_gender: str
    patient_phone: str
    appointment_date: date
    appointment_time_slot: str
    address: str
    landmark: str | None = None
    pincode: str
    locality_id: uuid.UUID | None = None
    package_ids: list[uuid.UUID] | None = None
    priority: str = "normal"
    special_instructions: str | None = None
    payment_mode: str = "cash"

    @field_validator("patient_age")
    @classmethod
    def age_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("patient_age must be greater than 0")
        return v

    @field_validator("patient_gender")
    @classmethod
    def gender_valid(cls, v: str) -> str:
        if v not in ("M", "F", "O"):
            raise ValueError("patient_gender must be M, F, or O")
        return v

    @field_validator("pincode")
    @classmethod
    def pincode_six_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("pincode must be exactly 6 digits")
        return v

    @field_validator("appointment_date")
    @classmethod
    def date_not_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("appointment_date cannot be in the past")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str) -> str:
        if v not in ("normal", "high"):
            raise ValueError("priority must be normal or high")
        return v

    @field_validator("payment_mode")
    @classmethod
    def payment_mode_valid(cls, v: str) -> str:
        if v not in ("cash", "online", "prepaid"):
            raise ValueError("payment_mode must be cash, online, or prepaid")
        return v


class OrderStatusUpdate(BaseModel):
    status: str
    reason: str | None = None


class StatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    notes: str | None = None
    changed_by: uuid.UUID | None = None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: str
    client_id: uuid.UUID
    pincode_id: uuid.UUID
    locality_id: uuid.UUID | None = None
    patient_title: str
    patient_name: str
    patient_age: int
    patient_gender: str
    patient_phone: str
    appointment_date: date
    appointment_time_slot: str
    address: str
    landmark: str | None = None
    status: str
    priority: str
    special_instructions: str | None = None
    amount: float
    payment_mode: str
    payment_status: str
    assigned_phlebotomist_id: uuid.UUID | None = None
    created_at: datetime


class OrderDetailResponse(OrderResponse):
    status_history: list[StatusHistoryResponse] = []


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
