# AI Health Trainer - Flutter UI 디자인 기준

> **이 문서의 목적:** Flutter 화면을 만들거나 고칠 때 따르는 디자인 토큰·공통 위젯·화면 패턴 기준.
> **대상:** lead·frontend 역할(Claude Code·Codex)과 사용자 본인
> **기준 코드:** `frontend/lib/core/theme/`, `frontend/lib/shared/widgets/neo_widgets.dart`, `frontend/lib/core/router/`. 문서와 코드가 다르면 코드가 맞고, 이 문서를 고친다.
> **디자인 출처:** Stitch `Kinetic Cybernetics` 레퍼런스(2026-07 적용). 적용 과정과 수용 검증은 `docs/UI_MOBILE_ACCEPTANCE_REPORT.md`에 있다.
> **Last updated:** 2026-09-25
> **다음 디자인 시스템:** shadcn_ui 기반 Light/Dark 설계는 `docs/DESIGN_SYSTEM.md`에 있다. 홈 탭(Dashboard)은 2026-10-04에 새 체계로 옮겼다(`DESIGN_SYSTEM.md` §17). 나머지 화면은 사용자가 옮기라고 지시하기 전까지 이 문서(현행)를 따른다.

2026-07 이전 설계(딥 네이비·그린 팔레트, Inter 폰트, 중앙 FAB 하단 바, 화면별 와이어프레임)는 폐기했다. 필요하면 `git log -- docs/FLUTTER_UI_DESIGN.md`로 이력을 본다.

---

## 1. 원칙

- 모바일 우선이다. 기준 폭은 360·390·430이다.
- 다크 테마 하나만 있다(`AppTheme.darkTheme`, Material 3). 라이트 모드를 가정하지 않는다.
- 정보가 먼저다. 기록·수치·다음 행동을 보여 주는 화면이고 마케팅 랜딩 페이지가 아니다.
- 없는 데이터를 꾸며 보이지 않는다(§6).
- 검정 바탕에 시안·라임·오렌지 포인트, 얇은 네온 테두리, 절제된 glow를 쓴다. glow는 강조 카드와 주 버튼에만 둔다.

---

## 2. 디자인 토큰

### 2-1. 색 (`app_colors.dart`)

| 토큰 | 값 | 용도 |
|---|---|---|
| `background` | `#050505` | 페이지 배경, 하단 고정 액션 바, 채운 버튼·칩 위 글자 |
| `surface` | `#131313` | 하단 탭 바, 채팅 입력 바, 드롭다운 메뉴, Shimmer 바탕 |
| `surfaceLow` | `#1C1B1B` | 카드 바탕(`cardDecoration`·`glassCardDecoration`), RefreshIndicator 배경 |
| `surfaceLight` | `#201F1F` | 입력 칸 채움(테마), 진행 바·링 트랙, Shimmer 하이라이트 |
| `surfaceHigh` | `#2A2A2A` | 원형 아이콘 버튼, 인증 카드, 차트 툴팁, 스낵바 |
| `surfaceHighest` | `#353534` | 선택되지 않은 칩 |
| `primary` | `#00F0FF` 일렉트릭 시안 | 주 액션, 활성 탭, 상단 바 제목, 칼로리·단백질 |
| `primarySoft` | 시안 20% | 활성 탭 배경 |
| `secondary` / `secondarySoft` | `#C3F400` 라임 / 라임 20% | 성공, 탄수화물 |
| `tertiary` | `#FF5C00` 오렌지 | 지방 |
| `textPrimary` / `textSecondary` / `textDisabled` | `#E5E2E1` / `#B9CACB` / `#849495` | 본문 / 보조 / 비활성·힌트 |
| `success` / `warning` / `error` | `secondary` / `#FFCFBE` / `#FFB4AB` | 상태 |
| `divider` / `glassBorder` / `shimmer` | `#3B494B` / 시안 15% / `#252525` | 구분선, 유리 테두리, 로딩 |

- 매크로 색은 `calories`·`protein` = `primary`, `carbs` = `secondary`, `fat` = `tertiary`다. 칼로리와 단백질은 같은 시안이다.
- 정의만 있고 화면에서 쓰지 않는 토큰: `surfaceLowest`, `primaryDark`, `primaryPale`, `secondaryDark`, `tertiarySoft`, `outline`, `info`.

규칙:

