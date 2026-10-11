"""Alembic 마이그레이션 계약 테스트.

계약:
1. 빈 PostgreSQL DB에서 `alembic upgrade head`가 성공한다.
2. head에서 `alembic check`가 모델과 스키마의 차이를 보고하지 않는다(종료 코드 0).
3. `alembic downgrade base`가 성공하고, 그 뒤 public 스키마에 애플리케이션 테이블
   (alembic_version 제외)과 사용자 정의 enum 타입이 남지 않는다. pgvector 확장은 남아도 된다.
4. 다시 `alembic upgrade head`가 성공하고 `alembic check`가 다시 차이를 보고하지 않는다.

안전:
- 개발 DB(health_trainer)나 일반 테스트 DB(health_trainer_test)를 건드리지 않는다.
  이름이 `_migration_test`로 끝나는 전용 DB를 만들고, 실패해도 마지막에 지운다.
- alembic/env.py는 get_settings().DATABASE_URL을 쓰므로, 테스트 프로세스의 캐시된
  설정을 재사용하지 않도록 alembic을 하위 프로세스에서 DATABASE_URL만 바꿔 실행한다.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  # create_all이 모든 모델 테이블을 만들도록 등록한다
from app.core.database import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_DB_SUFFIX = "_migration_test"
MIGRATION_DB_NAME = f"health_trainer{MIGRATION_DB_SUFFIX}"
ADMIN_DATABASE_URL = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
)
ALEMBIC_TIMEOUT_SECONDS = 300
OUTPUT_TAIL_CHARS = 3000


def _migration_database_url() -> str:
    """관리 DB URL에서 데이터베이스 이름만 전용 DB 이름으로 바꾼다."""
    url = make_url(ADMIN_DATABASE_URL).set(database=MIGRATION_DB_NAME)
    return url.render_as_string(hide_password=False)


def _assert_dedicated_database(url: str) -> None:
    name = make_url(url).database or ""
    assert name.endswith(MIGRATION_DB_SUFFIX), (
        f"마이그레이션 테스트는 '{MIGRATION_DB_SUFFIX}'로 끝나는 전용 DB에서만 돈다: {name!r}"
    )
    assert name not in {"health_trainer", "health_trainer_test", "postgres"}, (
        f"개발·일반 테스트·관리 DB에는 마이그레이션을 돌리지 않는다: {name!r}"
    )


def _tail(value: str) -> str:
    return value[-OUTPUT_TAIL_CHARS:] if len(value) > OUTPUT_TAIL_CHARS else value


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    _assert_dedicated_database(database_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=ALEMBIC_TIMEOUT_SECONDS,
        check=False,
    )


def _describe(step: str, result: subprocess.CompletedProcess[str]) -> str:
    return (
        f"[{step}] alembic {' '.join(result.args[3:])} 종료 코드 {result.returncode}\n"
        f"--- stdout (tail) ---\n{_tail(result.stdout)}\n"
        f"--- stderr (tail) ---\n{_tail(result.stderr)}"
    )


async def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return await asyncio.to_thread(_run_alembic, database_url, *args)


async def _terminate_and_drop(conn, db_name: str) -> None:
    await conn.execute(
        text(
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname = :db_name AND pid <> pg_backend_pid()"
        ),
        {"db_name": db_name},
    )
    await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))


async def _create_migration_database() -> None:
    _assert_dedicated_database(_migration_database_url())
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await _terminate_and_drop(conn, MIGRATION_DB_NAME)
            await conn.execute(text(f'CREATE DATABASE "{MIGRATION_DB_NAME}"'))
    finally:
        await admin_engine.dispose()


async def _drop_migration_database() -> None:
    _assert_dedicated_database(_migration_database_url())
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await _terminate_and_drop(conn, MIGRATION_DB_NAME)
    finally:
        await admin_engine.dispose()


async def _leftover_schema_objects(database_url: str) -> tuple[list[str], list[str], str | None]:
    """public 스키마에 남은 테이블(alembic_version 제외), 사용자 정의 enum, 현재 리비전."""
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            tables = (
                await conn.execute(
                    text(
                        "SELECT c.relname FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
                        "AND c.relname <> 'alembic_version' "
                        "ORDER BY c.relname"
                    )
                )
            ).scalars().all()
            # 확장이 소유한 타입은 제외한다(pgvector는 남아도 된다)
            enums = (
                await conn.execute(
                    text(
                        "SELECT n.nspname || '.' || t.typname FROM pg_type t "
                        "JOIN pg_namespace n ON n.oid = t.typnamespace "
                        "WHERE t.typtype = 'e' "
                        "AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
                        "AND NOT EXISTS ("
                        "  SELECT 1 FROM pg_depend d "
                        "  WHERE d.classid = 'pg_type'::regclass "
                        "  AND d.objid = t.oid AND d.deptype = 'e'"
                        ") "
                        "ORDER BY 1"
                    )
                )
            ).scalars().all()
            has_version_table = (
                await conn.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
            ).scalar_one()
            revision = None
            if has_version_table:
                revision = (
                    await conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one_or_none()
            return list(tables), list(enums), revision
    finally:
        await engine.dispose()


async def _current_revision(database_url: str) -> str | None:
    _, _, revision = await _leftover_schema_objects(database_url)
    return revision


@pytest.mark.migration
@pytest.mark.asyncio(loop_scope="session")
async def test_alembic_upgrade_check_downgrade_roundtrip_on_empty_database() -> None:
    database_url = _migration_database_url()
    _assert_dedicated_database(database_url)

    await _create_migration_database()
    try:
        # 0. 선형 이력: head가 하나여야 upgrade head / downgrade base가 결정적이다
        heads = await _alembic(database_url, "heads")
        assert heads.returncode == 0, _describe("0. heads", heads)
        head_lines = [line for line in heads.stdout.splitlines() if line.strip()]
        assert len(head_lines) == 1, f"[0. heads] head가 하나가 아니다:\n{heads.stdout}"
        head_revision = head_lines[0].split()[0]

        # 1. 빈 DB에서 upgrade head
        upgrade = await _alembic(database_url, "upgrade", "head")
        assert upgrade.returncode == 0, _describe("1. 빈 DB upgrade head", upgrade)
        assert await _current_revision(database_url) == head_revision, (
            f"[1. 빈 DB upgrade head] alembic_version이 head({head_revision})가 아니다"
        )

        # 2. head에서 모델과 스키마 차이가 없어야 한다
        check = await _alembic(database_url, "check")
        assert check.returncode == 0, _describe("2. head에서 alembic check", check)

        # 3. downgrade base 뒤 애플리케이션 테이블·사용자 정의 enum이 남지 않는다
        downgrade = await _alembic(database_url, "downgrade", "base")
        assert downgrade.returncode == 0, _describe("3. downgrade base", downgrade)
        tables, enums, revision = await _leftover_schema_objects(database_url)
        assert tables == [], f"[3. downgrade base] public 스키마에 테이블이 남았다: {tables}"
        assert enums == [], f"[3. downgrade base] 사용자 정의 enum 타입이 남았다: {enums}"
        assert revision is None, f"[3. downgrade base] alembic_version에 리비전이 남았다: {revision}"

        # 4. 다시 upgrade head 후 check
        reupgrade = await _alembic(database_url, "upgrade", "head")
        assert reupgrade.returncode == 0, _describe("4. 재 upgrade head", reupgrade)
        assert await _current_revision(database_url) == head_revision, (
            f"[4. 재 upgrade head] alembic_version이 head({head_revision})가 아니다"
        )
        recheck = await _alembic(database_url, "check")
        assert recheck.returncode == 0, _describe("4. 재 upgrade 뒤 alembic check", recheck)
    finally:
        await _drop_migration_database()


# ── (a) CHECK 제약·enum 차이 검사 ─────────────────────────────────────────────
# 계약: `alembic upgrade head`로 만든 스키마와 모델(`Base.metadata.create_all`)로 만든 스키마는
# CHECK 제약 정의와 enum 라벨 목록이 같다. env.py의 compare_type·compare_server_default만으로는
# `alembic check`가 CHECK 제약과 enum 값을 비교하지 않으므로 카탈로그를 직접 비교한다.
# 제약 이름은 naming convention(ck_%(table_name)s_%(constraint_name)s) 때문에 양쪽이 다를 수 있어,
# 이름이 아니라 (테이블, 정규화한 정의)로 비교한다.

HEAD_DB_NAME = f"health_trainer_head{MIGRATION_DB_SUFFIX}"
MODELS_DB_NAME = f"health_trainer_models{MIGRATION_DB_SUFFIX}"
SEEDED_DB_NAME = f"health_trainer_seeded{MIGRATION_DB_SUFFIX}"

ROOT_REVISION = "265e405ccf13"
# rag_sources·rag_chunks·rag_ingest_jobs·rag_retrieval_traces·ai_generation_traces를 만드는 리비전.
# 다음 리비전(e6b1d2a3c4f5)부터 이 테이블들에 NOT NULL·CHECK 추가와 백필이 이어진다.
KNOWLEDGE_OPS_REVISION = "d4f2b8c9a731"
# rag_pipeline_decisions 원문 query를 지우는 a8192a3b4c5d의 직전 리비전
BEFORE_SCRUB_REVISION = "f708192a3b4c"

CheckKey = tuple[str, str]


def _database_url(db_name: str) -> str:
    url = make_url(ADMIN_DATABASE_URL).set(database=db_name)
    rendered = url.render_as_string(hide_password=False)
    _assert_dedicated_database(rendered)
    return rendered


@asynccontextmanager
async def _temporary_database(db_name: str) -> AsyncIterator[str]:
    """전용 임시 DB를 만들고 URL을 준다. 본문이 실패해도 마지막에 지운다."""
    database_url = _database_url(db_name)
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await _terminate_and_drop(conn, db_name)
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()
    try:
        yield database_url
    finally:
        admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
        try:
            async with admin_engine.connect() as conn:
                await _terminate_and_drop(conn, db_name)
        finally:
            await admin_engine.dispose()


def _normalize_check_definition(definition: str) -> str:
    """pg_get_constraintdef 결과의 공백 차이와 NOT VALID 표기를 없앤다."""
    normalized = re.sub(r"\s+", " ", definition).strip()
    normalized = re.sub(r"\s+NOT VALID$", "", normalized)
    return normalized


async def _check_constraints(database_url: str) -> Counter[CheckKey]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT c.relname, pg_get_constraintdef(con.oid) "
                        "FROM pg_constraint con "
                        "JOIN pg_class c ON c.oid = con.conrelid "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE con.contype = 'c' AND n.nspname = 'public'"
                    )
                )
            ).all()
    finally:
        await engine.dispose()
    return Counter((table, _normalize_check_definition(definition)) for table, definition in rows)


async def _enum_labels(database_url: str) -> dict[str, list[str]]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT t.typname, e.enumlabel FROM pg_type t "
                        "JOIN pg_namespace n ON n.oid = t.typnamespace "
                        "JOIN pg_enum e ON e.enumtypid = t.oid "
                        "WHERE n.nspname = 'public' "
                        "ORDER BY t.typname, e.enumsortorder"
                    )
                )
            ).all()
    finally:
        await engine.dispose()
    labels: dict[str, list[str]] = {}
    for type_name, label in rows:
        labels.setdefault(type_name, []).append(label)
    return labels


def _schema_constraint_diff(
    migration_checks: Counter[CheckKey],
    model_checks: Counter[CheckKey],
    migration_enums: dict[str, list[str]],
    model_enums: dict[str, list[str]],
) -> list[str]:
    """차이를 사람이 읽을 줄 목록으로 만든다. 빈 목록이면 차이가 없다."""
    lines: list[str] = []
    for side, only in (
        ("마이그레이션(upgrade head)에만", migration_checks - model_checks),
        ("모델(create_all)에만", model_checks - migration_checks),
    ):
        for (table, definition), count in sorted(only.items()):
            suffix = f" (x{count})" if count > 1 else ""
            lines.append(f"CHECK {side} 있음: {table}: {definition}{suffix}")
    for type_name in sorted(set(migration_enums) - set(model_enums)):
        lines.append(f"ENUM 마이그레이션(upgrade head)에만 있음: {type_name} {migration_enums[type_name]}")
    for type_name in sorted(set(model_enums) - set(migration_enums)):
        lines.append(f"ENUM 모델(create_all)에만 있음: {type_name} {model_enums[type_name]}")
    for type_name in sorted(set(migration_enums) & set(model_enums)):
        if migration_enums[type_name] != model_enums[type_name]:
            lines.append(
                f"ENUM 라벨 불일치: {type_name} "
                f"마이그레이션={migration_enums[type_name]} 모델={model_enums[type_name]}"
            )
    return lines


@pytest.mark.migration
def test_schema_constraint_diff_reports_each_side_and_ignores_whitespace() -> None:
    """비교기가 한쪽에만 있는 CHECK·enum과 라벨 순서 차이를 잡고, 공백 차이는 무시한다."""
    same = ("users", _normalize_check_definition("CHECK ((age >= 0))"))
    migration_checks = Counter(
        [same, ("ai_generation_traces", "CHECK (((status)::text = ANY (ARRAY['a'::text])))")]
    )
    model_checks = Counter(
        [
            ("users", _normalize_check_definition("CHECK  ((age >= 0))\n")),
            ("rag_chunks", "CHECK ((version > 0))"),
        ]
    )
    diff = _schema_constraint_diff(
        migration_checks,
        model_checks,
        {"goal_enum": ["bulk", "diet"], "old_enum": ["x"]},
        {"goal_enum": ["diet", "bulk"], "new_enum": ["y"]},
    )
    assert diff == [
        "CHECK 마이그레이션(upgrade head)에만 있음: ai_generation_traces: "
        "CHECK (((status)::text = ANY (ARRAY['a'::text])))",
        "CHECK 모델(create_all)에만 있음: rag_chunks: CHECK ((version > 0))",
        "ENUM 마이그레이션(upgrade head)에만 있음: old_enum ['x']",
        "ENUM 모델(create_all)에만 있음: new_enum ['y']",
        "ENUM 라벨 불일치: goal_enum 마이그레이션=['bulk', 'diet'] 모델=['diet', 'bulk']",
    ]
    assert _schema_constraint_diff(Counter([same]), Counter([same]), {}, {}) == []


@pytest.mark.migration
@pytest.mark.asyncio(loop_scope="session")
async def test_upgrade_head_check_constraints_and_enums_match_models() -> None:
    async with _temporary_database(HEAD_DB_NAME) as head_url, _temporary_database(
        MODELS_DB_NAME
    ) as models_url:
        upgrade = await _alembic(head_url, "upgrade", "head")
        assert upgrade.returncode == 0, _describe("upgrade head", upgrade)

        models_engine = create_async_engine(models_url)
        try:
            async with models_engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.run_sync(Base.metadata.create_all)
        finally:
            await models_engine.dispose()

        migration_checks = await _check_constraints(head_url)
        model_checks = await _check_constraints(models_url)
        migration_enums = await _enum_labels(head_url)
        model_enums = await _enum_labels(models_url)

        # 조회가 비어서 비교가 공허하게 통과하지 않도록 최소 개수를 확인한다
        assert migration_checks, "upgrade head DB에서 CHECK 제약을 하나도 읽지 못했다"
        assert model_checks, "create_all DB에서 CHECK 제약을 하나도 읽지 못했다"
        assert len(migration_enums) >= 6, f"upgrade head DB enum이 너무 적다: {migration_enums}"
        assert len(model_enums) >= 6, f"create_all DB enum이 너무 적다: {model_enums}"

        diff = _schema_constraint_diff(migration_checks, model_checks, migration_enums, model_enums)
        assert diff == [], "마이그레이션과 모델의 CHECK·enum이 다르다:\n" + "\n".join(diff)


# ── (b) 데이터가 있는 DB의 upgrade 검사 ──────────────────────────────────────
# 계약: 이전 리비전에서 쌓인 행이 있어도 `alembic upgrade head`가 성공하고 행이 남는다.
# NOT NULL·CHECK 추가와 백필은 기존 행에 적용되므로, 해당 테이블이 생긴 시점과
# 원문을 지우는 리비전 직전에 대표 행을 넣는다.
# 개인정보 계약(docs/RAG_TRACE_PRIVACY.md "Legacy Redaction"):
# - e6f708192a3b: 기존 검색 원문은 legacy 지문·요약으로 바뀌고 query_text는 NULL이 된다.
# - a8192a3b4c5d: 결정 JSON의 query 사본과 채팅 context_summary의 원문이 지워진다.

RAW_RETRIEVAL_QUERY = "무릎 통증이 있는데 스쿼트 해도 되나요 legacy-raw-retrieval"
RAW_DECISION_QUERY = "당뇨 전단계 식단 추천 legacy-raw-decision"
RAW_CHAT_TEXT = "요즘 불면증이 심해요 legacy-raw-chat"
EMBEDDING_LITERAL = "[" + ",".join(["0.01"] * 3072) + "]"


async def _execute_all(database_url: str, statements: list[tuple[str, dict]]) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            for sql, params in statements:
                await conn.execute(text(sql), params)
    finally:
        await engine.dispose()


async def _seed_root_revision(database_url: str) -> None:
    """265e405ccf13 스키마의 핵심 테이블. enum 컬럼에는 실제 값을 쓴다."""
    await _execute_all(
        database_url,
        [
            (
                "INSERT INTO users (id, email, password_hash) "
                "VALUES (1, 'legacy@example.com', 'hash')",
                {},
            ),
            (
                "INSERT INTO user_profiles (id, user_id, height_cm, weight_kg, age, gender, goal, "
                "activity_level, allergies) VALUES (1, 1, 175.5, 70.2, 30, 'female', 'diet', "
                "'moderate', CAST(:allergies AS jsonb))",
                {"allergies": json.dumps(["땅콩"], ensure_ascii=False)},
            ),
            (
                "INSERT INTO refresh_tokens (id, user_id, token, expires_at) "
                "VALUES (1, 1, 'legacy-refresh-token', now() + interval '7 days')",
                {},
            ),
            (
                "INSERT INTO diet_logs (id, user_id, log_date, meal_type) "
                "VALUES (1, 1, DATE '2026-01-15', 'lunch')",
                {},
            ),
            (
                "INSERT INTO diet_log_items (id, diet_log_id, food_name, calories, protein_g) "
                "VALUES (1, 1, '닭가슴살', 165.0, 31.0)",
                {},
            ),
            (
                "INSERT INTO exercise_logs (id, user_id, exercise_date, exercise_name, muscle_group) "
                "VALUES (1, 1, DATE '2026-01-15', '스쿼트', 'legs')",
                {},
            ),
            (
                "INSERT INTO exercise_sets (id, exercise_log_id, set_number, reps, weight_kg) "
                "VALUES (1, 1, 1, 10, 60.0)",
                {},
            ),
            (
                "INSERT INTO ai_recommendations (id, user_id, type, context_summary, recommendation) "
                "VALUES (1, 1, 'diet', '목표 칼로리 1800', '단백질을 늘리세요'), "
                "(2, 1, 'coaching', :chat_summary, '수면 위생을 지키세요')",
                {"chat_summary": f"general 채팅: {RAW_CHAT_TEXT}"},
            ),
        ],
    )


async def _seed_knowledge_ops_revision(database_url: str) -> None:
    """d4f2b8c9a731 시점의 RAG·AI trace 테이블. 이후 리비전이 컬럼·CHECK·백필을 더한다."""
    await _execute_all(
        database_url,
        [
            (
                "INSERT INTO rag_sources (id, title, category, content_hash) "
                "VALUES (1, '근력 운동 가이드', 'exercise', :hash)",
                {"hash": "a" * 64},
            ),
            (
                "INSERT INTO rag_chunks (id, source_id, chunk_index, title, content, content_hash, "
                "category, embedding, embedding_model) VALUES (1, 1, 0, '스쿼트', '무릎 정렬', :hash, "
                "'exercise', CAST(CAST(:embedding AS text) AS vector), 'gemini-embedding-001')",
                {"hash": "b" * 64, "embedding": EMBEDDING_LITERAL},
            ),
            (
                "INSERT INTO rag_ingest_jobs (id, job_type, source_id, status) "
                "VALUES (1, 'ingest', 1, 'succeeded')",
                {},
            ),
            (
                "INSERT INTO rag_retrieval_traces (id, user_id, request_type, rag_trace_group_id, "
                "query_text, search_backend, search_mode, top_k, chunk_id, source_id, rank) VALUES "
                "(1, 1, 'chat', 'group-1', :query, 'opensearch', 'hybrid', 3, 1, 1, 1), "
                "(2, 1, 'chat', 'group-1', :query, 'opensearch', 'hybrid', 3, 1, 1, 2)",
                {"query": RAW_RETRIEVAL_QUERY},
            ),
            (
                "INSERT INTO ai_generation_traces (id, user_id, recommendation_id, request_type, "
                "prompt_version, model_used, rag_trace_group_id) VALUES "
                "(1, 1, 1, 'diet', 'diet-v1', 'gemini-3-flash-preview', NULL), "
                "(2, 1, 2, 'chat', 'chat-v1', 'gemini-3-flash-preview', 'group-1')",
                {},
            ),
        ],
    )


async def _seed_before_scrub_revision(database_url: str) -> None:
    """a8192a3b4c5d 직전. 결정 JSON에 원문 query 사본이 남아 있던 행."""
    await _execute_all(
        database_url,
        [
            (
                "INSERT INTO rag_pipeline_decisions (id, job_id, source_id, decision_type, "
                "policy_version, selected_action, risk_level, reason_code, context) VALUES "
                "(1, 1, 1, 'retrieval_fallback', 'policy-v1', 'keyword_only', 'low', "
                "'opensearch_unavailable', CAST(:context AS jsonb)), "
                "(2, 1, 1, 'ingest', 'policy-v1', 'reembed', 'low', 'content_changed', "
                "CAST(:plain AS jsonb))",
                {
                    "context": json.dumps(
                        {"query": RAW_DECISION_QUERY, "category": "diet"}, ensure_ascii=False
                    ),
                    "plain": json.dumps({"changed_chunks": 2}),
                },
            ),
        ],
    )


async def _fetch_all(database_url: str, sql: str) -> list[dict]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            return [dict(row) for row in (await conn.execute(text(sql))).mappings().all()]
    finally:
        await engine.dispose()


async def _upgrade_to(database_url: str, revision: str) -> None:
    result = await _alembic(database_url, "upgrade", revision)
    assert result.returncode == 0, _describe(f"데이터가 있는 DB upgrade {revision}", result)
    assert await _current_revision(database_url) == revision, (
        f"[upgrade {revision}] alembic_version이 {revision}이 아니다"
    )


@pytest.mark.migration
@pytest.mark.asyncio(loop_scope="session")
async def test_upgrade_head_preserves_seeded_rows() -> None:
    async with _temporary_database(SEEDED_DB_NAME) as database_url:
        heads = await _alembic(database_url, "heads")
        assert heads.returncode == 0, _describe("heads", heads)
        head_revision = heads.stdout.split()[0]

        await _upgrade_to(database_url, ROOT_REVISION)
        await _seed_root_revision(database_url)
        await _upgrade_to(database_url, KNOWLEDGE_OPS_REVISION)
        await _seed_knowledge_ops_revision(database_url)
        await _upgrade_to(database_url, BEFORE_SCRUB_REVISION)
        await _seed_before_scrub_revision(database_url)
        await _upgrade_to(database_url, head_revision)

        # 1. 핵심 테이블 행과 enum 값이 그대로 남는다
        users = await _fetch_all(database_url, "SELECT id, email, is_active FROM users")
        assert users == [{"id": 1, "email": "legacy@example.com", "is_active": True}]
        profiles = await _fetch_all(
            database_url,
            "SELECT user_id, gender::text AS gender, goal::text AS goal, "
            "activity_level::text AS activity_level, allergies FROM user_profiles",
        )
        assert profiles == [
            {
                "user_id": 1,
                "gender": "female",
                "goal": "diet",
                "activity_level": "moderate",
                "allergies": ["땅콩"],
            }
        ]
        tokens = await _fetch_all(database_url, "SELECT id, token, is_revoked FROM refresh_tokens")
        assert tokens == [{"id": 1, "token": "legacy-refresh-token", "is_revoked": False}]
        diet = await _fetch_all(
            database_url,
            "SELECT d.id, d.meal_type::text AS meal_type, i.food_name, i.calories::float AS calories, "
            "i.food_catalog_item_id, i.serving_grams FROM diet_logs d "
            "JOIN diet_log_items i ON i.diet_log_id = d.id",
        )
        assert diet == [
            {
                "id": 1,
                "meal_type": "lunch",
                "food_name": "닭가슴살",
                "calories": 165.0,
                "food_catalog_item_id": None,
                "serving_grams": None,
            }
        ]
        exercise = await _fetch_all(
            database_url,
            "SELECT l.id, l.muscle_group::text AS muscle_group, s.reps FROM exercise_logs l "
            "JOIN exercise_sets s ON s.exercise_log_id = l.id",
        )
        assert exercise == [{"id": 1, "muscle_group": "legs", "reps": 10}]

        # 2. 채팅 context_summary 원문은 지워지고, 채팅이 아닌 요약은 그대로 남는다
        recommendations = await _fetch_all(
            database_url,
            "SELECT id, type::text AS type, context_summary FROM ai_recommendations ORDER BY id",
        )
        assert [(row["id"], row["type"]) for row in recommendations] == [(1, "diet"), (2, "coaching")]
        assert recommendations[0]["context_summary"] == "목표 칼로리 1800"
        assert RAW_CHAT_TEXT not in (recommendations[1]["context_summary"] or "")

        # 3. RAG 원천·청크·작업 행은 남고, 추가된 NOT NULL 컬럼은 기본값으로 채워진다
        sources = await _fetch_all(
            database_url, "SELECT id, origin_type, refresh_policy FROM rag_sources"
        )
        assert sources == [{"id": 1, "origin_type": "manual_text", "refresh_policy": "manual"}]
        chunks = await _fetch_all(
            database_url,
            "SELECT id, source_id, source_version, vector_dims(embedding) AS dims FROM rag_chunks",
        )
        assert chunks == [{"id": 1, "source_id": 1, "source_version": 1, "dims": 3072}]
        jobs = await _fetch_all(database_url, "SELECT id, pipeline_stage FROM rag_ingest_jobs")
        assert jobs == [{"id": 1, "pipeline_stage": "created"}]

        # 4. 검색 trace: 행은 남고 원문은 어디에도 없다(query_text NULL + legacy 지문·요약)
        traces = await _fetch_all(
            database_url,
            "SELECT id, query_text, query_hash, query_summary, query_policy_version, "
            "query_key_version, used_in_response, "
            "query_retention_until = created_at + interval '90 days' AS retention_90d, "
            "row_to_json(t)::text AS row_json FROM rag_retrieval_traces t ORDER BY id",
        )
        assert [row["id"] for row in traces] == [1, 2]
        for row in traces:
            assert row["query_text"] is None
            assert re.fullmatch(r"[0-9a-f]{64}", row["query_hash"] or ""), row
            assert row["query_summary"]
            assert row["query_policy_version"] == "legacy-redaction-v1"
            assert row["query_key_version"] == "legacy-unkeyed-v1"
            assert row["used_in_response"] is False
            assert row["retention_90d"] is True
            assert RAW_RETRIEVAL_QUERY not in row["row_json"]

        # 5. 생성 trace: 기존 행은 성공한 제공자 호출로 표시되고 수명주기·쿼터 컬럼이 채워진다
        generations = await _fetch_all(
            database_url,
            "SELECT id, status, provider_invoked, request_id, lifecycle_version, "
            "started_at = created_at AS started_is_created, "
            "completed_at = created_at AS completed_is_created, quota_status "
            "FROM ai_generation_traces ORDER BY id",
        )
        assert [row["id"] for row in generations] == [1, 2]
        for row in generations:
            assert row["status"] == "succeeded"
            assert row["provider_invoked"] is True
            assert row["request_id"] is not None
            assert row["lifecycle_version"] == "request-lifecycle-v1"
            assert row["started_is_created"] is True
            assert row["completed_is_created"] is True
            assert row["quota_status"] == "not_checked"
        assert generations[0]["request_id"] != generations[1]["request_id"]

        # 6. 결정 JSON: query 사본만 지워지고 나머지 키와 query 없는 행은 그대로다
        decisions = await _fetch_all(
            database_url, "SELECT id, context FROM rag_pipeline_decisions ORDER BY id"
        )
        assert [row["id"] for row in decisions] == [1, 2]
        scrubbed = decisions[0]["context"]
        assert "query" not in scrubbed
        assert scrubbed["category"] == "diet"
        assert RAW_DECISION_QUERY not in json.dumps(scrubbed, ensure_ascii=False)
        assert decisions[1]["context"] == {"changed_chunks": 2}
