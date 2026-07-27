# AI 통합 검증 자동화 운영 기준

## 목적

이 검증기는 화면에서 사용하는 실제 API, Gemini 생성, RAG 검색, trace, 개인정보 최소화,
테스트 데이터 정리를 하나의 감사 가능한 run으로 검증한다. 단순히 HTTP 200만 확인하지 않고
각 단계의 성공 여부와 운영 증거를 `ai_validation_runs` 및 `ai_validation_items`에 저장한다.

## 검증 경로

```text
health
  -> 임시 계정 등록/로그인
  -> 프로필 설정
  -> 식단/운동 생성 및 조회
  -> 대시보드 projection
  -> 식단 추천 / 운동 추천 / AI 채팅 / 음식 사진 분석
  -> generation trace 검증
  -> retrieval/source trace 검증
  -> 개인정보 불변식 검증
  -> API 삭제 및 DB/Redis 잔여 데이터 정리
  -> Markdown report
```

검증 item은 시작 시점과 종료 시점에 각각 commit된다. 프로세스가 중간에 종료되어도 마지막으로
성공한 단계와 실패 단계가 DB에 남으며, `validation-cleanup`으로 잔여 데이터를 제거할 수 있다.

## 실행

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec -e DEBUG=false backend python -m app.cli.ai validate-integration \
  --report-path /workspace/docs/UI_AI_INTEGRATION_VALIDATION_REPORT.md
```

조회와 복구:

```bash
docker compose exec -e DEBUG=false backend python -m app.cli.ai validation-runs --limit 20
docker compose exec -e DEBUG=false backend python -m app.cli.ai validation-run --run-id <run_uuid>
docker compose exec -e DEBUG=false backend python -m app.cli.ai validation-cleanup --run-id <run_uuid>
```

기본 fixture는 Flutter Stitch asset인 `nutrition_salmon.jpg`이며 Docker Compose에서 read-only로
mount된다. 다른 JPEG/PNG를 검증하려면 `--image-path`를 명시한다.

## 상태 계약

- `succeeded`: 필수 item이 모두 통과했고 cleanup도 성공했다.
- `partial`: 일부 item이 통과했지만 실패 또는 skip이 있다.
- `failed`: 유효한 검증 결과를 만들지 못했다.
- `abandoned`: 중단된 run을 사후 cleanup으로 종료했다.

각 item은 `started`, `passed`, `failed`, `skipped` 중 하나다. 실패 시 provider 원문 대신
machine-readable `error_code`, HTTP status, bounded evidence만 저장한다.

## 개인정보와 정리 경계

저장하지 않는 값:

- 임시 계정 이메일과 비밀번호
- access/refresh token
- 사용자 질문, prompt, AI 답변 원문
- 음식 이름과 provider raw response

저장하는 값:

- run/check status와 latency
- source, suggestion, trace, attempt 개수
- model, token count, provider latency, request UUID
- search backend, prompt/final evidence row 개수
- 개인정보 불변식과 cleanup 결과

검증 종료 시 profile, refresh token, 식단/운동, AI recommendation, 임시 사용자를 삭제한다.
Redis quota key도 삭제한다. Generation/retrieval trace는 운영 증거로 유지하되 `user_id`가
`ON DELETE SET NULL`로 익명화됐는지 확인한다.

## 최신 실행 증거

- Run ID: `de86df0a-004c-406e-948b-b5b79b08fd9b`
- 결과: `14/14 passed`
- AI 경로: 식단 추천, 운동 추천, 채팅, 음식 사진 분석
- Generation trace: 4건, provider attempt 4건
- Retrieval trace: 9건, final evidence 6건, OpenSearch hybrid
- 개인정보 검사: raw query/prompt/chat 원문 0건
- cleanup: API delete 실패 0건, 임시 사용자 및 기록 잔여 0건

상세 실행 결과는 `docs/UI_AI_INTEGRATION_VALIDATION_REPORT.md`에 생성된다. Flutter widget test와
Android 실기기 검증은 API/AI run과 별도 계층이며 `docs/UI_MOBILE_ACCEPTANCE_REPORT.md`에서 관리한다.
