// 홈 화면 표시 데이터. API 응답(Map)을 화면이 쓰는 값으로 바꾼다
// (docs/DESIGN_SYSTEM.md §17, §21-2). 없는 값은 꾸미지 않고 null로 둔다.
import 'dart:math' as math;

import 'package:flutter/foundation.dart';

import '../../../shared/design_system/week_consistency.dart';

/// 체중 추이 기록의 불러오기 상태. 홈 전체 로딩과 따로 진행된다.
enum WeightTrendState { loading, error, ready }

@immutable
class DashboardViewData {
  const DashboardViewData({
    required this.intakeKcal,
    required this.targetKcal,
    required this.exerciseCount,
    required this.exerciseSets,
    required this.exerciseStreakDays,
    required this.dietStreakDays,
    required this.weightKg,
    required this.weightChangeKg,
    required this.weightHistory,
    required this.weightDates,
    this.weightTrendState = WeightTrendState.ready,
    required this.proteinG,
    required this.proteinTargetG,
    required this.carbsG,
    required this.carbsTargetG,
    required this.fatG,
    required this.fatTargetG,
    required this.todayExerciseTitle,
    required this.todayExerciseDetail,
    required this.week,
  });

  final int intakeKcal;

  /// 하루 목표 열량. 목표가 없으면 null.
  final int? targetKcal;
  final int exerciseCount;
  final int exerciseSets;
  final int exerciseStreakDays;
  final int dietStreakDays;

  /// 현재 체중(profile). 없으면 null.
  final double? weightKg;

  /// 지난 30일 첫 기록 대비 마지막 기록의 변화량. 기록이 2개 미만이면 null.
  final double? weightChangeKg;
  final List<double> weightHistory;

  /// [weightHistory]와 같은 길이의 날짜 라벨("9/5").
  final List<String> weightDates;
  final WeightTrendState weightTrendState;
  final int proteinG;
  final int? proteinTargetG;
  final int carbsG;
  final int? carbsTargetG;
  final int fatG;
  final int? fatTargetG;

  /// 오늘 운동이 없으면 null.
  final String? todayExerciseTitle;
  final String? todayExerciseDetail;
  final List<WeekDayStatus> week;

  bool get hasTarget => targetKcal != null && targetKcal! > 0;

  /// 목표 대비 비율. 1을 넘을 수 있다. 목표가 없으면 0.
  double get intakeRatio => hasTarget ? intakeKcal / targetKcal! : 0;

  /// 목표를 넘긴 열량. 넘지 않았거나 목표가 없으면 0.
  int get overKcal => hasTarget ? math.max(0, intakeKcal - targetKcal!) : 0;

  /// API 응답에서 만든다. [now]는 오늘·미래 요일과 30일 범위를 정한다.
  factory DashboardViewData.fromApi({
    required Map<String, dynamic> profile,
    required Map<String, dynamic> today,
    required Map<String, dynamic> weekly,
    required List<Map<String, dynamic>>? weightHistory,
    required WeightTrendState weightTrendState,
    required DateTime now,
  }) {
    final Map<String, dynamic> nutrition = _map(today['nutrition']);
    final Map<String, dynamic> consumed = _map(nutrition['consumed']);
    final Map<String, dynamic>? target = nutrition['target'] is Map
        ? _map(nutrition['target'])
        : null;
    final Map<String, dynamic> exercise = _map(today['exercise']);
    final Map<String, dynamic> streak = _map(today['streak']);

    final int exerciseCount = _toInt(exercise['exercises_count']);
    final int exerciseSets = _toInt(exercise['total_sets']);
    final List<String> muscles = _stringList(
      exercise['muscle_groups_trained'],
    ).map(muscleGroupLabel).toList();

    final List<({DateTime date, double value})> points = recentWeightPoints(
      weightHistory ?? const <Map<String, dynamic>>[],
      now,
    );
    final double? change = points.length < 2
        ? null
        : _round1(points.last.value - points.first.value);

    return DashboardViewData(
      intakeKcal: _toInt(consumed['calories']),
      targetKcal: target == null ? null : _toInt(target['calories']),
      exerciseCount: exerciseCount,
      exerciseSets: exerciseSets,
      exerciseStreakDays: _toInt(streak['exercise_days']),
      dietStreakDays: _toInt(streak['diet_logging_days']),
      weightKg: _toNullableDouble(profile['weight_kg']),
      weightChangeKg: change,
      weightHistory: <double>[for (final p in points) p.value],
      weightDates: <String>[
        for (final p in points) '${p.date.month}/${p.date.day}',
      ],
      weightTrendState: weightTrendState,
      proteinG: _toInt(consumed['protein_g']),
      proteinTargetG: target == null ? null : _toInt(target['protein_g']),
      carbsG: _toInt(consumed['carbs_g']),
      carbsTargetG: target == null ? null : _toInt(target['carbs_g']),
      fatG: _toInt(consumed['fat_g']),
      fatTargetG: target == null ? null : _toInt(target['fat_g']),
      todayExerciseTitle: exerciseCount > 0
          ? (muscles.isEmpty ? '운동 완료' : muscles.join(' · '))
          : null,
      todayExerciseDetail: exerciseCount > 0
          ? '$exerciseCount개 운동 · $exerciseSets세트'
          : null,
      week: weekStatuses(_mapList(weekly['daily_breakdown']), now),
    );
  }
}

