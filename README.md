# AI Health Trainer

AI 기반 개인 맞춤형 건강·피트니스 코칭 애플리케이션입니다.

문서는 역할 기준으로만 유지합니다.

| Document | Audience | Purpose |
|----------|----------|---------|
| `AGENTS.md` | AI 작업자 | Codex/AI가 작업할 때 지킬 실행 규칙 |
| `docs/OWNER_GUIDE.md` | 개발자/설계자/운영자인 사용자 | 제품 방향, 구현 현황, 개발/운영 기준 |

현재 상태:

- Phase 1~6 완료
- Backend tests: 56 PASS
- Flutter analyze: 0 issues

로컬 실행:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

백엔드 API 문서:

- `http://localhost:8000/docs`
