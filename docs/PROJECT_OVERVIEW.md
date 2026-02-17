# AI Health Trainer - 프로젝트 개요

## 1. 프로젝트 목적

사진 한 장 + 운동 기록만으로 현재 상태를 평가하고, 벌크/다이어트/유지 목표에 맞춘 '다음 행동'을 추천해주는 **AI 코치 앱**.  
Google Play Store 배포를 목표로 하는 **포트폴리오** 프로젝트.

---

## 2. 기술 스택

| 영역 | 기술 | 버전/비고 |
|------|------|-----------|
| Frontend | Flutter (Dart) | 최신 stable |
| Backend | Python 3.12+ / FastAPI | 비동기, 자동 Swagger |
| Database | PostgreSQL 17 + pgvector | 메인 DB + 벡터 검색 |
| Cache | Redis | 세션/캐시 |
| AI/LLM | **Google Gemini API** (Gemini 2.5 Flash/Pro) | 멀티모달 + 텍스트, 무료 티어 활용 |
| Auth | JWT (자체 구현) | python-jose + passlib |
| Infra | Docker Compose | 단일 VM 배포 |
| Proxy | Nginx | 리버스 프록시 + HTTPS |
| CI/CD | GitHub Actions | 자동 테스트 + 배포 |

---

## 3. AI 개발 역할 분담

이 프로젝트는 두 개의 AI를 역할별로 나누어 개발합니다.

### 3-1. Claude Opus 4.6 — 설계자 (Architect)

**담당:** 프로젝트 관리 및 전체 설계

| 카테고리 | 구체적 업무 |
|---------|------------|
| **요구사항** | 기능 요구사항 정의, 우선순위 결정, 스코프 관리 |
| **설계** | 시스템 아키텍처, DB 스키마 ERD, API 엔드포인트 설계 |
| **DB** | 테이블 설계, 인덱스 전략, 마이그레이션 계획 |
| **API** | RESTful API 명세, 요청/응답 스키마, 에러 코드 정의 |
| **AI 전략** | LLM 프롬프트 설계, RAG 파이프라인 아키텍처 |
| **테스트 전략** | 테스트 범위 정의, 테스트 시나리오 작성 |
| **리스크 관리** | 기술 리스크 식별, 비용 관리 방안 |
| **문서화** | 설계 문서 작성 및 유지보수 |

**산출물:** `docs/` 폴더 내 모든 설계 문서

### 3-2. Codex 5.3 — 구현자 (Implementer)

**담당:** 코드 작성 및 품질 관리

| 카테고리 | 구체적 업무 |
|---------|------------|
| **구현** | `docs/` 설계 문서를 기반으로 코드 작성 |
| **리팩토링** | 코드 품질 개선, 중복 제거, 패턴 적용 |
| **테스트** | 단위 테스트, 통합 테스트 코드 작성 |
| **버그 수정** | 에러 분석 및 수정 |
| **최적화** | 성능 개선, 쿼리 최적화 |

**참조 문서 (Codex가 반드시 읽어야 하는 문서):**

```
docs/
├── PROJECT_OVERVIEW.md    ← 지금 이 문서 (프로젝트 전체 맥락)
├── DATABASE_SCHEMA.md     ← DB 테이블/컬럼 상세 명세
├── API_SPECIFICATION.md   ← API 엔드포인트 상세 명세
├── AI_RAG_STRATEGY.md     ← AI 모델 호출 방법 및 RAG 설계
├── DEVELOPMENT_GUIDE.md   ← 코딩 컨벤션, 구조, 실행 방법
├── FLUTTER_UI_DESIGN.md   ← 화면별 UI/UX 설계, 디자인 시스템
└── DEPLOYMENT.md          ← Docker/배포 설정
```

### 3-3. 협업 워크플로우

```
[Claude Opus 4.6]                    [Codex 5.3]
     │                                    │
     ├─ 1. 설계 문서 작성 ──────────────→ │
     │                                    ├─ 2. 설계 문서 기반 코드 구현
     │                                    │
     │ ←──── 3. 구현 중 이슈/질문 ────────┤
     │                                    │
     ├─ 4. 설계 수정/보완 ──────────────→ │
     │                                    ├─ 5. 코드 수정/완성
     │                                    │
     ├─ 6. 코드 리뷰/피드백 ────────────→ │
     │                                    ├─ 7. 리팩토링/테스트 추가
     │                                    │
     ├─ 8. 테스트 전략 제공 ────────────→ │
     │                                    ├─ 9. 테스트 코드 작성
     └────────────────────────────────────┘
```