const List<String> _weekdays = <String>['월', '화', '수', '목', '금', '토', '일'];

/// 헤더 부제의 날짜("10월 4일 토요일"). 로케일 데이터 없이 만든다.
String dashboardDateLabel(DateTime date) =>
    '${date.month}월 ${date.day}일 ${_weekdays[date.weekday - 1]}요일';

/// profile goal의 현재 진행 표현. 모르는 값이면 null.
String? dashboardGoalLabel(Object? goal) => switch (goal) {
  'diet' => '체지방 감량 중',
  'bulk' => '근육 증가 중',
  'maintain' => '체중 유지 중',
  _ => null,
};

/// 헤더 부제. 목표는 profile을 받았을 때만 붙인다(§21-2).
String dashboardSubtitle(DateTime now, {Map<String, dynamic>? profile}) {
  final String date = dashboardDateLabel(now);
  final String? goal = profile == null
      ? null
      : dashboardGoalLabel(profile['goal']);
  return goal == null ? date : '$date · $goal';
}

/// 지난 30일(오늘 포함 31일 범위) 체중 기록을 날짜순으로 돌려준다.
List<({DateTime date, double value})> recentWeightPoints(
  List<Map<String, dynamic>> history,
  DateTime now,
) {
  final DateTime today = DateTime(now.year, now.month, now.day);
  final DateTime from = today.subtract(const Duration(days: 30));
  final List<({DateTime date, double value})> points =
      <({DateTime date, double value})>[];
  for (final Map<String, dynamic> item in history) {
    final DateTime? date = DateTime.tryParse(
      item['log_date']?.toString() ?? '',
    );
    final double? value = _toNullableDouble(item['weight_kg']);
    if (date == null || value == null) continue;
    if (date.isBefore(from) || date.isAfter(today)) continue;
    points.add((date: date, value: value));
  }
  points.sort((a, b) => a.date.compareTo(b.date));
  return points;
}

/// weekly daily_breakdown(월~일)을 요일 상태로 바꾼다. 오늘 뒤는 future다.
List<WeekDayStatus> weekStatuses(
  List<Map<String, dynamic>> days,
  DateTime now,
) {
  final DateTime today = DateTime(now.year, now.month, now.day);
  final List<WeekDayStatus> result = <WeekDayStatus>[];
  for (int i = 0; i < days.length; i++) {
    final Map<String, dynamic> day = days[i];
    final DateTime? date = DateTime.tryParse(day['date']?.toString() ?? '');
    final String label = date == null
        ? _weekdays[i.clamp(0, 6)]
        : _weekdays[date.weekday - 1];
    final bool future = date != null && date.isAfter(today);
    DayMark mark(bool done) =>
        future ? DayMark.future : (done ? DayMark.done : DayMark.missed);
    result.add(
      WeekDayStatus(
        label: label,
        fullName: '$label요일',
        isToday: date != null && date == today,
        exercise: mark(day['exercised'] == true),
        diet: mark(_toDouble(day['calories']) > 0),
      ),
    );
  }
  return result;
}

String muscleGroupLabel(String value) => switch (value) {
  'chest' => '가슴',
  'back' => '등',
  'legs' => '하체',
  'shoulders' => '어깨',
  'arms' => '팔',
  'core' => '코어',
  'cardio' => '유산소',
  'full_body' => '전신',
  _ => value,
};

Map<String, dynamic> _map(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map<String, dynamic>(
      (dynamic k, dynamic v) => MapEntry<String, dynamic>(k.toString(), v),
    );
  }
  return <String, dynamic>{};
}

List<Map<String, dynamic>> _mapList(Object? value) {
  if (value is! List) return <Map<String, dynamic>>[];
  return value.whereType<Map>().map(_map).toList();
}

List<String> _stringList(Object? value) {
  if (value is! List) return <String>[];
  return value.map((Object? item) => item.toString()).toList();
}

double _toDouble(Object? value) => _toNullableDouble(value) ?? 0;

double? _toNullableDouble(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

int _toInt(Object? value) => _toDouble(value).round();

double _round1(double value) => (value * 10).roundToDouble() / 10;