- 색은 `AppColors` 토큰으로만 지정한다. `Color(0x...)` hex 직접 입력은 쓰지 않는다.
- Material `Colors.*`는 `Colors.transparent`와 반투명 흑백 오버레이(`Colors.white.withValues(alpha: 0.08)` 같은 것)에만 쓴다.
- 투명도는 `withValues(alpha: ...)`로 준다.

### 2-2. 타이포그래피 (`app_typography.dart`)

폰트는 `pubspec.yaml`에 asset으로 번들한다(`google_fonts` 패키지는 쓰지 않는다). 모든 스타일은 한글 fallback으로 `NotoSansKR`을 갖고 `letterSpacing`은 0이다.

| 스타일 | 폰트 | 크기·굵기 | 주 용도 |
|---|---|---|---|
| `display` | Sora | 36 / w800 | hero 제목 |
| `h1` | Sora | 28 / w700 | 화면 대제목 |
| `h2` | Sora | 22 / w700 | 섹션 제목, 상태 카드 제목 |
| `h3` | Sora | 18 / w700 | 상단 바 제목(시안), 카드 소제목 |
| `body1` | Hanken Grotesk | 16 / w500 | 강조 본문 |
| `body2` | Hanken Grotesk | 14 / w500 | 기본 본문, 입력 필드 |
| `label` | Geist | 12 / w700 | 버튼 라벨, 증감 표시 |
| `caption` | Geist | 11 / w600 | 메타 정보, 칩, 지표 라벨 |
| `number` | Geist | 32 / w800 | 큰 수치 |
| `numberSmall` | Geist | 22 / w800 | 지표 타일 수치 |

크기를 새로 정하지 않는다. 위 스타일에서 고른 뒤 `copyWith`로 색이나 굵기만 바꾼다. `fontSize`를 직접 지정한 곳은 하단 탭 라벨(10) 하나뿐이다.

### 2-3. 간격과 반경 (`app_spacing.dart`)

| `AppSpacing` | 값 | | `AppRadius` | 값 | 쓰는 곳 |
|---|---:|---|---|---:|---|
| `xs` / `sm` | 4 / 8 | | `sm` | 8 | 작은 요소 |
| `md` / `lg` | 16 / 24 | | `md` | 12 | 기본 카드, 이미지, 입력 칸 |
| `xl` / `xxl` | 32 / 48 | | `lg` | 16 | 버튼 |
| `pageHorizontal` | 20 | | `xl` | 24 | 강조 카드, 하단 탭 바 |
| `topBarHeight` | 56 | | `full` | 999 | 칩, 진행 바, 원형 버튼 |
| `bottomNavHeight` | 72 | | | | |
| `bottomContentInset` | 104 | | | | |

- 페이지 좌우 여백은 `pageHorizontal`(20)이다.
- `bottomContentInset`은 떠 있는 하단 탭 바에 콘텐츠가 가려지지 않게 두는 하단 여백이다. `NeoPage`의 기본값이다.
- 수용 보고서에는 "8px 이하 기본 card radius"라고 적혀 있지만, 코드의 기본 카드는 12다. 코드를 따른다.

### 2-4. 장식과 테마

`app_decorations.dart`:

| 이름 | 모양 | 쓰는 곳 |
|---|---|---|
| `cardDecoration` | `surfaceLow` 82% + 흰 10% 테두리 + 옅은 그라데이션, 반경 12 | 기본 카드 |
| `glassCardDecoration` | `surfaceLow` 66% + 시안 20% 테두리 + 시안 glow, 반경 24 | 강조 카드 |
| `primaryButtonDecoration` | 시안 채움 + glow, 반경 16 | 주 버튼 |
| `outlineButtonDecoration` | 투명 + 시안 45% 테두리, 반경 16 | 보조 버튼 |
| `chipDecoration(selected, color)` | 선택 시 색 채움, 아니면 `surfaceHighest` 72% | 칩 |

`app_theme.dart`가 모든 입력 칸의 스타일을 정한다. `surfaceLight` 채움, 반경 12, 힌트 `textDisabled`, 테두리는 기본 `divider`·포커스 시안·오류 빨강이다. 스낵바·카드 테마도 여기서 정한다. 화면에서는 `InputDecoration(hintText: ..., suffixIcon: ...)`처럼 기능 인자만 주고 채움·테두리를 다시 지정하지 않는다. 좁은 칸에 꼭 필요한 `contentPadding` 같은 레이아웃 인자만 예외다(운동 추가의 세트 칸).

---

## 3. 공통 위젯 (`neo_widgets.dart`)

