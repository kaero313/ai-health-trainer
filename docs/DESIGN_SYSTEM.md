# AI Health Trainer - Design System (초안)

> **상태:** 부분 확정. §19의 결정 10개는 2026-09-26에 사용자가 확정했다. 나머지 값(토큰 세부, 스케일, 컴포넌트 규칙)은 Theme Preview로 확인한 뒤 확정한다. 확정 전에는 이 문서를 근거로 실제 화면을 고치지 않는다.
> **대상:** lead·frontend 역할과 사용자 본인
> **범위:** 기능, 화면 정보 구조, 사용자 플로우는 유지하고 시각 체계만 바꾼다.
> **근거:**
> - `screenshots/2026-09-25/` 캡처 26장(390폭, 다크)
> - `frontend/lib/` 코드
> - `shadcn_ui 0.57.1` 소스(Flutter 3.41.9)
> **관계:** 현재 구현 기준 문서는 `docs/FLUTTER_UI_DESIGN.md`이고, 이 문서는 옮겨 갈 목표다. 확정되면 `FLUTTER_UI_DESIGN.md`를 이 문서 기준으로 다시 쓴다.
> **Last updated:** 2026-10-03

---

## 1. 현재 디자인 분석

### 1-1. 공통 UI 패턴

| 패턴 | 나오는 곳 | 현재 구현 | 관찰 |
|---|---|---|---|
| 헤더 | 모든 화면 | `NeoTopBar` | 탭 화면마다 브랜드 워드마크(홈·통계·식단·스캔)나 화면 제목(플랜)이 섞여 있다. 오른쪽 알림 아이콘은 누를 수 없는 장식이다 |
| 페이지 제목 | 탭 화면 | 큰 제목 + 설명 한 줄 | 제목은 가늘게 보이고, 설명문이 모든 화면에 반복된다 |
| 강조 카드 | 홈·통계·플랜·식단·스캔·채팅 | `NeoGlassCard(highlighted)` | 시안 테두리, glow, 그라데이션, blur가 한 화면에 2~3개씩 있다 |
| 기본 카드 | 전 화면 | `NeoGlassCard` | 반경 12. 강조 카드는 24라 같은 목록 안에서 반경이 섞인다 |
| AI 코치 카드 | 홈·플랜·식단 | 강조 카드 + 채운 버튼 | 거의 같은 카드가 세 화면에 있다. 플랜 화면에는 AI 진입점이 3개(링크, 카드 2버튼, 하단 버튼)다 |
| 채운 버튼 | 전 화면 | `NeoPrimaryButton` | 시안 채움 + glow. 한 화면에 2~3개가 동시에 보인다(플랜: 운동 기록 시작, 루틴 추천, 운동 추가) |
| 외곽선 버튼 | 하단 버튼 줄 | `NeoOutlineButton` | 채운 버튼과 반씩 나란히 둔다 |
| 칩·배지 | 전 화면 | `NeoInfoChip` | 시안·라임·오렌지 테두리 칩이 수치, 상태, 분류를 모두 표현한다. 식단 카드 하나에 칩이 4개 있다 |
| 필터 칩 | 플랜(근육군) | 커스텀 | 선택된 칩을 시안으로 채운다 |
| 입력 칸 | 인증·식단 추가·운동 추가·프로필 | `TextField` + 테마 | 프로필 숫자 칸은 값을 입력하면 무엇을 입력하는 칸인지 보이지 않는다(라벨 없음). 오류 표시는 두 방식이 섞여 있다 |
| 드롭다운·날짜 | 입력 화면 | Material `DropdownButtonFormField`, `showDatePicker` | 입력 칸과 모양이 비슷하지만 따로 구현되어 있다 |
| 리스트 행 | 통계(활력·체성분), 식단(기준 관리) | 카드 안 Row | 라벨 왼쪽, "-- / 기록 없음" 오른쪽 2줄로 정렬이 불규칙하다 |
| 표 | 플랜(세트) | Row 반복 | 무게 열만 시안으로 칠했다 |
| 타임라인 | 식단 | 카드 + 세로 연결선 | 구조는 좋다. 연결선 색이 들쭉날쭉하다 |
| 진행 링 | 홈 | `NeoRing` | 굵기 16으로 무겁다. 중앙 숫자는 잘 읽힌다 |
| 진행 바 | 홈·식단 | `NeoProgressBar` | 시안·라임·오렌지 |
| 선 차트 | 홈(체중), 통계(체중 추이) | `NeoLineChart` | 축, 값, 날짜가 없고 그라데이션 면만 있어서 수치를 읽을 수 없다 |
| 막대 차트 | 홈(주간 일관성) | 커스텀 | 두꺼운 색 블록 2줄이고 축과 범례가 없다 |
| 월간 차트 | 월간 리포트 | `fl_chart` | 곡선 보간 때문에 실제 데이터에 없는 진동이 그려진다. y축 라벨이 겹친다("200/204") |
| 이미지 카드 | 홈(오늘 운동), 통계(연결 기기), 스캔, 로그인 배경, 온보딩 | `NeoAssetImage` | 데이터 카드에 장식용 사진이 들어간다 |
| 하단 탭 | 탭 화면 | `MainShell` | 떠 있는 둥근 바(반경 24)에 그림자가 무겁다 |
| 하단 고정 액션 | 입력 화면 | `NeoBottomActionBar` | 2026-09-25에 통일했다 |
| 상태 카드 | 로딩·오류·빈 상태 | `NeoStateCard` | 강조 카드라 오류도 glow가 난다 |
| 스켈레톤 | AI 추천 로딩 | `Shimmer` | 무난하다 |
| 세그먼트 탭 | 채팅 | 커스텀 | 선택된 탭을 시안으로 채운다 |

### 1-2. 유지할 것

- 브랜드 정체성: 시안 Primary, 다크 우선 분위기, 브랜드 마크와 워드마크.
- 정보 구조와 순서: 홈(오늘 진행 → 체중 → 영양 → 오늘 운동 → 주간 일관성 → AI 코치 → 월간 리포트)과 하단 5탭(홈·통계·플랜·식단·스캔).
- 데이터 진실성 정책: 없는 값은 `-- / 기록 없음`으로 보이고, AI 출처는 검증된 `sources`만 보인다.
- 좋은 구조: 하루 목표 진행 링, 매크로 분해, 식사 타임라인, 세트 표, 입력 화면의 하단 고정 저장 바.
- 한국어 합니다체 문구와 페이지 좌우 여백 20.

### 1-3. 개선할 것

1. **Accent 남용.** 시안·라임·오렌지가 제목, 칩, 숫자, 버튼, 차트에 동시에 쓰여 강조가 강조로 읽히지 않는다.
2. **장식 효과.** glow, 그라데이션, blur, 순검정 배경의 네온 대비를 걷어낸다.
3. **CTA 경쟁.** 한 화면에 채운 버튼이 여러 개다. AI 진입점도 중복된다.
4. **헤더 불일치.** 브랜드 워드마크와 화면 제목이 섞여 있고, 알림 아이콘은 기능이 없다.
5. **타이포그래피.** 폰트 가족이 4개(Sora·Hanken Grotesk·Geist·Noto Sans KR)이고, 한글은 fallback으로 그려진다. 크기와 굵기가 화면마다 다르다.
6. **차트 가독성.** 축·값·범례가 없고, 곡선 보간이 데이터를 왜곡한다. 수치 텍스트를 시리즈 색으로 칠한다.
7. **반경 혼재.** 비슷한 요소가 8·12·16·24·full로 제각각이다.
8. **칩 과다.** 정보 칩이 테두리 색으로 의미를 나른다.
9. **장식 사진.** 데이터 카드 안의 스톡 사진이 정보 없이 공간을 차지한다.
10. **폼 가독성.** 숫자 칸의 라벨이 사라지고, 오류 표시 방식이 두 가지다.
11. **하단 탭.** 떠 있는 바와 무거운 그림자 때문에 웹 대시보드처럼 보인다.
12. **라이트 모드 없음.** 색이 정적 상수라 테마를 따라가지 않는다(`AppColors.` 343곳).

---

## 2. 원칙

1. **데이터가 먼저다.** 숫자는 가장 크고 선명하게 보이고, 장식은 숫자를 가리지 않는다.
2. **Accent는 드물게 쓴다.** 시안은 화면의 주 CTA 하나, 핵심 진행 표시, 선택 상태에만 쓴다(§3-4).
3. **한 디자인, 두 테마.** Light와 Dark는 같은 토큰 이름에 값만 다르다. 화면 코드는 hex를 모르고 토큰만 쓴다.
4. **정해진 값만 쓴다.** 크기·간격·반경·색은 이 문서의 스케일에서만 고른다. 화면마다 임의로 값을 만들지 않는다.
5. **모바일 네이티브.** 붙어 있는 하단 탭, 큰 제목, 48 이상의 터치 영역, 시스템 제스처를 존중한다. 웹 대시보드식 격자와 hover 전제 UI를 쓰지 않는다.
6. **효과를 절제한다.** 면은 단색이고 경계는 1px 선으로 나눈다. 그림자는 떠 있는 레이어(시트, 토스트, 팝오버)에만 쓴다.
7. **색만으로 의미를 전하지 않는다.** 상태는 아이콘과 문구를 함께 쓰고, 차트는 범례나 직접 라벨을 함께 쓴다.

