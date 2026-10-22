// 홈 Summary 카드: 오늘의 진행, 체중, 영양 (docs/DESIGN_SYSTEM.md §17 1~4).
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../../core/design_system/app_shad_theme.dart';
import '../../../../core/design_system/app_text_styles.dart';
import '../../../../core/design_system/app_tokens.dart';
import '../../../../shared/design_system/design_system.dart';
import '../dashboard_view_data.dart';

/// "1,185" numMedium + " / 2,085 kcal" body muted. 목표가 없으면 " kcal"만 붙인다.
Widget kcalOfTarget(BuildContext context, int value, int? target) {
  final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
  return Text.rich(
    TextSpan(
      children: <InlineSpan>[
        TextSpan(
          text: formatNumber(value),
          style: AppTextStyles.numMedium.copyWith(color: cs.foreground),
        ),
        TextSpan(
          text: target == null || target <= 0
              ? ' kcal'
              : ' / ${formatNumber(target)} kcal',
          style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
        ),
      ],
    ),
  );
}

/// 화면 대표 카드(안쪽 여백 20): 링 + 섭취 열량·운동 지표 + 초과·연속 기록 배지.
class TodayProgressCard extends StatelessWidget {
  const TodayProgressCard({super.key, required this.data});

  /// 폭 360에서 카드 안쪽 280 중 링 112 + 간격 16 + 지표 152가 들어간다.
  static const double ringSize = 112;

  final DashboardViewData data;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final TextStyle label = AppTextStyles.caption.copyWith(
      color: cs.mutedForeground,
    );
    final bool hasExercise = data.exerciseCount > 0;
    final List<Widget> badges = <Widget>[
      // 목표 초과는 링 대신 warning 배지로 알린다(§12-4).
      if (data.overKcal > 0)
        AppBadge.status(
          tone: AppBadgeTone.warning,
          label: '${formatNumber(data.overKcal)}kcal 초과',
        ),
      if (data.exerciseStreakDays > 0)
        AppBadge.neutral(
          icon: LucideIcons.flame,
          label: '운동 ${data.exerciseStreakDays}일 연속',
        ),
      if (data.dietStreakDays > 0)
        AppBadge.neutral(
          icon: LucideIcons.flame,
          label: '식단 ${data.dietStreakDays}일 연속',
        ),
    ];
    return AppCard(
      title: '오늘의 진행',
      emphasis: true,
      children: <Widget>[
        Row(
          children: <Widget>[
            ProgressRing(
              value: data.intakeRatio,
              valueText: data.hasTarget ? null : '--',
              label: data.hasTarget ? '열량 목표' : '목표 없음',
              size: ringSize,
            ),
            const SizedBox(width: AppSpace.s16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('섭취 열량', style: label),
                  const SizedBox(height: AppSpace.s4),
                  kcalOfTarget(context, data.intakeKcal, data.targetKcal),
                  const SizedBox(height: AppSpace.s12),
                  Text('운동', style: label),
                  const SizedBox(height: AppSpace.s4),
                  Text(
                    hasExercise
                        ? '${data.exerciseCount}개 · ${data.exerciseSets}세트'
                        : '기록 없음',
                    style: hasExercise
                        ? AppTextStyles.numMedium.copyWith(color: cs.foreground)
                        : AppTextStyles.body.copyWith(
                            color: cs.mutedForeground,
                          ),
                  ),
                ],
              ),
            ),
          ],
        ),
        if (badges.isNotEmpty)
          Wrap(spacing: AppSpace.s8, runSpacing: AppSpace.s8, children: badges),
      ],
    );
  }
}

/// 체중: numHero + 단위, 지난 30일 변화 중립 배지, 단일 시리즈 추이.
class WeightCard extends StatelessWidget {
  const WeightCard({super.key, required this.data});

  final DashboardViewData data;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final double? change = data.weightChangeKg;
    final String changeText = change == null
        ? ''
        : formatNumber(change.abs(), decimals: 1);
    final double? weight = data.weightKg;
    return AppCard(
      title: '체중',
      // 목표 방향을 판단하지 않으므로 상태색이 아닌 중립 배지다.
      trailing: change == null || change == 0
          ? null
          : AppBadge.neutral(
              icon: change < 0
                  ? LucideIcons.trendingDown
                  : LucideIcons.trendingUp,
              label: '${changeText}kg',
              semanticLabel:
                  '지난 30일 대비 ${changeText}kg ${change < 0 ? '감소' : '증가'}',
            ),
      children: <Widget>[
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: <Widget>[
                Text(
                  weight == null ? '--' : formatNumber(weight, decimals: 1),
                  style: AppTextStyles.numHero.copyWith(color: cs.foreground),
                ),
                const SizedBox(width: AppSpace.s4),
                Text(
                  weight == null ? '기록 없음' : 'kg',
                  style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.s4),
            Text(
              '지난 30일',
              style: AppTextStyles.caption.copyWith(color: cs.mutedForeground),
            ),
          ],
        ),
        switch (data.weightTrendState) {
          WeightTrendState.loading => const SkeletonBlock(
            height: TrendLineChart.defaultHeight,
          ),
          WeightTrendState.error => Text(
            '체중 추이를 불러오지 못했습니다',
            style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
          ),
          WeightTrendState.ready => TrendLineChart(
            series: <TrendSeries>[
              TrendSeries(
                label: '체중',
                color: cs.chartKcal,
                values: data.weightHistory,
              ),
            ],
            xLabels: data.weightDates,
            unit: 'kg',
            valueDecimals: 1,
            semanticLabel: _chartSemantics(),
          ),
        },
      ],
    );
  }

  String _chartSemantics() {
    final List<double> h = data.weightHistory;
    if (h.length < 2) return '체중 추이';
    return '체중 추이, ${data.weightDates.first} '
        '${formatNumber(h.first, decimals: 1)}kg에서 '
        '${data.weightDates.last} ${formatNumber(h.last, decimals: 1)}kg';
  }
}

/// 영양: 열량 대비 진행(primary) + 매크로 3개(대상 색). 헤더 액션은 식단 탭으로 간다.
class NutritionCard extends StatelessWidget {
  const NutritionCard({super.key, required this.data, required this.onOpen});

  final DashboardViewData data;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return AppCard(
      title: '영양',
      trailing: AppCardAction(label: '보기', onPressed: onOpen),
      children: <Widget>[
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            kcalOfTarget(context, data.intakeKcal, data.targetKcal),
            const SizedBox(height: AppSpace.s8),
            ShadProgress(
              value: data.intakeRatio.clamp(0.0, 1.0),
              color: cs.primary,
              semanticsLabel: '섭취 열량',
            ),
          ],
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            MacroBar(
              label: '단백질',
              value: data.proteinG,
              target: data.proteinTargetG,
              color: cs.chartProtein,
            ),
            const SizedBox(height: AppSpace.s12),
            MacroBar(
              label: '탄수화물',
              value: data.carbsG,
              target: data.carbsTargetG,
              color: cs.chartCarbs,
            ),
            const SizedBox(height: AppSpace.s12),
            MacroBar(
              label: '지방',
              value: data.fatG,
              target: data.fatTargetG,
              color: cs.chartFat,
            ),
          ],
        ),
      ],
    );
  }
}
