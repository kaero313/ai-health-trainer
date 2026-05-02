"""RAG 데이터 초기화 스크립트

사용법:
    docker compose exec backend python scripts/reset_rag_data.py
"""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings


async def reset_rag_data() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT count(*) FROM rag_chunks"))
            count = result.scalar_one()
            print(f"현재 rag_chunks 레코드 수: {count}")

            if count > 0:
                await session.execute(text("DELETE FROM ai_generation_traces"))
                await session.execute(text("DELETE FROM rag_retrieval_traces"))
                await session.execute(text("DELETE FROM rag_pipeline_decisions"))
                await session.execute(text("DELETE FROM rag_ingest_jobs"))
                await session.execute(text("DELETE FROM rag_chunks"))
                await session.execute(text("DELETE FROM rag_embedding_cache"))
                await session.execute(text("DELETE FROM rag_sources"))
                await session.commit()
                print(f"삭제 완료: {count}개 chunk와 관련 RAG 운영 레코드")
            else:
                print("삭제할 데이터가 없습니다.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_rag_data())