---

## 3. 색 토큰

### 3-1. 구조

- `shadcn_ui 0.57.1`의 `ShadColorScheme` 기본 토큰 20개를 그대로 쓴다.
- 앱 전용 토큰은 `ShadColorScheme.custom` 맵에 넣고, `ShadColorScheme` 확장 getter로 읽는다(예: `colorScheme.success`).
- 대비는 `dataviz` 스킬의 `contrast()`로 계산했다(WCAG 2.x). 기준은 본문 4.5:1, 큰 글자와 UI 경계 3:1이다.
- shadcn의 `accent` 토큰은 hover·눌림 배경을 뜻하는 **중립색**이다. 브랜드 강조색이 아니다. 브랜드 시안은 `primary`다.

### 3-2. 기본 토큰 (shadcn)

| 토큰 | 용도 | Light | Dark | 대비 (Light / Dark) |
|---|---|---|---|---|
| `background` | 페이지 배경 | `#F4F4F5` | `#09090B` | |
| `foreground` | 본문·제목·핵심 숫자 | `#09090B` | `#FAFAFA` | 18.1 / 19.1 (배경) |
| `card` | 카드 면 | `#FFFFFF` | `#18181B` | |
| `cardForeground` | 카드 안 본문 | `#09090B` | `#FAFAFA` | 19.9 / 17.0 |
| `popover` / `popoverForeground` | 시트·팝오버·토스트 | `#FFFFFF` / `#09090B` | `#18181B` / `#FAFAFA` | |
| `primary` | 주 CTA, 진행 표시, 선택 상태, 링크 | `#0E7490` | `#22D3EE` | 텍스트로 5.36 / 9.80 (카드) |
| `primaryForeground` | primary 위 글자 | `#FFFFFF` | `#083344` | 5.36 / 7.41 |
| `secondary` / `secondaryForeground` | 보조 버튼 면 | `#E4E4E7` / `#18181B` | `#27272A` / `#FAFAFA` | 글자 13.96 / 14.27 (확정 2026-10-03) |
| `muted` | 트랙, 세그먼트, 스켈레톤, 비활성 면 | `#E4E4E7` | `#27272A` | mutedForeground 글자 4.55 / 5.81 (확정 2026-10-03) |
| `mutedForeground` | 보조 텍스트, 라벨, 축 | `#65656E` | `#A1A1AA` | 5.25 (배경) / 6.91 (카드) |
| `accent` / `accentForeground` | 눌림·hover 배경 | `#E4E4E7` / `#18181B` | `#27272A` / `#FAFAFA` | 확정 2026-10-03 |
| `destructive` | 삭제 버튼 면 (오류 글자는 `error`, §3-3) | `#DC2626` | `#DC2626` | 확정 2026-10-03 |
| `destructiveForeground` | destructive 위 글자 | `#FFFFFF` | `#FFFFFF` | 4.83 / 4.83 |
| `border` | 카드 외곽선, 구분선 | `#E4E4E7` | `#27272A` | 장식선 |
| `input` | 입력 칸 테두리 | `#8A8A93` | `#71717A` | 3.42 / 3.67 (UI 3:1) |
| `ring` | 포커스 링 | `#0E7490` | `#22D3EE` | |
| `selection` | 텍스트 선택 | `#0E7490` 20% | `#22D3EE` 30% | |

**은은한 면 규칙:** `muted`·`secondary`·`accent`는 페이지 배경과 카드 양쪽에서 구분되어야 한다.
- 대비 1.1 이상이고, 테스트로 고정했다.
- shadcn은 흰 배경을 전제로 이 면들을 `#F4F4F5`로 둔다. 이 앱은 페이지 배경이 `#F4F4F5`라서, Light는 한 단계 진한 `#E4E4E7`을 쓴다.
- Light는 배경 대비 1.15, 카드 대비 1.27이고, Dark `#27272A`는 1.34 / 1.19다.

라이트 `primary`는 시안 계열 중 흰 글자와 4.5:1을 넘는 가장 밝은 단계(cyan-700)다. cyan-600(`#0891B2`)은 흰 글자와 3.68이라 버튼 라벨로 쓸 수 없다.

### 3-3. 앱 확장 토큰 (`custom`)

| 토큰 | 용도 | Light | Dark |
|---|---|---|---|
| `primaryMuted` | 선택된 탭 표시, 선택 필터 배경 | `#ECFEFF` (primary 글자 5.15) | `#0B2B33` (primary 글자 8.26) |
| `success` / `successMuted` | 성공 아이콘·글자 / 배지·알림 배경 | `#15803D` / `#F0FDF4` | `#4ADE80` / `#4ADE80` 12% |
| `warning` / `warningMuted` | 주의 | `#B45309` / `#FFFBEB` | `#FBBF24` / `#FBBF24` 12% |
| `info` / `infoMuted` | 안내 | `#1D4ED8` / `#EFF6FF` | `#60A5FA` / `#60A5FA` 12% |
| `error` | 오류 글자·아이콘·입력 오류 테두리 | `#DC2626` (카드 4.83) | `#F87171` (카드 6.40) |
| `errorMuted` | 오류 배경 | `#FEF2F2` | `#F87171` 12% |
| `chartGrid` | 차트 격자·기준선 | `#E4E4E7` | `#27272A` |
| `chartKcal` … `chartExercise` | 차트 시리즈 | §12-2 | §12-2 |

상태 글자색 대비(카드 위)는 Light가 success 5.02, warning 5.02, info 6.70이고, Dark가 success 10.17, warning 10.61, info 6.97이다.

### 3-4. Accent(시안) 사용 규칙

**쓰는 곳:**
- 화면의 **주 CTA 1개**
- 핵심 진행 표시(오늘 열량 목표 링, 열량 진행 바)
- 선택 상태(하단 탭, 필터, 세그먼트)
- 텍스트 링크와 포커스 링

**쓰지 않는 곳:**
- 제목
- 일반 수치 텍스트
- 정보 칩
- 표의 열
- 헤더 워드마크(스플래시·로그인·온보딩의 브랜드 표기는 예외)
- 카드 테두리

핵심 수치는 `foreground`로 크게 쓴다. 색을 칠해서 강조하지 않고 크기와 굵기로 강조한다.

---

## 4. 타이포그래피

### 4-1. 폰트

| 역할 | 폰트 | 이유 |
|---|---|---|
| UI 텍스트(한글·영문) | **Noto Sans KR** (앱 asset) | 화면 대부분이 한글이다. fallback이 아니라 기본 폰트로 지정해 굵기와 행간을 직접 제어한다 |
| 숫자·단위 | **Geist** (`shadcn_ui` 번들 `packages/shadcn_ui/Geist`) | 데이터 가독성. 표·축·세로 정렬 숫자에는 `FontFeature.tabularFigures()` |
| 브랜드 워드마크 | 로고 이미지나 현행 유지 | 타입 스케일 밖 |

Sora와 Hanken Grotesk는 새 스케일에서 쓰지 않는다. asset 제거는 전환이 끝난 뒤 따로 정한다(§19).

### 4-2. 스케일

크기와 행간은 논리 픽셀, 굵기는 400·500·600·700만 쓴다.

| 토큰 | 크기/행간 | 굵기 | 폰트 | 용도 | `ShadTextTheme` 매핑 |
|---|---|---|---|---|---|
| `display` | 28/36 | 700 | Noto Sans KR | 탭 루트 화면의 큰 제목(인사말) | `h1` |
| `title` | 20/28 | 700 | Noto Sans KR | 상세 화면 제목, 시트·다이얼로그 제목 | `h2` |
| `heading` | 17/24 | 600 | Noto Sans KR | 카드·섹션 제목 | `h3`, `h4` |
| `body` | 15/22 | 400 | Noto Sans KR | 본문, 입력 값 | `p`, `list`, `blockquote` |
| `bodyStrong` | 15/22 | 600 | Noto Sans KR | 리스트 항목 제목, 버튼 라벨 | `large` |
| `bodySmall` | 13/18 | 400 | Noto Sans KR | 보조 설명, 도움말, 오류 문구 | `small`, `muted`(색은 `mutedForeground`) |
| `caption` | 12/16 | 500 | Noto Sans KR | 라벨, 배지, 탭 라벨, 범례 | `custom['caption']` |
| `numHero` | 40/44 | 700 | Geist | 화면당 핵심 수치 1개 | `h1Large`, `custom['numHero']` |
| `numLarge` | 28/32 | 700 | Geist | 스탯 타일 수치, 링 중앙 | `custom['numLarge']` |
| `numMedium` | 20/24 | 600 | Geist | 카드 안 보조 수치 | `custom['numMedium']` |
| `numSmall` | 13/16 | 500 | Geist tabular | 표, 축 눈금, 세트 기록 | `table`, `custom['numSmall']` |

