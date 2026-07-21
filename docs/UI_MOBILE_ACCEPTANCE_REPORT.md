# Mobile UI Acceptance Report

> Date: 2026-07-15
> Scope: Stitch `Kinetic Cybernetics` 기반 Flutter 모바일 UI
> Runtime: Flutter Web local development server + Samsung Android 15 Debug APK

## 1. Acceptance Goal

기존 Riverpod, GoRouter, API, AI/RAG 기능을 유지하면서 Stitch 레퍼런스의 정보 계층과 시각 언어를 전체 앱에 적용했다. 단순 색상 교체가 아니라 모바일 화면의 카드 순서, 버튼 계층, 하단 5탭, 입력 화면 구조, 상태 표현을 다시 구성했다.

적용 기준:

- black surface + electric cyan + lime + orange palette
- Sora headline, Hanken Grotesk body, Geist label/number, Noto Sans KR fallback
- glass card, thin neon border, restrained glow, 8px 이하 기본 card radius
- 동일 폭의 `홈 / 통계 / 플랜 / 식단 / 스캔` 하단 5탭
- 모든 사용자 문구 한국어. 브랜드명, 단위, AI/RAG/VO2 Max 같은 표준 약어만 예외
- HTML 레퍼런스 이미지는 `frontend/assets/stitch/`의 로컬 asset으로 사용

## 2. Data Truth Policy

레퍼런스 화면의 수치를 앱 데이터처럼 복제하지 않았다.

- 체중과 목표 영양은 실제 profile/API 값만 표시한다.
- 체중 추이는 실제 weight history가 있을 때만 그린다.
- 체지방, 근육량, 심박, 수면, VO2 Max, 체성분 값이 없으면 `-- / 기록 없음`으로 표시한다.
- 실시간 세션 API가 없으므로 가짜 타이머, 강도, 심박, 완료율을 표시하지 않는다.
- 연결 기기 정보가 없으면 `기기 미연결`로 표시한다.
- 알레르기와 식단 선호는 임의 chip을 만들지 않고 프로필 관리 화면으로 연결한다.
- 추천/채팅의 출처는 backend가 검증한 `sources`만 UI chip으로 표시한다.

## 3. Route Matrix

| Route | Surface | 390x844 Browser | Automated State Coverage |
|---|---|---:|---:|
| `/splash` | 스플래시 | PASS | PASS |
| `/onboarding` | 온보딩 | PASS | PASS |
| `/login` | 로그인 | PASS | PASS |
| `/register` | 회원가입 | PASS | PASS |
| `/dashboard` | 홈 | PASS | PASS |
| `/profile` | 통계 | PASS | PASS |
| `/exercise` | 플랜 | PASS | PASS |
| `/diet` | 식단 | PASS | PASS |
| `/diet/analyze` | 스캔 | PASS | PASS |
| `/ai/chat` | AI 코치 | PASS | PASS |
| `/dashboard/monthly` | 월간 리포트 | PASS | PASS |
| `/diet/add` | 식단 추가 | PASS | PASS |
| `/diet/recommend` | AI 식단 추천 | PASS | PASS |
| `/exercise/add` | 운동 추가 | PASS | PASS |
| `/exercise/recommend` | AI 운동 추천 | PASS | PASS |
| `/profile/edit` | 프로필 설정 | PASS | PASS |

## 4. Responsive Verification

자동 widget test와 인앱 브라우저를 함께 사용했다.

| Viewport | Coverage | Result |
|---|---|---:|
| 360x800 | 하단 5탭, 홈, 스캔, 운동 추가, 프로필 설정, 전체 화면군 widget test | PASS |
| 390x844 | 16개 전체 route 실제 브라우저 렌더링 | PASS |
| 430x932 | 홈, 식단, 플랜, 채팅, 전체 화면군 widget test | PASS |
| 360x600 | 채팅 입력과 낮은 keyboard viewport | PASS |
| Text scale 1.3 | 인증, 홈/통계/월간, 식단, 운동, 채팅/프로필 입력 | PASS |

검증 중 발견해 수정한 결함:

- 온보딩 상단 브랜드/건너뛰기 행의 큰 글자 overflow
- 식단 매크로 목표 값 행의 compact card overflow
- 스캔 hero의 큰 글자 vertical overflow
- 과거 quick-action FAB를 전제로 한 하단 navigation test
- 대시보드/profile test의 weight history 실제 HTTP 호출
- Android 실기기에서 설명문의 한두 글자만 다음 줄로 떨어지는 문제
- Android 실기기에서 스캔 hero와 운동 추가 제목의 어색한 단어 분리

## 5. Automated Evidence

```text
flutter analyze   -> No issues found
flutter test      -> 39 passed
flutter build web -> success
flutter build apk --debug -> success
backend pytest    -> 188 passed
```

추가 확인:

- `Image.network` / `NetworkImage` 사용 없음
- 기능 화면의 외부 image URL 사용 없음
- 알려진 Stitch 영문 placeholder와 고정 건강 수치 검색 결과 없음
- 브라우저 console error 없음
- 개발 서버의 DWDS 경고만 확인했으며 release Web build에는 해당하지 않음

## 6. Android Device Verification