| 위젯 | 용도 | 알아 둘 것 |
|---|---|---|
| `NeoPage` | 스크롤 화면의 뼈대 | SafeArea + 56 높이 상단 바 + 스크롤 + 하단 104 여백. `onRefresh`를 주면 pull-to-refresh가 붙는다 |
| `NeoTopBar` | 상단 바 | 기본은 브랜드 마크 + `AI Health Trainer` + 알림 아이콘. 상세 화면은 `title`과 `showBack: true`. 돌아갈 곳이 없으면 `/dashboard`로 간다 |
| `NeoGlassCard` | 모든 카드의 기본 | 기본은 반경 12. `highlighted: true`면 반경 24와 시안 테두리·glow가 붙는다. 강조는 화면의 핵심 카드에만 쓴다. `onTap`을 주면 InkWell이 붙는다 |
| `NeoStateCard` | 로딩·오류·빈 상태 | 항상 강조 카드다. `actionLabel`과 `onAction`을 함께 주면 주 버튼이 생긴다 |
| `NeoSectionHeader` | 섹션 제목(h2) | 오른쪽에 텍스트 액션을 둘 수 있다 |
| `NeoMetricTile` | 라벨 + 수치 + 단위 + 증감 | 라벨은 대문자 caption으로 보인다 |
| `NeoInfoChip` | 출처·태그·상태 칩 | 최대 2줄, 넘치면 말줄임. `filled`로 채움 |
| `NeoPrimaryButton` | 주 액션 | 높이 48. `onPressed`가 null이면 55% 투명도로 비활성 표시 |
| `NeoOutlineButton` | 보조 액션 | 높이 48 |
| `NeoBottomActionBar` | 상세 화면의 하단 고정 액션 바 | `background` 바탕, 위쪽 `divider` 선, `SafeArea(top: false)`. `errorText`를 주면 버튼 위에 오류 문구(최대 2줄)가 보인다 |
| `NeoProgressBar` | 가로 진행 | 값은 0~1로 자른다. 기본 높이 8 |
| `NeoRing` | 원형 진행 | 가운데에 수치와 라벨 |
| `NeoLineChart` | 추이 선 그래프 | 값이 2개 이상일 때만 그린다. 실제 기록이 있을 때만 쓴다 |
| `NeoAssetImage` | 이미지 | `frontend/assets/stitch/`의 로컬 asset만 쓴다 |

위젯을 둘 위치:

- 화면 하나에서만 쓰면 그 화면 파일의 private 위젯으로 둔다(예: `_SourcesView`).
- 한 기능의 여러 화면에서 쓰면 `features/<기능>/presentation/widgets/`에 둔다(예: `nutrient_bar.dart`).
- 여러 기능에서 쓰면 `neo_widgets.dart`에 추가한다.

---

## 4. 내비게이션과 화면 뼈대

### 4-1. 하단 5탭 (`main_shell.dart`)

| 탭 | 경로 | 화면 |
|---|---|---|
| 홈 | `/dashboard` | 오늘의 진행, 주간 요약 |
| 통계 | `/profile` | 신체 통계, 목표 |
| 플랜 | `/exercise` | 운동 기록 |
| 식단 | `/diet` | 식단 기록 |
| 스캔 | `/diet/analyze` | 음식 사진 AI 분석 |

- 다섯 탭은 같은 폭이다. 바는 반경 24로 화면 아래에 떠 있다.
- 활성 탭은 시안 아이콘과 `primarySoft` 알약 배경으로 표시한다.
- FAB는 없다. `ShellRoute` 안의 화면에서만 탭 바가 보인다.

### 4-2. 라우트와 뼈대 (`app_router.dart`)

| 경로 | 화면 | 탭 바 | 뼈대 |
|---|---|:---:|---|
| `/splash`, `/onboarding` | 스플래시, 온보딩 | | `Scaffold` |
| `/login`, `/register` | 로그인, 회원가입 | | `auth_layout.dart`의 `AuthSurface`·`AuthBrand` |
| `/dashboard`, `/profile`, `/exercise`, `/diet`, `/diet/analyze` | 5탭 | O | `NeoPage` |
| `/dashboard/monthly` | 월간 리포트 | | `NeoPage` |
| `/ai/chat` | AI 코치 채팅 | | 상세 화면 뼈대 + 하단 입력 바 |
| `/diet/add`, `/exercise/add`, `/profile/edit` | 입력 화면 | | 상세 화면 뼈대 + `NeoBottomActionBar` 저장 버튼 |
| `/exercise/recommend` | AI 운동 추천 | | 상세 화면 뼈대 + 하단 고정 액션 바(추천이 있을 때) |
| `/diet/recommend` | AI 식단 추천 | | 상세 화면 뼈대, 액션은 스크롤 안 |

