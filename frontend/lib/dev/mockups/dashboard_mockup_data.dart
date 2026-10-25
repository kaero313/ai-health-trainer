// Dashboard 목업 전용 가짜 데이터(내부 전용). 캡처(screenshots/2026-09-25/) 기준 값이다.
// 실제 화면과 같은 DashboardViewData로 만든다. 날짜는 고정 문자열로 둔다.
import '../../features/dashboard/presentation/dashboard_view_data.dart';
import '../../shared/design_system/week_consistency.dart';

/// 목업이 보이는 화면 상태.
enum DashboardMockupState { data, loading, empty, sparse, error }

/// 헤더 부제의 날짜. 목표는 프로필에서 오므로 프로필을 모르는 상태
/// (로딩·빈 상태·오류)에서는 부제에 날짜만 보인다(§21-2).
const String dashboardMockupDate = '10월 4일 토요일';

/// 프로필을 받은 상태(data·sparse)의 부제.
const String dashboardMockupSubtitle = '$dashboardMockupDate · 체지방 감량 중';

const List<(String, String)> _weekdays = <(String, String)>[
  ('월', '월요일'),
  ('화', '화요일'),
  ('수', '수요일'),
  ('목', '목요일'),
  ('금', '금요일'),
  ('토', '토요일'),
  ('일', '일요일'),
];

/// 오늘은 토요일(5)이고 일요일(6)은 미래다.
const int _todayIndex = 5;

List<WeekDayStatus> _week({
  required Set<int> exerciseDays,
  required Set<int> dietDays,
}) {
  return <WeekDayStatus>[
    for (int i = 0; i < _weekdays.length; i++)
      WeekDayStatus(
        label: _weekdays[i].$1,
        fullName: _weekdays[i].$2,
        isToday: i == _todayIndex,
        exercise: i > _todayIndex
            ? DayMark.future
            : (exerciseDays.contains(i) ? DayMark.done : DayMark.missed),
        diet: i > _todayIndex
            ? DayMark.future
            : (dietDays.contains(i) ? DayMark.done : DayMark.missed),
      ),
  ];
}

/// data 상태: 캡처 기준 값.
final DashboardViewData dashboardMockupFull = DashboardViewData(
  intakeKcal: 1185,
  targetKcal: 2085,
  exerciseCount: 2,
  exerciseSets: 7,
  exerciseStreakDays: 1,
  dietStreakDays: 14,
  weightKg: 72.4,
  weightChangeKg: -1.1,
  // 지난 30일 12개 기록. 73.5에서 약간 오르내리며 72.4로 내려간다.
  weightHistory: const <double>[
    73.5, 73.6, 73.3, 73.2, 73.4, 73.0, 72.9, 73.1, 72.8, 72.6, 72.7, 72.4, //
  ],
  weightDates: const <String>[
    '9/5', '9/7', '9/10', '9/12', '9/15', '9/17', //
    '9/20', '9/22', '9/25', '9/27', '10/1', '10/4',
  ],
  proteinG: 69,
  proteinTargetG: 130,
  carbsG: 165,
  carbsTargetG: 261,
  fatG: 26,
  fatTargetG: 58,
  todayExerciseTitle: '가슴 · 하체',
  todayExerciseDetail: '2개 운동 · 7세트',
  // 운동 월·수·금, 식단 월~금
  week: _week(exerciseDays: <int>{0, 2, 4}, dietDays: <int>{0, 1, 2, 3, 4}),
);

/// sparse 상태: 기록 부족. 체중 1개, 오늘 운동 없음, 주간 점 대부분 빈 원.
final DashboardViewData dashboardMockupSparse = DashboardViewData(
  intakeKcal: 320,
  targetKcal: 2085,
  exerciseCount: 0,
  exerciseSets: 0,
  exerciseStreakDays: 0,
  dietStreakDays: 1,
  weightKg: 72.4,
  weightChangeKg: null,
  weightHistory: const <double>[72.4],
  weightDates: const <String>['10/4'],
  proteinG: 18,
  proteinTargetG: 130,
  carbsG: 40,
  carbsTargetG: 261,
  fatG: 9,
  fatTargetG: 58,
  todayExerciseTitle: null,
  todayExerciseDetail: null,
  week: _week(exerciseDays: <int>{}, dietDays: <int>{_todayIndex}),
);