> **핵심 원칙:** Claude Opus가 만든 `docs/` 문서가 "계약서" 역할을 합니다.  
> Codex는 이 문서에 정의된 스키마, API, 규칙을 충실히 따라 구현합니다.

---

## 4. 핵심 기능 모듈

### 4-1. 인증 모듈 (Auth)
- 이메일/비밀번호 기반 회원가입 및 로그인
- JWT Access Token + Refresh Token
- 비밀번호 bcrypt 해싱

### 4-2. 프로필 모듈 (Profile)
- 신체 정보: 키, 몸무게, 나이, 성별
- 목표 설정: 벌크업 / 다이어트 / 유지
- 활동 수준: 비활동적 / 가벼운 운동 / 보통 / 활발 / 매우 활발
- 알레르기 및 선호 식품 목록

### 4-3. 식단 모듈 (Diet)
- 식단 기록 CRUD (아침/점심/저녁/간식)
- 음식 사진 → AI 분석 (Gemini 2.5 Flash Vision)
- 영양소 자동 계산 (칼로리, 단백질, 탄수화물, 지방)
- AI 기반 식단 추천 (목표 기반)

### 4-4. 운동 모듈 (Exercise)
- 운동 기록 CRUD (운동명, 근육군, 세트/횟수/무게)
- 과거 기록과 비교 분석
- AI 기반 운동 추천 (목표 + 기록 기반)

### 4-5. 대시보드 모듈 (Dashboard)
- 오늘의 영양 섭취 현황 (목표 대비 진행률)
- 오늘의 운동 현황
- 주간/월간 트렌드

### 4-6. AI 코칭 모듈 (AI Coaching)
- RAG 기반 근거 있는 추천
- 사용자 컨텍스트 기반 개인화
- 추천 히스토리 저장

---

## 5. MVP 개발 순서 (Phase)

| Phase | 기간 | 범위 | 완료 기준 |
|-------|------|------|-----------|
| **Phase 1** | 1~2주 | 인프라 + 인증 + 프로필 | Docker 실행, 회원가입/로그인 동작 |
| **Phase 2** | 2~3주 | 운동 + 식단 CRUD | 기록 저장/조회/수정/삭제 동작 |
| **Phase 3** | 2~3주 | AI 통합 + RAG | AI 추천 + 음식 사진 분석 동작 |
| **Phase 4** | 1~2주 | 대시보드 + 배포 | Play Store 배포 완료 |

---

## 6. 디렉토리 구조

```
AI_Health-Trainer/
├── docs/                        # 설계 문서 (Claude Opus 관리)
│   ├── PROJECT_OVERVIEW.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPECIFICATION.md
│   ├── AI_RAG_STRATEGY.md
│   ├── DEVELOPMENT_GUIDE.md
│   └── DEPLOYMENT.md
│
├── backend/                     # Python FastAPI (Codex 구현)
│   ├── app/
│   │   ├── api/v1/              # API 라우터
│   │   ├── core/                # 설정, 보안, DB 연결
│   │   ├── models/              # SQLAlchemy ORM 모델
│   │   ├── schemas/             # Pydantic 요청/응답 스키마
│   │   ├── services/            # 비즈니스 로직
│   │   └── main.py              # FastAPI 앱 진입점
│   ├── alembic/                 # DB 마이그레이션
│   ├── rag_data/                # RAG용 데이터
│   ├── tests/                   # 테스트 코드
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                    # Flutter 앱 (Codex 구현)
│   ├── lib/
│   │   ├── models/              # 데이터 모델
│   │   ├── screens/             # 화면
│   │   ├── services/            # API 통신
│   │   ├── providers/           # 상태 관리 (Riverpod)
│   │   ├── widgets/             # 재사용 위젯
│   │   └── main.dart
│   └── pubspec.yaml
│
├── nginx/
│   └── nginx.conf               # 리버스 프록시 설정
├── docker-compose.yml           # 전체 서비스 오케스트레이션
├── .github/workflows/           # CI/CD
├── .env.example                 # 환경변수 템플릿
└── README.md
```