뼈대는 두 가지다.

- **스크롤 화면:** `NeoPage(header: NeoTopBar(...), onRefresh: ..., children: [...])`.
- **상세 화면:** 키보드나 하단 액션이 있는 화면이다. `Scaffold(backgroundColor: AppColors.background)` 안에 `SafeArea`와 `Column`을 두고, 위에서부터 다음 순서로 쌓는다. 입력이 있으면 `resizeToAvoidBottomInset: true`를 준다.
  1. `NeoTopBar(showBack: true)`와 좌우 20 패딩
  2. `Expanded` 스크롤 영역
  3. (있으면) `NeoBottomActionBar`

저장 버튼은 스크롤 끝이나 `Scaffold.bottomNavigationBar`에 두지 않는다. 스크롤 끝에 두면 긴 폼에서 스크롤해야 보이고, `bottomNavigationBar`는 키보드에 가려진다. `Column` 마지막 자식으로 두면 키보드 위에 붙는다.

---

## 5. 상태 표현

| 상태 | 표현 |
|---|---|
| 목록·대시보드 로딩 | `NeoStateCard`(기능 아이콘 또는 `Icons.hourglass_top`, "…불러오는 중") |
| AI 추천 로딩 | `Shimmer` 스켈레톤 |
| 분석·저장 진행 | `LinearProgressIndicator` |
| 오류 | `NeoStateCard(icon: Icons.error_outline, title: '…불러오지 못했습니다', actionLabel: '다시 시도')` |
| 빈 상태 | `NeoStateCard`(예: "아직 기록된 운동이 없습니다")와 다음 행동 |
| 짧은 알림 | `SnackBar`(테마 기본값) |

- API 오류 문구는 repository에서 `core/network/api_error.dart`의 `parseDioApiError`로 만든다. 여기서 AI 오류 코드(`AI_TIMEOUT`, `DAILY_LIMIT_EXCEEDED` 등)가 한국어 문구로 바뀐다.
- 화면에는 예외 원문이나 스택을 보이지 않는다.
- 확인 대화상자와 바텀시트는 지금 쓰지 않는다. 새로 도입하면 이 문서에 패턴을 추가한다.

---

## 6. 데이터 진실성

레퍼런스 화면의 수치를 앱 데이터처럼 복제하지 않는다.

- 체중과 목표 영양은 실제 profile/API 값만 보인다.
- 체중 추이는 실제 weight history가 있을 때만 그린다.
- 체지방, 근육량, 심박, 수면, VO2 Max, 체성분 값이 없으면 `-- / 기록 없음`으로 보인다.
- 실시간 세션 API가 없으므로 타이머, 강도, 심박, 완료율을 꾸며 보이지 않는다.
- 연결 기기 정보가 없으면 `기기 미연결`로 보인다.
- 알레르기와 식단 선호는 임의로 칩을 만들지 않고 프로필 관리 화면으로 연결한다.
- AI 추천·채팅의 출처는 backend가 검증한 `sources`만 칩으로 보인다. 출처가 없으면 없다고 보인다.
- Stitch 레퍼런스의 영문 placeholder와 고정 건강 수치를 남기지 않는다.

---

## 7. 문구

- 사용자 대면 문구는 한국어 합니다체다(예: "프로필 설정이 필요합니다", "잠시 후 다시 시도해 주세요").
- 영문은 브랜드명, 단위, AI/RAG/VO2 Max 같은 표준 약어에만 쓴다.
- 기능 설명 문구를 화면에 늘어놓지 않는다. 화면이 필요로 할 때만 쓴다.
- 짧게 쓴다. Android 실기기에서 설명문 끝의 한두 글자만 다음 줄로 떨어지거나 제목 단어가 어색하게 나뉜 사례가 있었다.

---

## 8. 반응형과 접근성

