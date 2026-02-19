import argparse
import asyncio
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.rag_service import RAGService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG 데이터 인제스트 CLI")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--dir", dest="directory", help="인제스트할 폴더 경로")
    target_group.add_argument("--file", dest="file_path", help="인제스트할 단일 파일 경로")
    parser.add_argument("--category", help="단일 파일 인제스트 시 카테고리")
    return parser


def _read_document(file_path: Path) -> tuple[str, str]:
    content: str | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            content = file_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError(f"파일 인코딩을 해석할 수 없습니다: {file_path}")

    title = file_path.stem
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip() or title
            break
    return title, content


def _infer_category(file_name: str) -> str:
    normalized = file_name.lower()
    if normalized.startswith("nutrition_"):
        return "nutrition"
    if normalized.startswith("exercise_"):
        return "exercise"
    return "nutrition"


def _collect_files(directory: Path) -> list[Path]:
    markdown_files = list(directory.rglob("*.md"))
    text_files = list(directory.rglob("*.txt"))
    return sorted(markdown_files + text_files)


async def _run_ingest(args: argparse.Namespace) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    total_files = 0
    total_chunks = 0

    try:
        async with session_factory() as session:
            rag_service = RAGService(session, settings)

            if args.directory:
                target_dir = Path(args.directory)
                if not target_dir.exists() or not target_dir.is_dir():
                    raise FileNotFoundError(f"유효한 디렉토리가 아닙니다: {target_dir}")

                files = _collect_files(target_dir)
                if not files:
                    print("인제스트할 파일이 없습니다.")
                    return

                for file_path in files:
                    title, content = _read_document(file_path)
                    category = _infer_category(file_path.name)
                    chunk_count = await rag_service.ingest_document(
                        title=title,
                        content=content,
                        category=category,
                        source=str(file_path),
                    )
                    total_files += 1
                    total_chunks += chunk_count
                    print(f"인제스트: {file_path.name} - {chunk_count} 청크 저장")
            else:
                target_file = Path(args.file_path)
                if not target_file.exists() or not target_file.is_file():
                    raise FileNotFoundError(f"유효한 파일이 아닙니다: {target_file}")
                if not args.category:
                    raise ValueError("--file 사용 시 --category가 필요합니다")

                title, content = _read_document(target_file)
                chunk_count = await rag_service.ingest_document(
                    title=title,
                    content=content,
                    category=args.category,
                    source=str(target_file),
                )
                total_files = 1
                total_chunks = chunk_count
                print(f"인제스트: {target_file.name} - {chunk_count} 청크 저장")

        print(f"완료: {total_files}개 파일, 총 {total_chunks} 청크 저장")
    finally:
        await engine.dispose()


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(_run_ingest(args))
    except Exception as exc:
        print(f"실패: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
