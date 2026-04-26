# AI Health Trainer - Flutter UI/UX 화면 설계서

> **이 문서의 목적:** Codex가 Flutter 화면을 구현할 때 참조하는 UI/UX 설계 명세서.
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)
> **디자인 참조:** Hevy, Fitbod, MacroFactor, Nike Training Club의 최신 UI/UX 트렌드 반영
> **현재 기준:** 최신 프로젝트 상태와 다음 의사결정은 `docs/OWNER_GUIDE.md`를 우선한다.

---

## 1. 디자인 시스템

### 1-1. 컬러 팔레트 (다크 모드 기본)

```dart
/// lib/core/theme/app_colors.dart

class AppColors {
  // ── 배경 ──
  static const background       = Color(0xFF0D1B2A);  // 딥 네이비 (메인 배경)
  static const surface          = Color(0xFF1B2838);  // 카드/서피스 배경
  static const surfaceLight     = Color(0xFF243447);  // 입력 필드/활성 카드 배경

  // ── 브랜드 액센트 ──
  static const primary          = Color(0xFF00E676);  // 바이브런트 그린 (주 액센트)
  static const primaryDark      = Color(0xFF00C853);  // 눌림 상태
  static const primarySoft      = Color(0x3300E676);  // 20% 투명도 (배지, 배경)

  // ── 보조 색상 ──
  static const calories         = Color(0xFFFF6B6B);  // 칼로리 (레드 코랄)
  static const protein          = Color(0xFF4ECDC4);  // 단백질 (틸 민트)
  static const carbs            = Color(0xFFFFD93D);  // 탄수화물 (골든 옐로)
  static const fat              = Color(0xFFFF8A65);  // 지방 (소프트 오렌지)

  // ── 텍스트 ──
  static const textPrimary      = Color(0xFFF0F0F0);  // 제목/본문
  static const textSecondary    = Color(0xFF8899AA);  // 보조 텍스트
  static const textDisabled     = Color(0xFF556677);  // 비활성

  // ── 상태 ──
  static const success          = Color(0xFF00E676);
  static const warning          = Color(0xFFFFD93D);
  static const error            = Color(0xFFFF5252);
  static const info             = Color(0xFF448AFF);

  // ── 기타 ──
  static const divider          = Color(0xFF2A3A4A);  // 구분선
  static const shimmer          = Color(0xFF2A3A4A);  // 로딩 시머
}
```

### 1-2. 타이포그래피

```dart
/// lib/core/theme/app_typography.dart
/// Google Fonts 'Inter' 사용 (google_fonts 패키지)

class AppTypography {
  // ── 제목 ──
  static const h1 = TextStyle(fontSize: 28, fontWeight: FontWeight.w700, letterSpacing: -0.5);
  static const h2 = TextStyle(fontSize: 22, fontWeight: FontWeight.w700, letterSpacing: -0.3);
  static const h3 = TextStyle(fontSize: 18, fontWeight: FontWeight.w600);

  // ── 본문 ──
  static const body1  = TextStyle(fontSize: 16, fontWeight: FontWeight.w400, height: 1.5);
  static const body2  = TextStyle(fontSize: 14, fontWeight: FontWeight.w400, height: 1.4);

  // ── 라벨/캡션 ──
  static const label  = TextStyle(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 0.5);
  static const caption = TextStyle(fontSize: 11, fontWeight: FontWeight.w400);

  // ── 숫자 (큰 수치 표시용) ──
  static const number = TextStyle(fontSize: 32, fontWeight: FontWeight.w800, letterSpacing: -1.0);
  static const numberSmall = TextStyle(fontSize: 20, fontWeight: FontWeight.w700);
}
```

### 1-3. 간격 & 사이즈

```dart
/// lib/core/theme/app_spacing.dart

class AppSpacing {
  static const xs  = 4.0;
  static const sm  = 8.0;
  static const md  = 16.0;
  static const lg  = 24.0;
  static const xl  = 32.0;
  static const xxl = 48.0;
}

class AppRadius {
  static const sm  = 8.0;   // 작은 요소 (칩, 배지)
  static const md  = 12.0;  // 카드
  static const lg  = 16.0;  // 시트, 다이얼로그
  static const xl  = 24.0;  // 큰 카드
  static const full = 999.0; // 원형
}
```

