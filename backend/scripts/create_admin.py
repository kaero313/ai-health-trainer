"""Admin 테스트 계정 생성 스크립트

사용법:
    docker compose exec backend python scripts/create_admin.py
"""

import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Admin@12345678"


async def create_admin() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.email == ADMIN_EMAIL)
            )
            if result.scalar_one_or_none():
                print(f"User '{ADMIN_EMAIL}' already exists. Skipping.")
                return

            user = User(
                email=ADMIN_EMAIL,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print(f"Created admin user: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
