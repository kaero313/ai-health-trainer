// 주간 일관성: 요일 7열 × 위아래 점 2개 (docs/DESIGN_SYSTEM.md §12-1, §19-9).
// 위 점은 운동(chartExercise), 아래 점은 식단(chartKcal). 색만으로 구분하지 않도록
// 범례와 요일별 접근성 라벨을 함께 둔다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_badge.dart';

/// 하루 한 항목의 기록 상태.
enum DayMark {
  /// 기록 있음: 채운 점.
  done,

  /// 기록 없음: 1.5px input 색 테두리 원.
  missed,

  /// 오늘 이후: 점을 그리지 않고 칸만 비워 둔다. 요일 라벨은 muted다.
  future,
}

@immutable
class WeekDayStatus {
  const WeekDayStatus({
    required this.label,
    required this.fullName,
    required this.exercise,
    required this.diet,
    this.isToday = false,
  });

  /// 열 아래 짧은 요일("월").
  final String label;

  /// 접근성 라벨용 요일 이름("월요일").
  final String fullName;
  final DayMark exercise;
  final DayMark diet;
  final bool isToday;
}

class WeekConsistency extends StatelessWidget {
  const WeekConsistency({
    super.key,
    required this.days,
    this.exerciseLabel = '운동',
    this.dietLabel = '식단',
  });

  static const double dotSize = 12;
  static const double missedStroke = 1.5;

  final List<WeekDayStatus> days;
  final String exerciseLabel;
  final String dietLabel;

  int get exerciseDays =>
      days.where((WeekDayStatus d) => d.exercise == DayMark.done).length;
  int get dietDays =>
      days.where((WeekDayStatus d) => d.diet == DayMark.done).length;

  static String describeMark(DayMark mark) => switch (mark) {
    DayMark.done => '기록 있음',
    DayMark.missed => '기록 없음',
    DayMark.future => '아직 지나지 않음',
  };

  /// 예: "수요일 운동 기록 있음, 식단 기록 있음", 오늘이면 "토요일 오늘, ...".
  String semanticsFor(WeekDayStatus d) {
    final String today = d.isToday ? ' 오늘' : '';
    return '${d.fullName}$today, $exerciseLabel ${describeMark(d.exercise)}, '
        '$dietLabel ${describeMark(d.diet)}';
  }

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Wrap(
          spacing: AppSpace.s12,
          runSpacing: AppSpace.s8,
          children: <Widget>[
            AppLegendDot(
              color: cs.chartExercise,
              label: '$exerciseLabel $exerciseDays일',
            ),
            AppLegendDot(color: cs.chartKcal, label: '$dietLabel $dietDays일'),
          ],
        ),
        const SizedBox(height: AppSpace.s16),
        Row(
          children: <Widget>[
            for (final WeekDayStatus d in days)
              Expanded(
                child: Semantics(
                  label: semanticsFor(d),
                  excludeSemantics: true,
                  child: _DayColumn(day: d, cs: cs),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _DayColumn extends StatelessWidget {
  const _DayColumn({required this.day, required this.cs});

  final WeekDayStatus day;
  final ShadColorScheme cs;

  @override
  Widget build(BuildContext context) {
    final TextStyle label = day.isToday
        ? AppTextStyles.withWeight(
            AppTextStyles.caption,
            FontWeight.w600,
          ).copyWith(color: cs.foreground)
        : AppTextStyles.caption.copyWith(color: cs.mutedForeground);
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        _Dot(mark: day.exercise, color: cs.chartExercise, cs: cs),
        const SizedBox(height: AppSpace.s8),
        _Dot(mark: day.diet, color: cs.chartKcal, cs: cs),
        const SizedBox(height: AppSpace.s8),
        Text(day.label, style: label, maxLines: 1),
      ],
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.mark, required this.color, required this.cs});

  final DayMark mark;
  final Color color;
  final ShadColorScheme cs;

  @override
  Widget build(BuildContext context) {
    // 세 상태 모두 같은 12×12 칸을 차지해 행 높이가 흔들리지 않게 한다.
    final Widget? dot = switch (mark) {
      DayMark.done => Container(
        width: WeekConsistency.dotSize,
        height: WeekConsistency.dotSize,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
      DayMark.missed => Container(
        width: WeekConsistency.dotSize,
        height: WeekConsistency.dotSize,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(
            color: cs.input,
            width: WeekConsistency.missedStroke,
          ),
        ),
      ),
      // Light에서 muted 점은 카드와 대비가 1.27이라 보이지 않는다. 그리지 않는다.
      DayMark.future => null,
    };
    return SizedBox.square(
      dimension: WeekConsistency.dotSize,
      child: dot == null ? null : Center(child: dot),
    );
  }
}