규칙:
- 단위(kg, kcal, g)는 숫자보다 한 단계 작게 쓰고 `mutedForeground`로 칠한다. 예: `numHero` 72.4 + `body` kg.
- 천 단위 구분 기호를 쓴다(1,185).
- 큰 단독 수치는 비례 숫자, 세로로 줄 맞추는 숫자는 tabular 숫자를 쓴다.
- 제목은 왼쪽 정렬이 기본이다. 가운데 정렬은 빈 상태와 스플래시에만 쓴다.
- 한 카드 안에 크기를 3단계 넘게 섞지 않는다. 단계는 아래처럼 센다(2026-10-04 확정, §19 C).
  - 숫자와 그 단위는 한 단계다. 값이 없을 때 그 자리에 쓰는 muted 문구("기록 없음")도 같은 단계다.
  - `caption`(12)과 `numSmall`(13)은 같은 "작은 글자" 단계다. 차트 축과 진행 바 라벨·값이 여기에 든다.
  - 화면 대표 카드(안쪽 여백 20) 1개만 4단계까지 쓴다. 예: 오늘의 진행 = 제목, 링 중앙 수치, 열량 수치+단위, 작은 글자.

---

## 5. 간격

4의 배수만 쓴다. 토큰 이름은 값 그대로다. 기존 `AppSpacing.md`=16과 헷갈리지 않게 이름을 새로 정했다.

| 토큰 | 값 | 주 용도 |
|---|---:|---|
| `s4` | 4 | 아이콘과 글자 사이, 숫자와 단위 사이 |
| `s8` | 8 | 라벨과 값, 배지 사이, 칩 사이 |
| `s12` | 12 | 카드와 카드 사이, 카드 안 행 사이 |
| `s16` | 16 | 카드 안쪽 여백, 카드 안 블록 사이 |
| `s20` | 20 | 페이지 좌우 여백, 강조 카드 안쪽 여백 |
| `s24` | 24 | 섹션과 섹션 사이 |
| `s32` | 32 | 화면 상단 제목 블록 아래 |
| `s48` | 48 | 빈 상태 위아래 |

레이아웃 규칙:
- 페이지 좌우 여백은 20이다.
- 카드 안쪽 여백은 16이고, 화면의 대표 카드 1개만 20이다.
- 카드 사이는 12, 섹션 제목 위는 24다.
- 터치 영역은 최소 48×48이다. 시각 크기가 작아도 hit 영역은 48을 확보한다.
- 리스트 행 높이는 한 줄이면 48, 두 줄이면 64다.
- 탭 화면은 콘텐츠가 붙은 하단 탭 뒤까지 이어지고(`extendBody`), 스크롤 끝 여백은 하단 탭 높이(64 + 하단 safe area) + 16이다. 그래서 마지막 카드와 탭 사이에 16이 보인다. 하단 탭이 없는 화면은 safe area + 16이다.

---

## 6. 반경

| 토큰 | 값 | 대상 |
|---|---:|---|
| `radiusSm` | 8 | 작은 썸네일, 아이콘 타일 안쪽 |
| `radius` | 12 | 버튼, 입력 칸, 셀렉트, 팝오버, 아이콘 타일, 스켈레톤. **`ShadThemeData.radius`** |
| `radiusLg` | 16 | 카드, 이미지 카드, 리스트 그룹 |
| `radiusXl` | 24 | 바텀시트 윗모서리 |
| `radiusFull` | 999 | 배지, 필터 칩, 진행 바, 아바타, 탭 선택 표시 |

같은 종류의 요소는 같은 반경을 쓴다. 카드는 강조 여부와 관계없이 16이다.

---

## 7. 면, 경계, 효과

- 카드는 `card` 면 + 1px `border` 외곽선이다. 그림자, glow, 그라데이션, `BackdropFilter`는 쓰지 않는다.
- 레이어 위계는 `background` < `card` < `popover`(시트·토스트, 그림자 1단계) 순서다.
- 떠 있는 레이어의 그림자는 한 가지뿐이다. Light는 `0 8 24 rgba(0,0,0,0.08)`, Dark는 그림자 없이 `border`로 구분한다.
- 구분선은 1px `border`다. 카드 안 표 행 사이에만 쓴다.
- 단순 장식용 사진은 데이터 카드에서 없앤다. 음식 사진, 운동 동작 콘텐츠처럼 이미지 자체가 정보인 경우는 유지한다. 온보딩은 예외다. (확정 §19-3)

---

## 8. 버튼

| 변형 | 용도 | 모양 | shadcn |
|---|---|---|---|
| Primary | 화면의 주 행동 **1개**(저장, 기록 시작, AI 코치에게 질문) | `primary` 면 / `primaryForeground` 글자 | `ShadButton()` |
| Secondary | 보조 행동(같은 영역에 주 행동이 있을 때) | `secondary` 면 | `ShadButton.secondary()` |
| Outline | 대등한 두 선택지 중 두 번째, 카드 안 이동 | 1px `input` 테두리, 투명 면 | `ShadButton.outline()` |
| Ghost | 헤더 액션, 카드 오른쪽 위 액션(`AppCardAction`), 리스트 안 작은 동작 | 면 없음, `foreground` 글자, 눌림 시 `accent` | `ShadButton.ghost()` |
| Link | 섹션 제목 오른쪽 "전체 보기" 등. 카드 헤더에는 쓰지 않는다(§9) | `primary` 글자 | `ShadButton.link()` |
| Destructive | 삭제, 로그아웃 확인 | `destructive` 면 | `ShadButton.destructive()` |

| 크기 | 높이 | 좌우 여백 | 라벨 | 용도 |
|---|---:|---:|---|---|
| default | 48 | 16 | `bodyStrong` 15/600 | 하단 고정 CTA, 폼 제출, 전체 폭 버튼 |
| compact | 40 | 12 | 14/600 | 카드 안 버튼 |
| icon | 48 × 48 | - | 아이콘 20 | 헤더 뒤로가기, 삭제, 더보기. Ghost라 평소에는 면이 보이지 않는다 |

`ShadThemeData.buttonSizesTheme`(`ShadButtonSizesTheme`)으로 `regular`를 48, `sm`을 40, `icon`을 48×48로 덮어쓴다. shadcn 기본값은 regular 40, sm 36, lg 44다. 구현은 `lib/core/design_system/app_shad_theme.dart`에 있다.

규칙:
- 한 화면에 보이는 Primary 버튼은 1개다. 스크롤해서 새로 나타나는 영역도 같은 흐름이면 1개로 센다.
- 두 버튼을 나란히 둘 때는 Outline + Primary이고, Primary가 오른쪽이다. 하단 고정 바에는 Primary 1개를 전체 폭으로 둔다.
- 아이콘은 라벨 왼쪽 18 크기, 아이콘만 있는 버튼은 20 크기이며 접근성 라벨이 필수다.
- glow, 그림자, 그라데이션을 쓰지 않는다. 비활성은 투명도 0.5에 터치 차단이다.
- 로딩은 라벨 자리에 16 크기 인디케이터를 두고, 버튼 폭을 유지한다.

---

## 9. 카드

모든 카드는 `ShadCard` 기반의 한 가지 모양이다.

| 속성 | 값 |
|---|---|
| 면 / 경계 | `card` / 1px `border` |
| 반경 | 16 |
| 안쪽 여백 | 16 (화면 대표 카드 1개만 20) |
| 헤더 | 왼쪽 `heading` 제목, 오른쪽 배지 1개나 Ghost 이동 액션(`AppCardAction`) 1개. 액션은 보이는 높이 40, 누르는 영역 48(위아래 4는 카드 여백 쪽으로 넘친다) |
| 본문 블록 간격 | 16 |
| 눌리는 카드 | 카드 전체가 눌리면 오른쪽 끝에 chevron을 두고 눌림 시 `accent` 면 |

카드 종류:

| 종류 | 구성 | 예 |
|---|---|---|
| Summary | 제목 + 핵심 수치(`numHero`·`numLarge`) + 보조 수치 + 선택적 차트 | 오늘의 진행, 체중, 영양 |
| List | 제목 + 행 목록(구분선) | 활력 지표, 신체 구성, 세트 표 |
| Action | 아이콘 + 제목 + 한 줄 설명 + 버튼 1개 | AI 코치 |
| Nav row | 아이콘 + 제목 + chevron | 월간 리포트 보기, 식단 기준 관리 |

규칙:
- "강조 카드"라는 변형은 없다. 강조는 카드 안 숫자 크기와 accent 진행 표시로 한다.
- 카드 안에 카드를 넣지 않는다. 묶음이 필요하면 구분선이나 `muted` 면의 블록을 쓴다.
- 같은 화면에서 같은 목적의 카드(AI 코치)는 1개다.

---

## 10. 입력