### 1-4. 공통 컴포넌트 스타일

```dart
/// 카드 스타일 (모든 카드에 적용)
BoxDecoration cardDecoration = BoxDecoration(
  color: AppColors.surface,
  borderRadius: BorderRadius.circular(AppRadius.md),
  border: Border.all(color: AppColors.divider, width: 0.5),
);

/// 글래스모피즘 카드 (강조 카드에 사용)
BoxDecoration glassCardDecoration = BoxDecoration(
  color: AppColors.surface.withOpacity(0.7),
  borderRadius: BorderRadius.circular(AppRadius.lg),
  border: Border.all(color: AppColors.primary.withOpacity(0.2)),
  boxShadow: [
    BoxShadow(
      color: AppColors.primary.withOpacity(0.05),
      blurRadius: 20,
      offset: Offset(0, 4),
    ),
  ],
);

/// 그라데이션 버튼
BoxDecoration primaryButtonDecoration = BoxDecoration(
  gradient: LinearGradient(
    colors: [AppColors.primary, AppColors.primaryDark],
  ),
  borderRadius: BorderRadius.circular(AppRadius.md),
);
```

---

## 2. 네비게이션 구조

### 2-1. 전체 화면 플로우

```
[스플래시] → [온보딩 (최초 1회)] → [로그인/회원가입]
                                         │
                                    ┌─────┴─────┐
                                    │ 메인 셸    │
                                    │ (BottomNav)│
                                    ├────────────┤
                                    │ ⓵ 대시보드  │ ← 홈
                                    │ ⓶ 식단     │
                                    │ ⓷ ➕ (FAB) │ ← 빠른 기록 추가
                                    │ ⓸ 운동     │
                                    │ ⓹ 프로필    │
                                    └────────────┘
                                         │
                              각 탭에서 상세 화면으로 Push
```

### 2-2. 하단 네비게이션 바

```
┌─────────────────────────────────────────────┐
│                                             │
│   🏠        🍽️        ➕        💪        👤   │
│  대시보드    식단     (FAB)     운동      프로필  │
│                                             │
└─────────────────────────────────────────────┘

디자인 스펙:
- 높이: 72dp (안전 영역 포함)
- 배경: AppColors.surface + 상단 blur(10) 효과
- 활성 탭: AppColors.primary 아이콘 + 텍스트
- 비활성 탭: AppColors.textSecondary 아이콘
- 중앙 FAB: 56dp 원형, AppColors.primary 그라데이션, 약간 위로 돌출
- FAB 누르면: 바텀시트 (운동 추가 / 식단 추가 / 사진 분석 선택)
```

### 2-3. 라우팅 (go_router)

```dart
/// lib/core/router/app_router.dart

final routes = [
  // 인증
  GoRoute(path: '/splash', builder: ...),
  GoRoute(path: '/onboarding', builder: ...),
  GoRoute(path: '/login', builder: ...),
  GoRoute(path: '/register', builder: ...),

  // 메인 셸 (하단 네비게이션)
  ShellRoute(
    builder: (context, state, child) => MainShell(child: child),
    routes: [
      GoRoute(path: '/dashboard', builder: ...),
      GoRoute(path: '/diet', builder: ...),
      GoRoute(path: '/exercise', builder: ...),
      GoRoute(path: '/profile', builder: ...),
    ],
  ),

  // 상세 화면 (Push)
  GoRoute(path: '/diet/analyze', builder: ...),        // 음식 사진 분석
  GoRoute(path: '/diet/add', builder: ...),             // 식단 기록 추가
  GoRoute(path: '/diet/recommend', builder: ...),       // AI 식단 추천
  GoRoute(path: '/exercise/add', builder: ...),         // 운동 기록 추가
  GoRoute(path: '/exercise/recommend', builder: ...),   // AI 운동 추천
  GoRoute(path: '/exercise/history/:group', builder: ...),// 근육군별 히스토리
  GoRoute(path: '/profile/edit', builder: ...),         // 프로필 수정
];
```

---

## 3. 화면별 상세 설계

### 3-1. 스플래시 화면 (`/splash`)