- 검증 폭은 360×800, 390×844, 430×932다. 키보드가 열린 낮은 화면은 360×600, 텍스트 배율은 1.3을 본다.
- `Row` 안의 텍스트는 `Expanded`나 `Flexible`로 감싸고, 길어질 수 있는 텍스트에는 `maxLines`와 `overflow: TextOverflow.ellipsis`를 준다.
- 탭 바처럼 아이콘만으로 뜻을 전하는 컨트롤에는 `Semantics` 라벨을 둔다.
- 자동 검사는 `frontend/test/*_mobile_layout_test.dart`가 한다.
  - 세 폭에서 화면을 띄우고 `tester.takeException()`이 null인지 본다.
  - 데이터는 `test/support/fake_repositories.dart`의 fake repository와 provider override로 넣는다.
  - 새 화면이나 큰 레이아웃 변경에는 같은 방식의 테스트를 추가한다.
- `frontend/test/input_screen_save_bar_test.dart`는 입력 화면 세 곳을 360×600에서 띄운다. 키보드 inset이 0일 때와 300일 때 모두, 스크롤하지 않아도 저장 버튼이 눌리는지와 키보드에 가려지지 않는지를 본다. 입력 화면을 추가하면 이 목록에 넣는다.

---

## 9. 변경 절차와 사람 확인

1. 공통 위젯이나 테마를 고치기 전에 사용처를 확인한다. `NeoPrimaryButton` 하나가 13개 파일에서 쓰인다. GitNexus `impact` 결과에는 import만 한 파일도 섞이므로 텍스트 검색으로 교차 확인한다.
2. 변경 뒤 `python scripts/verify.py --frontend`를 돌린다. Docker 없이 프론트만 볼 때는 `--frontend-only`를 쓴다.
3. 브라우저에서 실제 화면을 본다.
   - `flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3000`으로 띄우고 390×844에서 확인한다.
   - Flutter web은 canvas에 그리기 때문에 브라우저 도구가 DOM으로 요소를 읽기 어렵다. 스크린샷으로 판단한다.
4. 보고에는 사람이 확인할 화면·상태(로딩/오류/빈/데이터 있음)·폭을 목록으로 적는다. 테스트 통과와 스크린샷은 화면 품질의 증거가 아니다.

하지 않는 것:

- hex 색이나 `fontSize`를 직접 지정하지 않는다.
- `Image.network`나 외부 이미지 URL을 쓰지 않는다.
- 없는 건강 수치를 꾸며 보이지 않는다.
- 새 패키지를 보고 없이 추가하지 않는다. 의존성 목록은 `frontend/pubspec.yaml`이 기준이다.
- 백엔드 API 계약을 화면 작업에서 바꾸지 않는다.

---

## 10. 알려진 불일치

2026-09-25에 코드를 읽고 확인한 항목이다. 정리 여부는 사용자가 정한다. 정리하기 전까지 새 코드는 불일치를 늘리지 않고, 가장 가까운 기존 화면을 따른다.

같은 날 입력 칸 스타일을 테마 한 곳으로 모으고, 입력 화면 세 곳의 저장 버튼 위치를 `NeoBottomActionBar`로 맞췄다. 그 전에는 입력 칸 스타일이 두 가지, 저장 버튼 위치가 세 가지였다.

| 항목 | 현재 상태 |
|---|---|
| AI 운동 추천 하단 바 | `exercise_recommend_screen.dart`가 `NeoBottomActionBar`와 같은 모양의 바를 직접 만든다. 모양 변화 없이 바꿀 수 있다 |
| 프로필 드롭다운 | `profile_edit_screen.dart`의 드롭다운은 테마 입력 칸이 아니라 `DecoratedBox`로 비슷한 모양을 만든다. 텍스트 칸과 높이가 다를 수 있다 |
| 저장 중 라벨 | 프로필 설정만 '저장 중', 식단·운동 추가는 '저장 중...'이다 |
| 입력 오류 표시 | 로그인과 운동 세트 칸은 `InputDecoration.errorText`를 써서 빨간 테두리와 문구가 함께 나온다. 음식명, 운동명, 식단 매크로, 프로필 숫자 칸은 칸 아래에 별도 `Text`로 문구만 붙이므로 테두리가 바뀌지 않는다 |
| 기본 카드 반경 | 수용 보고서는 "8px 이하"라고 적었지만 코드는 12다 |
| 로딩 표시 | `profile_edit_screen.dart`만 `CircularProgressIndicator`를 쓴다 |
| 쓰지 않는 토큰 | §2-1의 7개 |
| 쓰지 않는 의존성 | `lottie`, `cached_network_image`가 `pubspec.yaml`에 있지만 `lib/`에서 쓰지 않는다 |