| 항목 | 규칙 | shadcn |
|---|---|---|
| 필드 구성 | 위에 라벨(`bodySmall` 600, `foreground`) → 입력 칸 → 아래 도움말이나 오류(`bodySmall`) | `ShadInputFormField(label:, description:)` |
| 입력 칸 | 높이 48, 반경 12, 면은 `card`, 테두리 1px `input`, 값은 `body`, placeholder는 `mutedForeground` | `ShadInput` |
| 포커스 | 2px `ring` | 기본 |
| 오류 | 테두리 `error` + 아래 오류 문구 `error` + 앞에 `circle-x` 아이콘 | `ShadForm` 검증 |
| 숫자 | 숫자 키보드, 단위는 칸 안 오른쪽 접미사(kg·g·kcal·cm·세) | `trailing` |
| 선택 | 입력 칸과 같은 높이·반경·**폭**. 0.57.1은 내용 폭이 기본이라 부모 폭을 `minWidth`로 넘긴다(`LayoutBuilder`) | `ShadSelectFormField(minWidth:)` |
| 날짜 | 입력 칸과 같은 모양 | `ShadDatePickerFormField` |
| 여러 줄 | 최소 3줄 | `ShadTextareaFormField` |
| 체크 | 한 줄 전체가 눌리는 행 | `ShadCheckboxFormField` |
| 태그 입력 | 입력 칸 + 추가 버튼, 아래에 삭제 가능한 배지 | Custom `TagInput` |

규칙:
- 라벨은 **항상 보인다.** placeholder를 라벨 대신 쓰지 않는다. 지금 프로필 숫자 칸이 여기에 해당한다.
- 오류는 한 가지 방식만 쓴다: 테두리 + 문구 + 아이콘. 칸 아래에 문구만 붙이는 방식은 없앤다.
- 필드 사이 간격은 16, 필드 그룹(섹션) 사이는 24다.
- 저장 버튼은 입력 화면 하단 고정 바의 Primary 1개다(현행 유지).

---

## 11. 내비게이션

### 11-1. 하단 탭

- 5탭(홈·통계·플랜·식단·스캔)과 순서는 유지한다.
- 화면 아래에 **붙은 바**다. 떠 있는 둥근 바와 그림자는 없앤다(확정 §19-2).
  - 높이는 64에 하단 safe area를 더한다. iOS 홈 인디케이터, Android 제스처 바·3버튼 바 영역만큼 바 면이 아래로 이어지고, 아이콘과 라벨은 그 위 64 안에 둔다.
  - 면은 `card`, 위쪽에 1px `border`다.
- 항목은 아이콘 24 + `caption` 라벨이고 라벨은 항상 보인다.
- 선택 상태는 아이콘과 라벨이 `primary`이고, 아이콘 뒤에 `primaryMuted` 알약(56×32, 반경 full)을 둔다. 비선택은 `mutedForeground`다.
- 탭 전환에는 애니메이션을 쓰지 않는다. 선택 표시만 150ms로 바뀐다.

### 11-2. 헤더

| 종류 | 구성 | 적용 |
|---|---|---|
| Root | 왼쪽 `display` 큰 제목 + 아래 `bodySmall` 부제(선택), 오른쪽 Ghost 아이콘 액션(선택) | 5탭 루트 화면 |
| Detail | 왼쪽 뒤로가기(icon 버튼) + `title` 제목, 오른쪽 Ghost 액션(선택) | 상세·입력·AI 화면 |

규칙:
- 브랜드 워드마크는 스플래시·온보딩·로그인·회원가입에만 둔다. 탭 화면 헤더에는 화면 제목을 둔다.
- 기능 없는 아이콘을 두지 않는다. 지금의 알림 아이콘은 없앤다. 알림 기능이 생기면 다시 넣는다.
- 뒤로가기 버튼은 테두리 원 없이 Ghost 아이콘 버튼으로 둔다.

### 11-3. 화면 안 내비게이션

| 요소 | 규칙 | 구현 |
|---|---|---|
| 세그먼트(채팅 전체/식단/운동) | `muted` 트랙 + 선택 항목 `card` 면. 시안으로 채우지 않는다 | `ShadTabs` |
| 필터(근육군) | 가로 스크롤 칩. 선택 칩은 `primaryMuted` 면 + `primary` 글자, 비선택은 1px `border` | Custom `FilterChipBar` |
| 날짜 이동 | 가운데 날짜(`heading`) + 좌우 Ghost 아이콘 버튼 | Custom `DateStepper` |
| 월 이동(월간 리포트) | 같은 `DateStepper`를 월 단위로 | Custom |

---

## 12. 차트

### 12-1. 형식

| 데이터의 역할 | 형식 | 현재 → 변경 |
|---|---|---|
| 목표 대비 하루 진행 1개 | 진행 링 | 링 두께 16 → 10, 중앙 `numLarge` + `caption` |
| 목표 대비 여러 항목 | 가로 진행 바 | 높이 6, 값은 막대 위 텍스트 |
| 시간에 따른 변화(체중, 일별 열량) | 선 차트 | 축·눈금 추가, 곡선 보간 금지 |
| 여러 영양소 추이 | 선 차트 여러 개 또는 작은 차트 나열 | 범례 + 끝점 직접 라벨 |
| 요일별 달성 여부 | 요일 격자(점이나 얇은 막대) | 두꺼운 색 블록 2줄 → 요일별 두 개 점 + 범례 |
| 단일 수치 | 차트가 아니라 스탯 타일 | 현행 유지 |

### 12-2. 시리즈 색 (검증됨, 두 모드 공통)

색은 **데이터의 대상**을 따른다. 순위나 순서로 칠하지 않는다.

| 대상 | 토큰 | hex | Light 대비(카드) | Dark 대비(카드) |
|---|---|---|---:|---:|
| 식단·섭취 열량, 단일 시리즈 기본 | `chartKcal` | `#0891B2` | 3.68 | 4.81 |
| 단백질 | `chartProtein` | `#7C3AED` | 5.70 | 3.11 |
| 탄수화물 | `chartCarbs` | `#D97706` | 3.19 | 5.56 |
| 지방 | `chartFat` | `#DB2777` | 4.60 | 3.85 |
| 운동 | `chartExercise` | `#65A30D` | 3.09 | 5.74 |

검증 결과(`dataviz` 스킬 `validate_palette.js`, 모든 쌍 기준):
- {열량, 단백질, 탄수화물, 지방}: 색각 이상 시뮬레이션 ΔE 최저 10.3(목표 8 이상), 정상 시각 ΔE 최저 20.3(하한 15 이상), 명도 범위 통과. Light·Dark 모두 통과했다.
- {열량, 운동}: 모든 검사를 통과했다.
- 운동과 매크로는 같은 차트에 함께 두지 않는다. 이 조합은 검증하지 않았다.

차트 시리즈 색은 UI의 `primary`와 다르다. 다크의 `primary`(`#22D3EE`)는 차트 명도 범위를 벗어나서 면적 표시에 쓰면 눈부시다. 진행 링과 진행 바처럼 "목표 대비 진행" 표시는 UI `primary`를 쓴다.

### 12-3. 표시 규칙

- **선:** 굵기 2, 곡선 보간 금지(`isCurved: false` 또는 `preventCurveOverShooting: true`). 면 채우기는 단일 시리즈에서만 투명도 10% 이하로 쓴다.
- **점:** 기본은 숨긴다. 마지막 값과 선택한 값만 8 크기 점 + 2px `card` 테두리 고리로 보인다.
- **격자:** 가로선만, 1px `chartGrid`, 실선이다. 점선은 쓰지 않는다. 눈금은 3~4개다.
- **축:** 라벨은 `numSmall`, `mutedForeground`다. y축은 최솟값·최댓값·중간값만 보인다. x축은 시작·끝과 3~5개 날짜만 보인다. 라벨이 겹치면 줄인다.
- **값 표시:**
  - 차트 위에 핵심 수치(현재값, 변화량)를 텍스트로 먼저 보인다. 탭하면 툴팁으로 해당 날짜의 값을 보인다.
  - 툴팁만으로 값을 알 수 있게 하지 않는다.
- **범례:** 시리즈가 2개 이상이면 항상 둔다(색 점 + `caption`). 4개 이하면 끝점에 직접 라벨을 붙인다.
- **텍스트 색:** 수치와 라벨 글자는 `foreground`·`mutedForeground`로 쓴다. 시리즈 색은 선·막대·점에만 쓰고 글자에는 쓰지 않는다.
- **데이터 부족:** 값이 2개 미만이면 선을 그리지 않고 "기록이 2개 이상 쌓이면 추이를 보여드립니다"를 보인다. 데이터 진실성 정책을 따른다.
- **축은 하나다.** 단위가 다른 두 값을 한 차트에 겹치지 않는다(이중 축 금지).
- 차트 높이는 축 라벨 영역을 포함해 잡는다. 카드 안에서 따로 스크롤되지 않게 한다.

### 12-4. 진행 표시

- **진행 링:** 트랙은 `muted`, 진행은 `primary`, 두께 10, 끝 모양 둥글게. 100%를 넘으면 링은 가득 찬 상태로 두고, 아래에 warning 배지(아이콘 + "320kcal 초과")를 보인다.
- **진행 바:** 높이 6, 반경 full, 트랙은 `muted`, 채움은 대상 색(매크로)이나 `primary`(열량)다. 라벨과 값은 막대 위 한 줄에 둔다(`caption` 라벨, `numSmall` 값).