```
┌─────────────────────────────┐
│                             │
│                             │
│                             │
│         🏋️ (아이콘)          │
│                             │
│     AI Health Trainer       │
│     ─── 로딩 바 ───         │
│                             │
│                             │
│                             │
└─────────────────────────────┘

스펙:
- 배경: AppColors.background
- 로고: 중앙 큰 아이콘 (Lottie 애니메이션 권장)
- 앱 이름: h1 + AppColors.primary
- 로딩 바: 얇은 선형 프로그레스, AppColors.primary
- 1.5초 후 자동 전환 (토큰 유무 확인 → 로그인 or 대시보드)
```

---

### 3-2. 온보딩 화면 (`/onboarding`) — 최초 1회

```
┌─────────────────────────────┐
│                             │
│   (3장 PageView로 스와이프)   │
│                             │
│      [일러스트/아이콘]        │
│                             │
│   "AI가 당신의 운동과 식단을   │
│    분석하고 코칭해드립니다"    │
│                             │
│      ● ○ ○ (인디케이터)      │
│                             │
│   [ 시작하기 ] (마지막 장)    │
│   [ 건너뛰기 ] (우상단)       │
└─────────────────────────────┘

3장 구성:
1. "사진 한 장으로 영양 분석" — 카메라 → AI 분석 아이콘
2. "AI 기반 맞춤 운동 추천" — 근육 → 추천 아이콘
3. "목표에 맞춘 코칭" — 그래프 상승 아이콘

스펙:
- PageView + 자동 스크롤 (3초 간격)
- 인디케이터: 활성=primary, 비활성=divider
- "시작하기" 버튼: primary 그라데이션, 풀 와이드
- "건너뛰기": textSecondary, 우상단
```

---

### 3-3. 로그인/회원가입 (`/login`, `/register`)

```
┌─────────────────────────────┐
│                             │
│      🏋️ AI Health Trainer    │
│                             │
│  ┌─── 이메일 ─────────────┐ │
│  │ user@email.com         │ │
│  └────────────────────────┘ │
│  ┌─── 비밀번호 ───────────┐ │
│  │ ••••••••    👁         │ │
│  └────────────────────────┘ │
│                             │
│  ┌────────────────────────┐ │
│  │      로그인            │ │← primary 그라데이션 버튼
│  └────────────────────────┘ │
│                             │
│  계정이 없으신가요? 회원가입   │← 텍스트 링크
│                             │
└─────────────────────────────┘

스펙:
- 입력 필드: surfaceLight 배경, 라운드 md, 포커스 시 primary 테두리
- 비밀번호 토글: 눈 아이콘
- 로그인 버튼: primaryButtonDecoration, h=52dp
- 키보드: resizeToAvoidBottomInset
- 회원가입: 이메일, 비밀번호, 비밀번호 확인 (3필드)
- 에러: 필드 하단 빨간 텍스트, 토스트 메시지
- 입력 검증: 실시간 (이메일 형식, 비밀번호 8자+)
```

---

### 3-4. 대시보드 (`/dashboard`) ⭐ 핵심 화면

```
┌─────────────────────────────┐
│ 민수님, 안녕하세요       🔔 │← AppBar (인사말 + 알림)
│─────────────────────────────│
│ ┌─ 오늘의 영양 ───────────┐ │
│ │                         │ │
│ │     ╭────────╮          │ │
│ │     │ 1,850  │          │ │← 중앙 원형 프로그레스
│ │     │ /2,800 │          │ │   (칼로리: calories 색상)
│ │     │  kcal  │          │ │
│ │     ╰────────╯          │ │
│ │                         │ │
│ │ 🟢단백질  🟡탄수화물  🟠지방  │ │← 3개 작은 선형 프로그레스
│ │ 120/126g  200/350g  55/78g │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 오늘의 운동 ───────────┐ │
│ │ 💪 가슴 + 팔             │ │← 근육군 아이콘 + 요약
│ │ 4개 운동 · 15세트 완료    │ │
│ │ ✅ 완료                  │ │← 완료 배지 (primary)
│ └─────────────────────────┘ │
│                             │
│ ┌─ AI 코칭 ──────────────┐ │
│ │ 🤖 "단백질 목표 거의 달성! │ │← AI 코칭 요약 카드
│ │  저녁에는 탄수화물 위주    │ │   (glassCardDecoration)
│ │  식사를 추천합니다."      │ │
│ │        [자세히 보기 →]    │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 이번 주 요약 ──────────┐ │
│ │ 월 화 수 목 금 토 일     │ │← 주간 캘린더 히트맵
│ │ 🟢 🟢 🟢 🟡 🟢 ⚫ ⚫     │ │   (운동 + 식단 기록 여부)
│ │                         │ │
│ │ 🔥 5일 연속 기록 중!      │ │← 스트릭 배지 (게이미피케이션)
│ └─────────────────────────┘ │
└─────────────────────────────┘

디자인 핵심:
- 원형 프로그레스: CustomPainter로 구현, 내부에 큰 숫자
- 각 영양소 프로그레스 바: 라운드, 높이 6dp, 해당 색상
- AI 코칭 카드: glassCardDecoration + primary 테두리 글로우
- 주간 히트맵: 7개 원 (운동+식단 완료=primary, 부분=warning, 미기록=divider)
- 스트릭: 불꽃 이모지 + primary 텍스트
- 스크롤: SingleChildScrollView, 부드러운 스크롤
- Pull-to-refresh 지원
```

