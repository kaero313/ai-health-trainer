# AI Health Trainer - 커밋 컨벤션 가이드

## Conventional Commits 형식

모든 커밋 메시지는 아래 형식을 따릅니다:

```
<type>(<scope>): <description>

[optional body]
```

### Type (필수)

| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새로운 기능 | `feat(auth): JWT 로그인 API 구현` |
| `fix` | 버그 수정 | `fix(diet): 칼로리 합계 계산 오류 수정` |
| `docs` | 문서 추가/수정 | `docs: DATABASE_SCHEMA.md 테이블 추가` |
| `style` | 코드 포맷팅 (기능 변경 없음) | `style: Black 포맷터 적용` |
| `refactor` | 리팩토링 (기능 변경 없음) | `refactor(exercise): 서비스 레이어 분리` |
| `test` | 테스트 추가/수정 | `test(auth): 토큰 갱신 테스트 추가` |
| `chore` | 빌드/설정/인프라 | `chore: Docker 환경 구성` |
| `perf` | 성능 개선 | `perf(dashboard): 쿼리 N+1 문제 해결` |
| `ci` | CI/CD 설정 | `ci: GitHub Actions 워크플로우 추가` |
| `build` | 빌드 시스템/의존성 | `build: requirements.txt 패키지 업데이트` |

### Scope (선택)

| Scope | 영역 |
|-------|------|
| `auth` | 인증 (JWT, 로그인, 회원가입) |
| `profile` | 프로필 (신체정보, 목표) |
| `diet` | 식단 (기록, AI 분석) |
| `exercise` | 운동 (기록, 세트) |
| `dashboard` | 대시보드 |
| `ai` | AI 서비스 (Gemini, RAG) |
| `db` | 데이터베이스, 마이그레이션 |
| `ui` | Flutter UI |

### 규칙
1. **첫 줄 100자 이내**
2. **한국어 또는 영어** 모두 허용
3. **마침표(.) 없이** 끝내기
4. **현재형** 사용 ("구현", "수정", "추가")

## 자동 검증

`.githooks/commit-msg` 훅이 형식을 자동으로 검증합니다.
잘못된 형식의 커밋은 자동으로 거부됩니다.

### 설정 방법
```bash
git config core.hooksPath .githooks
```