---

## 13. 상태 표현

### 13-1. 네 가지 상태

| 상태 | 글자·아이콘 | 배경 | 아이콘(Lucide) | 쓰는 곳 |
|---|---|---|---|---|
| success | `success` | `successMuted` | `circle-check` | 저장 완료 토스트, 목표 달성 배지 |
| warning | `warning` | `warningMuted` | `triangle-alert` | 목표 초과, AI 일일 한도 임박·초과 |
| error | `error` | `errorMuted` | `circle-x` | 저장·분석 실패, 네트워크 오류, 입력 오류 |
| info | `info` | `infoMuted` | `info` | 안내, 새 기능, AI 응답 출처 설명 |

규칙:
- 상태는 **아이콘 + 문구**로 보인다. 색만으로 상태를 전하지 않는다.
- 상태 색은 차트 시리즈에 쓰지 않고, 시리즈 색은 상태에 쓰지 않는다. 탄수화물(`chartCarbs`)과 warning은 같은 주황 계열이라 반드시 아이콘과 문구로 구분한다.
- 표시 형태:
  - 배지: `ShadBadge`, `caption`, 반경 full
  - 화면 안 알림: `ShadAlert`, 아이콘 + 제목 + 설명
  - 잠깐 뜨는 알림: `ShadToaster`, 화면 아래, 4초
- "기록 없음"은 상태가 아니다. `mutedForeground` 글자와 `--`로 중립 표기한다.

### 13-2. 화면 상태

| 상태 | 표현 |
|---|---|
| 로딩(첫 진입) | 카드 모양 스켈레톤(`muted` 면, 반경 16). 쓸고 지나가는 반짝임 대신 투명도 펄스(1.2s) |
| 로딩(다시 불러오기) | 이전 화면을 유지하고 당겨서 새로고침 인디케이터만 보인다. 스켈레톤으로 깜빡이지 않는다 |
| 빈 상태 | 가운데 정렬 아이콘 24(`mutedForeground`) + `heading` 제목 + `bodySmall` 설명 + 버튼 1개(Outline) |
| 오류 | 페이지에 바로 `ShadAlert`(error)를 두고, 그 아래 12 간격으로 전체 폭 Outline "다시 시도" 버튼을 둔다. Alert 자체가 테두리 상자라 카드로 감싸지 않는다(§9 카드 안 카드 금지) |
| AI 처리 중 | 스켈레톤 + "AI가 분석하고 있습니다" `bodySmall` |

---

## 14. 아이콘

- 새 UI는 `shadcn_ui`에 들어 있는 **Lucide** 아이콘을 쓴다. 크기는 16·20·24 세 단계다.
- 한 화면 안에서 Lucide와 Material 아이콘을 섞지 않는다. 화면 단위로 옮기고, 하단 탭은 한 번에 옮긴다.
- 아이콘 색은 기본 `foreground`, 보조 `mutedForeground`, 선택 `primary`다. 색 채운 아이콘 타일은 식사 종류 같은 분류 표시에만 `muted` 면으로 쓴다.

---

## 15. shadcn_ui 컴포넌트 매핑

| 현재 | 목표 | 비고 |
|---|---|---|
| `MaterialApp.router` + `AppTheme.darkTheme` | `ShadApp.custom` + `MaterialApp.router` 또는 `ShadApp.router` | Light·Dark·ThemeMode. Material 테마는 `materialThemeBuilder`로 토큰에서 만든다 |
| `NeoPrimaryButton` | `ShadButton` | 높이 48 |
| `NeoOutlineButton` | `ShadButton.outline` | |
| `TextButton`(섹션 액션) | `ShadButton.link` / `ShadButton.ghost` | |
| `_RoundIconButton`(뒤로가기) | `ShadIconButton.ghost` | 원 테두리 제거 |
| `NeoGlassCard` | `ShadCard` | 강조 변형 없음 |
| `NeoInfoChip`(정보·상태) | `ShadBadge` / `ShadBadge.secondary` / `ShadBadge.outline` | 상태 배지는 `backgroundColor`·`foregroundColor`로 상태 토큰 |
| `NeoProgressBar` | `ShadProgress` | `color`·`backgroundColor` |
| `NeoStateCard`(오류) | `ShadAlert.destructive` + 버튼 | |
| `TextField` + `InputDecoration` | `ShadInputFormField` + `ShadForm` | 라벨·오류 통일 |
| `DropdownButtonFormField` | `ShadSelectFormField` | |
| `showDatePicker` | `ShadDatePickerFormField` | 한국어는 `GlobalShadLocalizations`(ko 포함) |
| `Checkbox`(사진 분석 결과 선택) | `ShadCheckbox` | |
| `SnackBar` | `ShadToaster` + `ShadToast` | 상태 아이콘 포함 |
| 채팅 세그먼트 | `ShadTabs` | |
| 식사 카드 더보기(⋮) | `ShadSheet`(아래에서 올라오는 시트) | 모바일은 팝업 메뉴보다 시트 |
| 삭제 확인(도입 시) | `ShadDialog.alert` | |
| 구분선 | `ShadSeparator.horizontal` | |
| 온오프 설정(테마 등, 도입 시) | `ShadSwitch`, `ShadRadioGroup` | ThemeMode 선택 |
| `RefreshIndicator` | 유지(Material) | 네이티브 당겨서 새로고침. 색만 `primary` |
| `Shimmer` | Custom `Skeleton` | 펄스 방식 |

---

## 16. Custom Widget 목록

2026-10-04에 Dashboard에 필요한 템플릿을 `frontend/lib/shared/design_system/`에 구현했다(`design_system.dart`가 전부 export한다). 세부 값은 §24에 있다. 아래 표에서 구현된 위젯은 이름 옆에 ✓를 붙였다.

| 위젯 | 역할 | 구성 | 대체하는 현재 위젯 |
|---|---|---|---|
| `AppScaffold` ✓ | 탭·상세 화면 뼈대, safe area, 스크롤, 당겨서 새로고침 | Material `Scaffold` | `NeoPage`, 상세 화면 Scaffold 패턴 |
| `AppHeader` ✓ | Root / Detail 헤더 | `ShadIconButton` | `NeoTopBar` |
| `AppBottomNav` ✓ | 붙은 하단 5탭 | Custom | `MainShell._NavItem` |
| `BottomActionBar` | 하단 고정 Primary | `ShadButton` | `NeoBottomActionBar`(모양만 새 토큰으로) |
| `SectionHeader` | 섹션 제목 + Link 액션 | `ShadButton.link` | `NeoSectionHeader` |
| `MetricTile` | 라벨 + 숫자 + 단위 + 변화량 | `ShadCard` | `NeoMetricTile` |
| `ListRow` | 아이콘·제목·부제·값·chevron 행 | Custom | 통계 리스트, 식단 기준 관리 행 |
| `ProgressRing` ✓ | 하루 목표 진행 링 | `CustomPaint` | `NeoRing`, `CalorieRing` |
| `MacroBar` ✓ | 매크로 라벨·값·진행 바 | `ShadProgress` | `NutrientBar` |
| `TrendLineChart` ✓ | 체중·열량·영양소 추이(축·범례·툴팁 규칙 내장) | `fl_chart` | `NeoLineChart`, 월간 차트 |
| `WeekConsistency` ✓ | 요일별 운동·식단 달성 격자 + 범례 | Custom | `_ConsistencyBar` |
| `DateStepper` | 날짜·월 이동 | `ShadIconButton` | 플랜 날짜 헤더, 월간 헤더 |
| `FilterChipBar` | 가로 스크롤 선택 칩 | Custom | 근육군 필터 |
| `MealTimeline` | 식사 순서 타임라인 | Custom | 식단 타임라인 |
| `SetTable` | 세트·횟수·중량 표 | Custom(tabular 숫자) | 플랜 세트 목록 |
| `TagInput` | 알레르기·선호 식품 입력 | `ShadInput` + `ShadBadge` | 프로필 태그 편집 |
| `AiCoachCard` ✓ | AI 진입 카드(화면당 1개) | `ShadCard` + `ShadButton` | 홈·플랜·식단 AI 카드 |
| `AppSelectField` | 전체 폭 선택 칸(§10의 `minWidth` 처리 내장) | `ShadSelectFormField` | `DropdownButtonFormField` |
| `AppCard` ✓ / `AppCardAction` ✓ | 카드 한 가지 모양(선택적 헤더·trailing, `emphasis` 여백 20), 카드 헤더 Ghost 이동 액션 | `ShadCard`, `ShadButton.ghost` | `NeoGlassCard` |
| `NavRowCard` ✓ | 아이콘 타일 + 제목 + 부제 + chevron, 카드 전체가 눌림 | `AppCard` | 월간 리포트 보기 버튼, 식단 기준 관리 행 |
| `AppBadge` ✓ / `AppLegendDot` ✓ | 중립·외곽선·상태 배지(아이콘 16 + caption), 범례 점 | `ShadBadge` | `NeoInfoChip` |
| `SourceList` | 검증된 AI 출처 목록 | `ShadBadge` | `_SourcesView` |
| `EmptyState` / `Skeleton` ✓ | 빈 상태, 로딩 | Custom | `NeoStateCard`, `Shimmer` |
| `PhotoPicker` | 스캔 사진 선택 영역 | Custom | 스캔 화면 카드 |

