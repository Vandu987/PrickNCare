"""Seed an initial Super Admin user.

Reads credentials from environment variables:
  - SEED_ADMIN_EMAIL    (default: admin@prickncare.com)
  - SEED_ADMIN_PHONE    (default: +910000000000)
  - SEED_ADMIN_PASSWORD (required)

Safe to run multiple times — exits without changes if the user already exists.

Usage (one-off, inside the container):
    SEED_ADMIN_PASSWORD='YourStrongPass' python -m scripts.seed_admin
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.database import close_db, get_session_factory
from app.models.users import User, UserRole


async def seed() -> int:
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@prickncare.com").strip().lower()
    phone = os.environ.get("SEED_ADMIN_PHONE", "+910000000000").strip()
    password = os.environ.get("SEED_ADMIN_PASSWORD")

    if not password:
        print("ERROR: SEED_ADMIN_PASSWORD env var is required.", file=sys.stderr)
        return 2

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Admin user already exists: {email} — no changes.")
            return 0

        user = User(
            email=email,
            phone=phone,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        user.set_password(password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Created super admin: {email} (id={user.id})")
        return 0


async def main() -> int:
    try:
        return await seed()
    finally:
        await close_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
