# AI Health Trainer

AI 기반 개인 맞춤형 건강·피트니스 코칭 애플리케이션입니다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy Async, Alembic |
| Frontend | Flutter, Riverpod, go_router |
| DB | PostgreSQL 17, pgvector, Redis |
| AI | Google Gemini API, RAG |
| Infra | Docker Compose, Nginx, GitHub Actions |

## 로컬 실행

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

백엔드 API는 기본적으로 `http://localhost:8000`, 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

### 개발 환경 팁

Flutter Web에서 테스트할 때 CORS 에러가 발생하면, `backend/.env`의 `BACKEND_CORS_ORIGINS`를 `*`로 변경하세요.

## 프로덕션 배포

```bash
cp .env.example .env.prod
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## GitHub Secrets

GitHub Actions CD를 사용하려면 아래 시크릿을 GitHub Repository Settings > Secrets and variables > Actions 에 설정해야 합니다.

- `SSH_HOST`
- `SSH_USERNAME`
- `SSH_KEY`
- `SSH_PORT`

## 백업 실행

프로덕션 서버에서 아래 명령으로 PostgreSQL 백업을 실행합니다.

```bash
bash scripts/backup.sh
```

백업 파일은 `/opt/backups` 아래에 `.sql.gz` 형식으로 저장되고, 7일이 지난 백업은 자동 삭제됩니다.

## API 문서

- 로컬 백엔드 직접 접근: `/docs`
- Nginx 프록시 환경: `/docs`

## 테스트 실행

백엔드 테스트:

```bash
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test \
  -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres \
  backend pytest tests/ -v --tb=short
```

Flutter 정적 분석:

```bash
cd frontend
flutter pub get
flutter analyze
```

### RAG 데이터 인제스트

AI 추천 기능을 사용하려면 RAG 지식 데이터를 DB에 주입해야 합니다.

```bash
# 기존 RAG 데이터 초기화 (카테고리 변경 시 필요)
docker compose exec backend python scripts/reset_rag_data.py

# 전체 RAG 데이터 인제스트
docker compose exec backend python scripts/ingest_rag_data.py --dir rag_data/

# 단일 파일 인제스트 (카테고리 지정 필수)
docker compose exec backend python scripts/ingest_rag_data.py --file rag_data/nutrition_basics.md --category nutrition
```