---

## 17. 기준 화면: Dashboard 적용안

정보 구조와 순서는 그대로 두고 시각 체계만 바꾼다. 수치는 캡처 기준 예시다.

**구현된 목업(2026-10-04):**
- 코드: `frontend/lib/dev/mockups/`
- 실행: `flutter run -t lib/main_design_mockups.dart`
- 웹 주소: `#/dashboard?state=data|loading|empty|sparse|error&mode=system|light|dark`
- 렌더 이미지: `screenshots/mockups/2026-10-04/`(상태 5가지 × Light/Dark, 첫 화면과 전체 길이)
- 비교용: 주소에 `&theme=shadcn`을 붙이면 shadcn_ui 기본 테마(Slate)로 같은 화면을 그린다. 앱 전용 색(차트·상태)과 한글 대체 폰트만 더한다. 렌더 이미지는 `shadcn-*.png`다. 나란히 놓은 비교 이미지는 `compare-light.png`, `compare-dark.png`, `compare-all.png`(Light·Dark × shadcn 기본·앱 토큰 4열)다.

**실제 화면 적용(2026-10-04):** 홈 탭(`/dashboard`)을 이 설계로 옮겼다. 사용자가 지시한 첫 실제 화면이다.
- 코드: `frontend/lib/features/dashboard/presentation/`
  - `dashboard_screen.dart`: provider로 상태와 값을 정한다.
  - `dashboard_view.dart`: 상태별 화면을 그린다. 목업도 같은 `DashboardView`를 쓰므로 목업과 실제 화면이 갈라지지 않는다.
  - `dashboard_view_data.dart`: API 응답을 화면 값으로 바꾼다.
  - `widgets/`: 카드.
- 렌더 이미지: `screenshots/redesign/2026-10-04/dashboard-*.png`. 실제 셸(`MainShell`) 안에서 테스트 데이터로 그렸다.
- 이번 단계에서 정한 것:
  - **테마:** 앱 루트(`main.dart`)를 `ShadApp.custom`으로 감싸 `ShadTheme`을 앱 전체에 둔다. 옮기지 않은 화면은 MaterialApp의 옛 `AppTheme`을 그대로 쓴다. 옛 화면이 Dark 전용이라 지금은 **Dark로 고정**한다. System·Light와 Appearance 설정(§19-10)은 화면 전환이 더 진행된 뒤 연다.
  - **하단 탭:** 다섯 탭이 함께 쓰는 셸(`MainShell`)의 옛 떠 있는 탭을 그대로 둔다. `AppBottomNav`로 바꾸는 일은 다른 탭에도 영향이 있어 따로 한다.
  - **영양 카드:** 옛 화면에서 카드를 누르면 식단 탭으로 갔다. 이 이동을 지키려고 헤더에 `AppCardAction` "보기"를 두었다(목업에도 반영).
  - **체중 추이:** 지난 30일을 보인다. 이를 위해 `recentWeightHistoryProvider`가 3개월치를 받고 화면에서 30일로 자른다. 옛 화면은 이번 달 기록만 보였다.
  - **목표 초과:** 섭취가 목표를 넘으면 링 아래 배지 줄에 warning 배지("315kcal 초과")를 보인다(§12-4). 목표가 없으면 링 중앙은 `--`, 라벨은 "목표 없음"이다.
  - **체중 기록:** 홈의 다른 데이터와 따로 불러온다. 불러오는 동안 차트 자리에만 스켈레톤을 보인다.

아래 와이어프레임은 설계 당시 초안이고, 실제 배치는 렌더 이미지를 기준으로 본다.

```
┌──────────────────────────────────────┐
│ 좋은 하루예요                  display │  Root 헤더 (알림 아이콘 없음)
│ 9월 26일 금요일 · 목표 체지방 감량  │  부제: 날짜 + 현재 컨텍스트 (확정 §19-5)
│                                      │
│ ┌ 오늘의 진행 ─────────── heading ──┐ │  대표 카드: 안쪽 여백 20
│ │   ╭──────╮   섭취 열량            │ │
│ │   │ 57%  │   1,185 / 2,085 kcal   │ │  numMedium + 단위 muted
│ │   │열량목표│   운동                 │ │
│ │   ╰──────╯   2개 · 7세트          │ │
│ │  (링: primary, 두께 10)            │ │
│ │  [🔥 운동 1일 연속] [🔥 식단 14일]  │ │  ShadBadge.secondary (중립)
│ └───────────────────────────────────┘ │
│ ┌ 체중 ─────────────── [↓ 1.1kg] ──┐ │  배지는 중립. 목표 방향 판단은 없음
│ │ 72.4 kg                   numHero │ │
│ │ ── 선 차트 (chartKcal, 2px, 축) ── │ │  y 최소·최대, x 시작·끝 날짜
│ └───────────────────────────────────┘ │
│ ┌ 영양 ────────────────────────────┐ │
│ │ 1,185 / 2,085 kcal                │ │
│ │ ▓▓▓▓▓▓▓░░░░░ (primary)            │ │
│ │ ● 단백질 69g  ● 탄수화물 165g  ● 지방 26g │  점만 시리즈 색, 글자는 foreground
│ └───────────────────────────────────┘ │
│ ┌ 오늘 운동 기록 ──────────── 보기 > ┐ │  사진 배경 제거, Ghost 액션(foreground 글자)
│ │ 가슴 · 하체                        │ │
│ │ 2개 운동 · 7세트                   │ │
│ └───────────────────────────────────┘ │
│ ┌ 주간 일관성 ───── ● 운동 3일 ● 식단 5일┐│  범례 겸 요약
│ │ 월 화 수 목 금 토 일               │ │  요일별 점 2개 (chartExercise·chartKcal)
│ └───────────────────────────────────┘ │
│ ┌ AI 코치 ─────────────────────────┐ │  AiCoachCard: glow 없음
│ │ 목표와 기록을 바탕으로 답변합니다  │ │
│ │ [ AI 코치에게 질문          ]      │ │  이 화면의 유일한 Primary
│ └───────────────────────────────────┘ │
│ ┌ 📊 월간 리포트 보기            >  ┐ │  Nav row 카드 (전체 폭 Outline 버튼 대체)
│ └───────────────────────────────────┘ │
├──────────────────────────────────────┤
│  홈   통계   플랜   식단   스캔        │  붙은 하단 탭
└──────────────────────────────────────┘
```

이 화면에서 accent(시안)가 쓰이는 곳은 네 곳뿐이다.
1. 진행 링
2. 열량 진행 바
3. AI 코치 Primary 버튼
4. 하단 탭 선택 표시

---

## 18. 테마 구현 구조 (확정 후 작업)

- **토큰의 단일 원본:**
  - `lib/core/theme/` 아래에 Light·Dark 토큰 정의를 한 곳에 둔다.
  - 여기서 `ShadThemeData`(색, `ShadTextTheme`, 반경, 버튼 크기 테마)와 Material `ThemeData`(`materialThemeBuilder`)를 만든다.
- **토큰을 읽는 방법:** 위젯은 `ShadTheme.of(context)`와 확장 getter로 토큰을 읽는다. 정적 `AppColors`·`AppTypography` 직접 참조는 전환이 끝나면 없앤다.
- **ThemeMode:**
  - System·Light·Dark 세 가지이고 기본값은 System이다(확정 §19-10).
  - Riverpod provider가 들고, `shared_preferences`에 저장하며, 루트 앱이 `themeMode`로 받는다.
  - 선택 UI는 설정 또는 프로필 화면의 **Appearance** 영역에 둔다(확정 §19-10). 설정 화면이 없으므로 프로필 화면에 영역을 두는 것이 기본안이다.
- **폰트:**
  - Noto Sans KR(앱 asset `NotoSansKR`)과 Geist(`packages/shadcn_ui/Geist`)는 둘 다 가변 폰트다.
  - `fontWeight`와 함께 `fontVariations: [FontVariation.weight(...)]`를 지정해 굵기가 실제로 적용되게 한다. 현행 캡처에서 한글 제목이 가늘게 보이는 원인 후보다.
- **테스트:** 위젯 테스트 공통 래퍼가 `ShadTheme`을 주입하고, Light·Dark 두 번 렌더링한다.
- **전환 순서(제안):**
  1. 테마 기반(토큰·루트·ThemeMode·테스트 래퍼)
  2. 로그인·회원가입
  3. Dashboard
  4. 나머지 탭
  5. 입력·AI 화면
  6. 옛 `neo_widgets.dart`·정적 토큰 제거

---

## 19. 결정 사항 (2026-09-26 확정)