---

### 3-5. 식단 탭 (`/diet`)

```
┌─────────────────────────────┐
│ 식단 기록         📅 2/17   │← AppBar (날짜 선택 가능)
│─────────────────────────────│
│                             │
│ ┌─ 아침 ──────────────────┐ │
│ │ 🥣 오트밀            320kcal│← 음식 카드
│ │    단 15g  탄 45g  지 8g  │ │
│ ├─────────────────────────┤ │
│ │ 🥛 우유              150kcal│
│ │    단 8g   탄 12g  지 8g  │ │
│ │           + 추가하기      │ │← 섹션 내 추가 버튼
│ └─────────────────────────┘ │
│                             │
│ ┌─ 점심 ──────────────────┐ │
│ │ 🍗 닭가슴살 샐러드   350kcal│
│ │    단 40g  탄 15g  지 12g │ │
│ │           + 추가하기      │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 저녁 ──────────────────┐ │
│ │      아직 기록이 없습니다   │ │← 빈 상태
│ │      [+ 기록하기]         │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 간식 ──────────────────┐ │
│ │      아직 기록이 없습니다   │ │
│ └─────────────────────────┘ │
│                             │
│ ◉ 일일 합계 ───────────────  │
│ 칼로리: 820 / 2,800 kcal    │← 하단 고정 요약 바
│ ████░░░░░░░░░ 29%           │
│                             │
│ ┌──────┐  ┌───────────────┐ │
│ │📷분석│  │ 🤖 AI 추천    │ │← 하단 액션 버튼 2개
│ └──────┘  └───────────────┘ │
└─────────────────────────────┘

인터랙션:
- 날짜 선택: 상단 날짜 탭 → DatePicker 또는 좌우 스와이프
- 음식 카드 탭: 상세 보기 (수정/삭제)
- 음식 카드 좌로 스와이프: 삭제 (Dismissible)
- "+ 추가하기": 식단 추가 화면으로 Push
- "📷 분석": 카메라 → 음식 사진 AI 분석 화면
- "🤖 AI 추천": AI 식단 추천 화면
- 영양소 수치: 각 매크로 색상으로 표시 (protein=틸, carbs=골드, fat=오렌지)
```

---

### 3-6. 음식 사진 AI 분석 (`/diet/analyze`)

```
┌─────────────────────────────┐
│ ← 음식 사진 분석             │← AppBar
│─────────────────────────────│
│                             │
│ ┌─────────────────────────┐ │
│ │                         │ │
│ │    [ 촬영한 음식 사진 ]   │ │← 이미지 프리뷰 (h=250dp)
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│   🔄 분석 중...              │← 분석 중: Shimmer 로딩
│   ████████░░ 80%            │   또는 Lottie 애니메이션
│                             │
│ ── 분석 완료 후 ──           │
│                             │
│ ┌─ 인식된 음식 ───────────┐ │
│ │ ☑ 김치찌개    200kcal    │ │← 체크박스 (선택/해제 가능)
│ │   단12g 탄10g 지13g      │ │
│ │   신뢰도: ★★★★☆ (85%)   │ │← 신뢰도 표시
│ ├─────────────────────────┤ │
│ │ ☑ 흰쌀밥      300kcal    │ │
│ │   단5g  탄68g 지0.5g     │ │
│ │   신뢰도: ★★★★★ (92%)   │ │
│ └─────────────────────────┘ │
│                             │
│ 합계: 500kcal               │
│ 단17g · 탄78g · 지13.5g     │
│                             │
│ ┌────────────────────────┐  │
│ │   식단에 추가하기        │  │← primary 버튼
│ └────────────────────────┘  │
│                             │
│ [다시 촬영] [직접 수정]       │← 보조 텍스트 버튼
└─────────────────────────────┘

인터랙션:
- 카메라 접근: image_picker 패키지 (카메라/갤러리)
- 분석 중: Shimmer 효과로 카드 로딩 표현
- 체크박스: 인식 결과 중 원하는 것만 선택
- "직접 수정": 각 항목의 영양소를 수동 편집 가능
- "식단에 추가하기": 선택한 항목을 POST /diet/logs 로 저장
```

