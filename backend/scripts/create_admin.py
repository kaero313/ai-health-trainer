"""로컬 개발용 admin 계정 생성 스크립트

사용법:
    docker compose exec backend python scripts/create_admin.py
    docker compose exec -e ADMIN_PASSWORD backend python scripts/create_admin.py

두 번째 형식은 호스트 셸의 ADMIN_PASSWORD 값을 그대로 넘긴다. 명령줄에 비밀번호를 직접 쓰면 셸 기록에 남는다.
ADMIN_EMAIL을 주지 않으면 admin@admin.com을 쓴다.
ADMIN_PASSWORD를 주지 않으면 무작위 비밀번호를 만들어 한 번만 출력한다.
같은 이메일의 계정이 이미 있으면 건너뛴다. 비밀번호를 바꾸려면 그 계정을 지우고 다시 만든다.
"""

import asyncio
import os
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.auth import PASSWORD_PATTERN_COMPILED

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@admin.com")


def _resolve_password() -> tuple[str, bool]:
    password = os.environ.get("ADMIN_PASSWORD")
    if password:
        if PASSWORD_PATTERN_COMPILED.fullmatch(password) is None:
            sys.exit("ADMIN_PASSWORD는 영문·숫자·특수문자를 포함한 8자 이상이어야 합니다.")
        return password, False
    # token_urlsafe에 특수문자가 없을 수 있어 규칙을 만족하는 접미사를 붙인다
    return f"{secrets.token_urlsafe(12)}Aa1!", True


async def create_admin() -> None:
    # 규칙 위반은 DB에 접속하기 전에 알린다
    password, generated = _resolve_password()
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
                password_hash=get_password_hash(password),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            if generated:
                print(f"Created admin user: {ADMIN_EMAIL} / {password}")
            else:
                print(f"Created admin user: {ADMIN_EMAIL} (password from ADMIN_PASSWORD)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