| # | 확정 내용 | 비고 |
|---|---|---|
| 1 | 폰트는 Noto Sans KR + Geist 두 가지로 줄인다 | Sora·Hanken Grotesk asset 제거는 전환이 끝난 뒤에 한다 |
| 2 | 하단 탭은 화면 하단에 고정하고, iOS/Android safe area를 반드시 고려한다 | §11-1 |
| 3 | 데이터 카드의 단순 장식용 사진은 제거한다. 음식 사진, 운동 콘텐츠처럼 정보 자체가 이미지인 경우는 유지할 수 있다 | §7 |
| 4 | 탭 헤더의 불필요한 브랜드명과 기능 없는 알림 아이콘을 제거한다 | §11-2 |
| 5 | 탭 화면의 불필요한 설명문을 제거한다. 홈은 날짜와 현재 컨텍스트를 보여 준다 | §17 |
| 6 | Light `primary`는 우선 `#0E7490`을 쓴다 | "우선": Theme Preview로 보고 조정할 수 있다 |
| 7 | Light `background`는 우선 `#F4F4F5`를 쓴다 | "우선": 위와 같다 |
| 8 | AI 진입점은 화면당 명확한 1개를 원칙으로 한다 | 기능과 플로우는 그대로 둔다 |
| 9 | 주간 일관성은 요일별 상태를 직관적으로 보는 점(dot) 기반 표현으로 바꾼다 | §12-1 |
| 10 | 테마 선택은 설정 또는 프로필의 Appearance 영역에 둔다. System / Light / Dark, 기본값 System | §18 |

### 아직 확정되지 않은 것

아래는 초안 값이다. Theme Preview로 실제 렌더링을 보고 확정한다.

- 결정 6·7을 제외한 색 토큰 세부 값(§3)
- 타이포그래피 스케일(§4-2)
- 간격(§5)과 반경(§6)
- 버튼·카드·입력·내비게이션·차트·상태 규칙의 세부(§8~§13)
- 차트 팔레트 5색(§12-2). 계산 검증은 통과했고, 2026-09-26 Theme Preview에서 두 모드 모두 구분되는 것을 눈으로 확인했다
- Custom Widget 목록(§16)과 Dashboard 적용안(§17)

**확정(2026-10-04):** shadcn_ui 기본 테마(Slate) 대신 이 문서의 앱 토큰을 쓴다. 비교 이미지는 `screenshots/mockups/2026-10-04/compare-*.png`에 있다.

### Dashboard 목업 검토로 정한 것 (2026-10-04 확정)

목업 구현 중 문서 규칙과 부딪히거나 문서에 없던 점이다. 제안대로 확정했고 템플릿·목업·이 문서(§4-2, §8, §9, §21-2, §24)에 반영했다.

사용자가 2026-10-04에 검토 이미지(`screenshots/mockups/2026-10-04/review-1~3-*.png`, 확인할 곳을 주황색으로 표시)로 확인했고 수정 요청은 없었다.

| # | 항목 | 결정 |
|---|---|---|
| A | 카드 헤더 액션("보기", "기록하기")이 primary 링크라 강조색이 다섯 번째로 쓰인다(§17은 4곳) | Ghost(foreground 글자 + chevron)로 바꿔 강조색 4곳을 지킨다 |
| B | 카드 헤더 액션을 48 높이로 하면 헤더가 지나치게 높아진다 | 보이는 높이는 40, 누르는 영역은 카드 여백까지 넓혀 48 |
| C | "오늘의 진행" 카드가 글자 크기 5단계를 쓴다(§4-2는 카드당 3단계) | 숫자와 단위는 한 묶음으로 세고, 대표 카드는 4단계까지 허용 |
| D | Light에서 주간 일관성의 미래 요일 점이 너무 흐리다(대비 1.27) | 미래 요일은 점을 그리지 않고 요일 라벨만 muted로 |
| E | 배지 여백 8/4를 호출할 때마다 덮어쓴다 | `app_shad_theme.dart`의 배지 테마로 옮긴다 |
| F | 프로필이 없는 빈 상태에서도 헤더 부제에 목표("체지방 감량 중")가 나온다 | 프로필이 없으면 부제는 날짜만(§21-2 데이터 진실성). 프로필을 아직 모르는 로딩·오류 상태도 같다 |

### Theme Preview에서 발견한 것 (2026-09-26 발견, 2026-10-03 해결)

- **Light `muted`가 `background`와 같았다(`#F4F4F5`).** 그래서 페이지 위 muted 면이 보이지 않았다. → Light `muted`를 `#E4E4E7`로 바꿨다. 보조 글자 대비는 4.55다.
- **Dark 삭제 버튼이 연분홍으로 보였다.** → 버튼 면 `destructive`는 두 모드 모두 `#DC2626`에 흰 글자(4.83)로 하고, 오류 글자·아이콘·테두리는 새 `error` 토큰(Dark `#F87171`, Light `#DC2626`)으로 나눴다. `#DC2626`을 Dark 카드 위 글자로 쓰면 3.67이라 미달이다.
- **`ShadSelectFormField`가 내용 폭으로 줄어들었다.** → 부모 폭을 `minWidth`로 넘겨 입력 칸과 좌우 끝을 맞췄다. 테스트로 고정했다.
- **아이콘 버튼의 누르는 영역이 40이었다.** → 아이콘 버튼 크기 테마를 48×48로 했다. 테스트로 고정했다.
- **Light `secondary`·`accent`도 배경과 같았다(`#F4F4F5`).** 그래서 페이지 위 Secondary 버튼의 면과, 헤더 Ghost 버튼 같은 요소의 눌림 효과가 보이지 않았다. → 둘 다 `#E4E4E7`로 바꿨다(2026-10-03). §3-2의 은은한 면 규칙을 따른다.
- 한글 700 굵기는 새 타입 설정(Noto Sans KR 기본 폰트, `FontVariation.weight` 지정)에서 제대로 굵게 보인다.

## 20. Theme Preview (내부 전용)

- **실행:** `cd frontend && flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3001 -t lib/main_theme_preview.dart`. 기기에서 볼 때는 `flutter run -t lib/main_theme_preview.dart`다. 앱 내비게이션에는 연결하지 않았다.
- **코드:**
  - 토큰: `lib/core/design_system/`
  - 화면: `lib/dev/theme_preview/`
  - 테스트: `test/theme_preview_test.dart`
- **렌더 캡처:** 최신은 `screenshots/theme-preview/2026-10-03/light-01~12.png`, `dark-01~12.png`(폭 390, 수정 4건 반영). 수정 전은 `2026-09-26/`.

---

## 21. 문구와 데이터 표시

옛 문서(`FLUTTER_UI_DESIGN.md` §6·§7)의 규칙을 그대로 이어받는다. 새 디자인에서도 바뀌지 않는다.

### 21-1. 문구
- 사용자 대면 문구는 한국어 합니다체다(예: "프로필 설정이 필요합니다", "잠시 후 다시 시도해 주세요").
- 영문은 브랜드명, 단위(kg, kcal, g), AI·RAG·VO2 Max 같은 표준 약어에만 쓴다.
- 기능 설명 문구를 화면에 늘어놓지 않는다(확정 §19-5). 빈 상태, 오류, 첫 사용처럼 화면이 필요로 할 때만 쓴다.
- 짧게 쓴다. 한 줄에 들어가지 않는 설명은 끝의 한두 글자만 다음 줄로 넘어가지 않게 문장을 줄인다. Android 실기기에서 이런 사례가 있었다.
- 버튼 라벨은 동사로 끝낸다("기록하기", "다시 시도", "AI 코치에게 질문").

### 21-2. 데이터 진실성
- 체중과 목표 영양은 실제 profile·API 값만 보인다. 레퍼런스나 목업의 수치를 앱 데이터처럼 쓰지 않는다.
- 추이 차트는 기록이 2개 이상일 때만 그린다(§12-3).
- 체지방, 근육량, 심박, 수면, VO2 Max, 체성분 값이 없으면 `--`와 `기록 없음`(mutedForeground)으로 보인다. 상태색을 쓰지 않는다(§13-1).
- 실시간 세션 API가 없으므로 타이머, 강도, 심박, 완료율을 꾸며 보이지 않는다.
- 연결 기기 정보가 없으면 `기기 미연결`로 보인다.
- 알레르기와 식단 선호는 임의로 배지를 만들지 않고 프로필 화면으로 연결한다.
- AI 추천·채팅의 출처는 backend가 검증한 `sources`만 보인다. 출처가 없으면 없다고 보인다.
- 변화량 배지(예: 체중 ↓ 1.1kg)는 사용자의 목표 방향을 판단하지 않는 한 중립 배지로 보인다. 좋다·나쁘다를 상태색으로 단정하지 않는다.
- 헤더 부제의 목표(예: "체지방 감량 중")는 profile 값을 받았을 때만 보인다. 프로필이 없거나 아직 불러오지 못했으면(로딩·오류) 날짜만 보인다.