---

### 3-7. 운동 탭 (`/exercise`)

```
┌─────────────────────────────┐
│ 운동 기록         📅 2/17   │← AppBar
│─────────────────────────────│
│                             │
│ ┌─ 근육군 필터 (가로 스크롤) ─┐
│ │ [전체] [가슴] [등] [어깨]  │ │← Chip 필터
│ │ [하체] [팔] [코어] [유산소]│ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 벤치프레스 ────────────┐ │
│ │ 🏋️ 가슴                  │ │← 근육군 라벨 (color chip)
│ │                         │ │
│ │ 세트 1:  60kg × 10회  ✅ │ │← 세트별 기록 목록
│ │ 세트 2:  60kg × 10회  ✅ │ │
│ │ 세트 3:  60kg ×  8회  ✅ │ │
│ │ 세트 4:  62.5kg × 6회 ✅ │ │
│ │                         │ │
│ │ 📈 지난번 대비 +2.5kg    │ │← 진행 표시 (primary 색상)
│ └─────────────────────────┘ │
│                             │
│ ┌─ 인클라인 덤벨프레스 ───┐ │
│ │ 🏋️ 가슴                  │ │
│ │ 세트 1:  14kg × 12회  ✅ │ │
│ │ 세트 2:  14kg × 12회  ✅ │ │
│ │ 세트 3:  14kg × 10회  ✅ │ │
│ └─────────────────────────┘ │
│                             │
│ ┌──────┐  ┌───────────────┐ │
│ │+ 추가│  │ 🤖 AI 추천    │ │← 하단 액션 버튼
│ └──────┘  └───────────────┘ │
└─────────────────────────────┘

인터랙션:
- 근육군 Chip: 탭 시 해당 근육군만 필터
- 운동 카드 탭: 상세 보기 (메모, 수정, 삭제)
- 운동 카드 롱프레스: 드래그로 순서 변경
- 📈 진행 표시: 이전 같은 운동과 자동 비교
- "+ 추가": 운동 추가 화면으로 Push
- "🤖 AI 추천": AI 운동 추천 화면
```

---

### 3-8. 운동 추가 화면 (`/exercise/add`)

```
┌─────────────────────────────┐
│ ← 운동 추가                  │
│─────────────────────────────│
│                             │
│ ┌─── 운동명 ──────────────┐ │
│ │ 벤치프레스              🔍│ │← 자동완성 검색 필드
│ └─────────────────────────┘ │
│                             │
│ 근육군:  [가슴 ▾]            │← 드롭다운 (자동 선택)
│ 날짜:    [2026-02-17 ▾]     │
│                             │
│ ── 세트 기록 ──              │
│ ┌─────────────────────────┐ │
│ │ # │  무게(kg)  │  횟수   │ │← 데이터 테이블 스타일
│ │ 1 │  [60.0]    │  [10]   │ │
│ │ 2 │  [60.0]    │  [10]   │ │← 이전 세트 값 자동 복사
│ │ 3 │  [60.0]    │  [10]   │ │
│ │              [+ 세트 추가]│ │
│ └─────────────────────────┘ │
│                             │
│ ┌─── 메모 (선택) ─────────┐ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ 📊 지난 기록: 57.5kg × 10회 │ │← 참고용 이전 기록
│                             │
│ ┌────────────────────────┐  │
│ │       저장하기           │  │← primary 버튼
│ └────────────────────────┘  │
└─────────────────────────────┘

인터랙션:
- 운동명 입력: 자동완성 (최근 운동 + 인기 운동 목록)
- 운동명 선택 → 근육군 자동 설정
- 세트 추가: 이전 세트의 무게/횟수 자동 복사 (편의성)
- 무게 입력: 숫자 키보드, +/- 2.5kg 스텝퍼 버튼
- 횟수 입력: 숫자 키보드, +/- 1 스텝퍼 버튼
- 저장 시 진동 피드백 (HapticFeedback.mediumImpact)
```