2026-07-11에 Windows Android toolchain을 구성했고, 2026-07-15에 동일한 실제 Android 기기에 최신 Debug APK를 재설치해 기능 검증을 완료했다.

```text
Android SDK Platform 35       -> installed
Android SDK Build-Tools 35   -> installed
Android Platform-Tools/ADB   -> installed
Android NDK 27.0.12077973    -> installed
flutter build apk --debug    -> success
adb install -r               -> success
```

- 검증 기기: Samsung `SM S937N`, Android 15 (API 35)
- 앱 ID: `com.aihealthtrainer.frontend`
- 앱 표시명: `AI Health Trainer`
- min SDK: 21
- target/compile SDK: 35
- Debug APK: `frontend/build/app/outputs/flutter-apk/app-debug.apk`
- `--dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1`과 `adb reverse tcp:8000 tcp:8000`으로 로컬 backend에 연결했다.
- 홈, 통계, 플랜, 식단, 스캔 5개 탭의 실제 터치 전환과 API 데이터 로드를 확인했다.
- 카메라 앱 실행, Android Photo Picker 갤러리 선택, bytes upload, Gemini 음식 분석 결과 생성을 확인했다.
- 실제 음식 사진 분석 결과 4개가 화면에 표시됐고, 선택 항목을 식단으로 저장한 뒤 식단 화면에서 삭제했다.
- 스캔으로 생성한 식단 기록은 DB에서 `ai_analyzed=true`로 보존되는 것을 확인했고, 검증 후 해당 식단 기록이 남지 않은 것을 확인했다.
- 만료된 access token 상황을 one-shot 401 로컬 프록시로 재현했다. 첫 multipart 요청 401, refresh 1회, 새 multipart body 재전송 1회 후 Gemini 분석 성공과 결과 화면 표시를 확인했다.
- 위 재시도 검증에서 `analyze_requests=2`, `refresh_requests=1`이었으며, 유효한 갱신 토큰이 재시도 실패 때문에 삭제되지 않는 것도 자동 테스트로 검증했다.
- 첫 재현에서는 인증 재전송 이후 Gemini `ServerError`와 provider retry timeout으로 503이 반환됐고 실패 generation trace가 남았다. 동일 조건의 다음 실행은 성공해 클라이언트 인증 복구와 외부 provider 장애가 분리되어 관측되는 것을 확인했다.
- 프로필 수정 화면에서 Samsung 숫자 키보드가 열린 상태로 입력 필드와 하단 액션이 겹치지 않는 것을 확인했다.
- 운동 추가 validation과 키보드 표시 시 입력 필드/고정 저장 버튼이 가려지지 않는 것을 확인했다. `UI-E2E Bench Press`, 1세트 10회 60kg 기록을 실제로 저장하고 화면/DB 반영 후 앱에서 삭제했다.
- AI 운동 추천은 4개 운동과 `상체 운동 가이드`, `점진적 과부하 원칙` 출처를 표시했다. retrieval trace는 OpenSearch hybrid 검색 3건 중 최종 답변에 사용된 2건을 구분해 기록했다.
- AI 식단 추천은 provider 일시 장애와 timeout에서 안전한 한국어 오류 카드 및 `다시 시도` 동작을 확인했고, 후속 호출에서 추천 음식과 `단백질 보충 식사 예시`, `벌크업(근비대) 식단 가이드` 출처를 표시했다.
- AI 채팅은 운동 context와 실제 질문을 전송해 답변을 표시했고, 화면 source chip과 retrieval trace의 `used_in_response` 출처가 일치했다.
- 추천과 채팅의 성공 trace에는 Gemini model, token 수, latency, OpenSearch search backend가 저장됐고, provider 실패 trace에는 `AI_SERVICE_ERROR` 또는 `AI_TIMEOUT`과 실패 stage가 별도로 남았다.
- Android logcat에서 Flutter exception, fatal crash, Dio/Socket 오류, RenderFlex overflow가 없음을 확인했다.
- 검증 중 발견한 문장 orphan과 제목 줄바꿈을 수정하고 APK를 재설치해 동일 기기에서 재확인했다.

실기기 검증을 위해 생성한 식단/운동 기록과 recommendation row는 삭제했다. generation/retrieval trace는 운영 감사 증거로 유지했으며, 이번 Samsung Android 15 기준 실기기 acceptance 항목은 모두 완료했다.

## 7. Functional Boundaries

- Backend, DB, API contract, RAG ingest/control plane은 이번 UI 작업에서 변경하지 않았다.
- 식단/운동 CRUD, 사진 bytes upload, AI 추천, 채팅, source chip, profile update 라우트는 기존 provider/repository 경로를 유지한다.
- 실제 AI 생성 경로의 trace와 출처 무결성 검증은 `docs/UI_AI_INTEGRATION_VALIDATION_REPORT.md`를 기준으로 한다.
- 현재 acceptance는 Web mobile viewport, Android Debug APK 설치, 5탭 터치, 프로필 입력, 식단·운동 CRUD, 카메라/갤러리, 사진 AI 분석, 만료 토큰 multipart 재전송, 식단·운동 추천, AI 채팅과 검증된 출처 표시까지 포함한다.
- 다른 Android 제조사/해상도, iOS, release signing과 스토어 배포 검증은 이번 로컬 Debug APK acceptance 범위에 포함하지 않는다.