### 21-3. 사진
- 정보 자체가 이미지인 경우만 쓴다(확정 §19-3): 음식 사진 미리보기, 운동 동작 콘텐츠.
- Light와 Dark에서 같은 원본을 쓰고, 어둡게 덮는 그라데이션 오버레이를 쓰지 않는다.
- 반경은 사진 단독이면 12, 카드 안 썸네일이면 8이다. 흰 배경 사진이 Light 카드와 섞이지 않게 1px `border`를 두른다.

## 22. 접근성

- **대비:** 본문 4.5:1, 큰 글자와 UI 경계 3:1(§3). 토큰 대비는 테스트로 고정한다(`frontend/test/theme_preview_test.dart`).
- **터치 영역:** 최소 48×48(§5, §8).
- **글자 크기 확대:** 시스템 글자 크기 1.3배에서 넘치거나 잘리지 않는다. 화면별 위젯 테스트로 확인한다.
  - 줄바꿈이 필요한 곳은 줄바꿈을 허용한다.
  - 한 줄을 지켜야 하는 라벨(하단 탭, 배지)은 말줄임을 쓴다.
  - 숫자와 단위는 같은 줄에 두되 넘치면 단위를 다음 줄로 보낸다.
- **색만으로 의미를 전하지 않는다:** 상태는 아이콘 + 문구(§13), 차트는 범례·직접 라벨(§12), 주간 일관성 점은 접근성 라벨(예: "수요일 운동 기록 있음, 식단 기록 있음")을 단다.
- **스크린리더:** 아이콘만 있는 버튼에는 `Semantics` 라벨을 단다. 하단 탭 항목은 "홈 탭, 선택됨"처럼 선택 상태를 함께 읽힌다.
- **움직임 줄이기:** `MediaQuery.disableAnimations`이면 스켈레톤 펄스와 전환 애니메이션을 멈춘다(§23).

## 23. 모션

값은 Dashboard 목업 구현에서 정했고 `frontend/lib/core/design_system/app_motion.dart`에 있다.

| 토큰 | 값 | 쓰는 곳 |
|---|---|---|
| `AppMotion.selection` | 150ms | 하단 탭 선택 표시, 세그먼트 선택 이동 |
| `AppMotion.standard` | `Curves.easeInOut` | 위 전환의 곡선 |
| `AppMotion.skeletonPulse` | 1200ms(밝아짐 600 + 어두워짐 600) | 스켈레톤 투명도 1.0 ↔ 0.5 |

- 눌림 피드백은 애니메이션 없이 즉시 `accent` 면으로 바꾼다.
- 차트는 그려질 때 애니메이션하지 않는다(데이터가 바뀌어도 즉시 다시 그린다).

- 의미 있는 상태 변화에만 움직임을 쓴다: 눌림 피드백, 선택 표시 이동, 로딩. 장식 애니메이션은 쓰지 않는다.
- 화면 전환은 플랫폼 기본(iOS 밀어내기, Android 기본)을 따른다.
- `MediaQuery.disableAnimations`를 존중한다.

## 24. 템플릿 위젯 세부 값 (2026-10-04, Dashboard 목업에서 정함)

구현은 `frontend/lib/shared/design_system/`, 테스트는 `frontend/test/design_system_widgets_test.dart`·`dashboard_mockup_test.dart`다.

| 위젯 | 값 |
|---|---|
| `AppHeader.root` | 위 여백 16, 제목과 부제 사이 4. 첫 카드와 사이 24 |
| `AppHeader.detail` | 위 여백 8, 뒤로가기 아이콘 버튼 48(페이지 여백 20에 맞추려고 아이콘을 옮기지 않는다), 스크린리더 라벨 "뒤로" |
| `AppBottomNav` | 내용 높이 64 = 선택 알약 32 + 간격 4 + 라벨 16(+여백). 라벨 글자 배율은 최대 1.3배로 고정. 스크린리더 라벨 "홈 탭, 5개 중 1번째" + 선택 상태 |
| `AppCard` | 1px 테두리는 안쪽 여백 바깥에 있다. 그래서 내용은 바깥 끝에서 17(대표 카드 21)부터 시작한다. 헤더와 본문 사이 16. trailing이 `AppCardAction`이면 넘치는 4만큼 위 여백과 헤더 아래 간격을 줄여, 보이는 버튼은 여백 16 안쪽에서 시작하고 본문과 16 떨어진다 |
| `AppCardAction` | Ghost compact: 보이는 높이 40, 누르는 영역 48(위아래 4는 바깥 GestureDetector가 받는다). 좌우 8, `buttonCompact` `foreground` 라벨, chevron 16 `mutedForeground` |
| `AppBadge` | 안쪽 여백 8/4 → 높이 24(shadcn 기본 10/2는 4 격자에서 벗어남). 여백은 테마(`AppShadTheme.badgePadding`, 배지 변형 4개 모두)에 있고 호출부에서 덮어쓰지 않는다. 중립 배지도 아이콘 16을 쓸 수 있다. 라벨은 `caption` 500 |
| `AppLegendDot` | 점 8, 점과 글자 사이 4, 항목 사이 12, 줄바꿈 시 줄 사이 8 |
| `ProgressRing` | 기본 크기 112. 폭 360에서도 카드 내용(280)에 링 112 + 간격 16 + 지표 152가 들어간다. 중앙 글자는 링 두께 + 8만큼 떨어지고, 넘치면 `FittedBox`로 줄인다. 100%를 넘으면 링을 가득 채우고 둥근 끝 없이 그리며, 중앙에 실제 값(예: 115%)을 보인다 |
| `MacroBar` | 라벨 줄과 바 사이 8, 매크로 사이 12. 열량 텍스트와 열량 바 사이 8 |
| `TrendLineChart` | 높이 160(축 포함). y축 영역 40, x축 영역 24는 글자 배율을 따르고, 라벨까지 간격 8. y 눈금 3개는 1·2·2.5·5×10ⁿ 단위로 정한다(예: 72/73/74). x 라벨은 차트 가장자리 안쪽에 둔다. 툴팁은 popover 면 + 1px 테두리, 반경 12, 여백 12/8, "10/4 · 72.4 kg". 탭한 점에 1px muted 세로선. 기록 부족 문구 위아래 12 |
| `WeekConsistency` | 점 12, 행 사이 8, 요일 라벨까지 8, 범례 아래 16. 미기록은 1.5px `input` 테두리 원. 미래 요일은 점을 그리지 않고 12 칸만 비워 두며 요일 라벨은 muted다(muted 점은 Light 카드와 대비 1.27이라 보이지 않았다). 오늘 요일 라벨은 foreground 600. 스크린리더 라벨 "수요일, 운동 기록 있음, 식단 기록 있음", "토요일 오늘, …", 미래는 "아직 지나지 않음" |
| `SkeletonBlock` | 반경 16, 투명도 1.0 ↔ 0.5(§23). Dashboard 자리 높이 232/296/216/104/128 |
| `EmptyState` | 위아래 32(카드 여백 포함 48), compact는 8. 아이콘→제목 12, 제목→설명 4, 설명→버튼 16 |
| `ErrorState` | 카드 없이 Alert(아이콘 20) + 전체 폭 Outline "다시 시도"(rotate 아이콘), 사이 12 |
| `AiCoachCard` | sparkles 아이콘 타일, 아이콘과 제목 사이 12, 제목과 설명 사이 4 |
| `NavRowCard` | 글자와 chevron 사이 8, 눌림은 애니메이션 없이 accent 면 |
| 숫자 표기 | `formatNumber`가 로케일 데이터 없이 1,185처럼 천 단위 구분 기호를 붙인다. 숫자와 단위는 같은 기준선에 4 간격 |

### 24-1. Dashboard 화면 규칙(목업에서 정함)

- **오늘의 진행:**
  - "2개 · 7세트"는 `numMedium`이다.
  - 운동이 없으면 muted `body`로 "기록 없음"을 보인다.
  - 연속 기록 배지는 연속 일수가 0보다 클 때만 보인다.
- **헤더 부제:** data·sparse는 "10월 4일 토요일 · 체지방 감량 중", 로딩·빈 상태·오류는 날짜만(§21-2).
- **체중 변화량 배지:**
  - 비교할 기록이 없으면 숨긴다.
  - 화살표 글자 대신 trendingDown/Up 아이콘을 쓴다.
  - 스크린리더 라벨은 "지난 30일 대비 1.1kg 감소"다.

## 부록. 검증 방법

- **대비:** `dataviz` 스킬의 `scripts/validate_palette.js`의 `contrast()`로 계산했다. 카드 배경은 Light `#FFFFFF`, Dark `#18181B`이고, 페이지 배경은 Light `#F4F4F5`, Dark `#09090B`이다.
- **차트 팔레트:** 같은 스크립트의 `validate()`를 `pairs: "all"` 기준으로 두 모드에서 돌렸다. Tailwind v3 ramp의 cyan·violet·indigo·amber·orange·rose·pink·lime·green·emerald 400~700 단계를 조합해 탐색했고, 모든 검사 통과 + 카드 배경 대비 3:1 이상인 조합 중에서 골랐다.
- **캡처:** `screenshots/2026-09-25/` 26장. 폭 390(2x)이고 다크 모드뿐이다.