---

### 3-9. AI 추천 화면 (`/diet/recommend`, `/exercise/recommend`)

```
┌─────────────────────────────┐
│ ← AI 운동 추천               │
│─────────────────────────────│
│                             │
│ ┌─ AI 코치 메시지 ─────────┐│
│ │ 🤖                       ││← 로봇 아바타 아이콘
│ │                          ││
│ │ "지난 가슴 운동에서 벤치   ││← AI 응답 (채팅 버블 스타일)
│ │  프레스 60kg × 10회를      ││   glassCardDecoration
│ │  성공하셨습니다. 오늘은     ││
│ │  62.5kg으로 도전해보세요." ││
│ └──────────────────────────┘│
│                             │
│ ── 추천 운동 ──              │
│                             │
│ ┌─ 벤치프레스 ────────────┐ │
│ │ 4세트 × 8회 · 62.5kg    │ │← 추천 카드 (primary 테두리)
│ │ 💡 이전 대비 2.5kg 증량   │ │
│ │        [이 운동 기록하기]  │ │← 탭하면 운동 추가 화면으로
│ └─────────────────────────┘ │   (무게/횟수 자동 채움)
│                             │
│ ┌─ 인클라인 덤벨프레스 ───┐ │
│ │ 3세트 × 12회 · 16kg     │ │
│ │ 💡 상부 가슴 자극 보조    │ │
│ │        [이 운동 기록하기]  │ │
│ └─────────────────────────┘ │
│                             │
│ 📚 참고: 운동 과학 - 점진적  │ │← RAG 출처 표시
│    과부하 원칙 연구          │ │
│                             │
│ ┌────────────────────────┐  │
│ │   전체 추천 기록하기      │  │← 모든 추천을 한 번에 기록
│ └────────────────────────┘  │
└─────────────────────────────┘

디자인 핵심:
- AI 메시지: 채팅 버블 스타일, 좌측 로봇 아바타
- 추천 카드: primary 좌측 보더 라인 (4dp)
- "이 운동 기록하기": 탭 → /exercise/add로 이동 (데이터 prefill)
- RAG 출처: 작은 텍스트, info 색상
- 로딩: 타이핑 애니메이션 (점 3개 깜빡임)
```

---

### 3-10. 프로필 탭 (`/profile`)

```
┌─────────────────────────────┐
│ 프로필                    ⚙️ │← 설정 아이콘
│─────────────────────────────│
│                             │
│   ┌──────┐                  │
│   │  👤  │  민수님           │← 프로필 아바타 (원형)
│   └──────┘  user@email.com  │
│                             │
│ ┌─ 신체 정보 ─────────────┐ │
│ │                         │ │
│ │  175cm    70kg    28세   │ │← 숫자 강조(numberSmall)
│ │   키      몸무게   나이   │ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 목표 ──────────────────┐ │
│ │                         │ │
│ │  🎯 벌크업 (+300kcal)    │ │← 목표 배지 (primary 배경)
│ │  활동 수준: 보통 (주 3~5) │ │
│ │                         │ │
│ │  목표 칼로리: 2,800 kcal │ │
│ │  단백질: 126g            │ │
│ │  탄수화물: 350g          │ │
│ │  지방: 78g               │ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─ 기타 설정 ─────────────┐ │
│ │ 알레르기: 우유, 땅콩      │ │
│ │ 선호 식품: 닭가슴살, 고구마│ │
│ └─────────────────────────┘ │
│                             │
│ ┌────────────────────────┐  │
│ │      수정하기            │  │← outlined 버튼
│ └────────────────────────┘  │
│                             │
│ [로그아웃]                   │← 텍스트 버튼 (error 색상)
└─────────────────────────────┘
```

---

## 4. 애니메이션 가이드

### 적용할 마이크로 애니메이션

