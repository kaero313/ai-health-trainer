# Mobile UI Acceptance Report

> Date: 2026-07-11
> Scope: Stitch `Kinetic Cybernetics` 기반 Flutter 모바일 UI
> Runtime: Flutter Web local development server

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

## 5. Automated Evidence

```text
flutter analyze   -> No issues found
flutter test      -> 36 passed
flutter build web -> success
```

추가 확인:

- `Image.network` / `NetworkImage` 사용 없음
- 기능 화면의 외부 image URL 사용 없음
- 알려진 Stitch 영문 placeholder와 고정 건강 수치 검색 결과 없음
- 브라우저 console error 없음
- 개발 서버의 DWDS 경고만 확인했으며 release Web build에는 해당하지 않음

## 6. Android Build Verification

2026-07-11에 Windows Android toolchain을 구성하고 Debug APK 빌드를 검증했다.

```text
Android SDK Platform 35       -> installed
Android SDK Build-Tools 35   -> installed
Android Platform-Tools/ADB   -> installed
Android NDK 27.0.12077973    -> installed
flutter build apk --debug    -> success
```

- 앱 ID: `com.aihealthtrainer.frontend`
- 앱 표시명: `AI Health Trainer`
- min SDK: 21
- target/compile SDK: 35
- Debug APK: `frontend/build/app/outputs/flutter-apk/app-debug.apk`
- USB device용 API 주소는 `--dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1`로 주입할 수 있다.
- 실제 Android 기기 설치와 카메라/갤러리 검증은 기기 연결 및 USB debugging 승인 후 수행한다.

## 7. Functional Boundaries

- Backend, DB, API contract, RAG ingest/control plane은 이번 UI 작업에서 변경하지 않았다.
- 식단/운동 CRUD, 사진 bytes upload, AI 추천, 채팅, source chip, profile update 라우트는 기존 provider/repository 경로를 유지한다.
- 실제 AI 생성 경로의 trace와 출처 무결성 검증은 `docs/UI_AI_INTEGRATION_VALIDATION_REPORT.md`를 기준으로 한다.
- 현재 acceptance는 Web mobile viewport와 Android Debug APK build까지 포함한다. 실제 기기 권한/터치/카메라 검증은 기기 연결 후 완료한다.