| 위치 | 애니메이션 | 구현 |
|------|----------|------|
| 화면 전환 | 슬라이드 + 페이드 (300ms) | `go_router` 커스텀 트랜지션 |
| 카드 등장 | 아래→위 슬라이드 + 페이드 (200ms, staggered) | `AnimationController` + `SlideTransition` |
| 프로그레스 링 | 0에서 값까지 카운트업 (800ms, easeOutCubic) | `CustomPainter` + `AnimatedBuilder` |
| 숫자 변경 | 카운트업 애니메이션 | 커스텀 `AnimatedCount` 위젯 |
| 버튼 탭 | 스케일 0.95 → 1.0 (100ms) | `GestureDetector` + `AnimatedScale` |
| 삭제 스와이프 | 좌로 슬라이드 + 빨간 배경 | `Dismissible` |
| AI 로딩 | 점 3개 타이핑 애니메이션 | `AnimatedOpacity` 순차 반복 |
| Pull-to-refresh | 상단에서 원형 로더 | `RefreshIndicator` |
| FAB 확장 | 누르면 3개 옵션 펼침 | `FloatingActionButton.extended` + `AnimatedContainer` |
| 탭 전환 | 부드러운 크로스페이드 | `AnimatedSwitcher` |

### 애니메이션 원칙
1. **300ms 이하** — 모든 UI 애니메이션은 빠르게
2. **easeOutCubic** — 기본 커브 (자연스러운 감속)
3. **Staggered** — 목록 아이템은 50ms 간격으로 순차 등장
4. **의미 있는 모션만** — 불필요한 애니메이션은 제거

---

## 5. Flutter 패키지 의존성

```yaml
# frontend/pubspec.yaml dependencies

dependencies:
  flutter:
    sdk: flutter

  # 상태 관리
  flutter_riverpod: ^2.6.0
  riverpod_annotation: ^2.6.0

  # 라우팅
  go_router: ^14.0.0

  # HTTP
  dio: ^5.7.0

  # UI
  google_fonts: ^6.2.0           # Inter 폰트
  flutter_svg: ^2.0.0             # SVG 아이콘
  shimmer: ^3.0.0                 # 로딩 시머 효과
  fl_chart: ^0.69.0               # 차트 (프로그레스 링, 주간 차트)
  cached_network_image: ^3.4.0    # 이미지 캐싱

  # 기능
  image_picker: ^1.1.0            # 카메라/갤러리
  intl: ^0.19.0                   # 날짜 포맷

  # 저장
  flutter_secure_storage: ^9.2.0  # JWT 토큰 보관
  shared_preferences: ^2.3.0      # 설정 저장

  # 기타
  lottie: ^3.1.0                  # Lottie 애니메이션
  haptic_feedback: ^0.5.0         # 진동 피드백

dev_dependencies:
  flutter_test:
    sdk: flutter
  riverpod_generator: ^2.6.0
  build_runner: ^2.4.0
  flutter_lints: ^4.0.0
```

---

## 6. 반응형 레이아웃

```dart
/// 기본 모바일 (360~412dp 기준)
/// 태블릿 대응은 MVP 이후

class AppLayout {
  static const maxContentWidth = 500.0;   // 콘텐츠 최대 너비
  static const horizontalPadding = 16.0;  // 좌우 패딩

  // 모든 화면에 적용
  static Widget page({required Widget child}) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxContentWidth),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
          child: child,
        ),
      ),
    );
  }
}
```

---

## 7. Codex 구현 순서

```
Phase 1: 기반 UI
 1. 디자인 시스템 (colors, typography, spacing) 구현
 2. 메인 셸 + 하단 네비게이션 바
 3. 스플래시 화면
 4. 로그인/회원가입 화면 + API 연동
 5. 프로필 설정/수정 화면 + API 연동

Phase 2: 핵심 화면
 6. 대시보드 화면 (프로그레스 링, 카드)
 7. 식단 탭 (날짜별 기록, 영양소 표시)
 8. 식단 추가 화면
 9. 운동 탭 (근육군 필터, 세트 기록)
10. 운동 추가 화면

Phase 3: AI 화면
11. 음식 사진 AI 분석 화면
12. AI 식단 추천 화면
13. AI 운동 추천 화면
14. 온보딩 화면

Phase 4: 폴리시
15. 애니메이션 적용
16. 에러/빈 상태 UI
17. 로딩 상태 (Shimmer)
18. 최종 테스트 + 버그 수정
```
