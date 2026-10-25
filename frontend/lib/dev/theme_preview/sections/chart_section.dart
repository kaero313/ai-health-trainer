// Chart 섹션: 시리즈 5색 견본과 §12-3 규칙을 지킨 작은 선 차트.
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_shad_theme.dart';
import '../../../core/design_system/app_text_styles.dart';
import '../../../core/design_system/app_tokens.dart';
import '../widgets.dart';

const List<String> _days = <String>[
  '9/20',
  '9/21',
  '9/22',
  '9/23',
  '9/24',
  '9/25',
  '9/26',
];
const List<double> _protein = <double>[72, 80, 65, 90, 76, 84, 69];
const List<double> _carbs = <double>[190, 210, 175, 220, 200, 185, 165];
const List<double> _fat = <double>[40, 52, 38, 45, 60, 42, 26];

List<Widget> chartSections(BuildContext context) {
  final ShadThemeData theme = ShadTheme.of(context);
  final ShadColorScheme cs = theme.colorScheme;
  final AppColorTokens tokens = AppColorTokens.of(theme.brightness);

  return <Widget>[
    PreviewSection(
      title: 'Chart',
      description: '색은 데이터 대상을 따른다. 글자는 foreground·mutedForeground',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Text(
                '시리즈 5색 · card 대비',
                style: AppTextStyles.caption.copyWith(
                  color: cs.mutedForeground,
                ),
              ),
              const SizedBox(height: AppSpace.s8),
              for (final (String name, Color color) in tokens.chartEntries)
                ColorChipRow(name: name, color: color, against: cs.card),
              const SizedBox(height: AppSpace.s12),
              Wrap(
                spacing: AppSpace.s12,
                runSpacing: AppSpace.s8,
                children: <Widget>[
                  LegendDot(color: cs.chartKcal, label: '열량'),
                  LegendDot(color: cs.chartProtein, label: '단백질'),
                  LegendDot(color: cs.chartCarbs, label: '탄수화물'),
                  LegendDot(color: cs.chartFat, label: '지방'),
                  LegendDot(color: cs.chartExercise, label: '운동'),
                ],
              ),
            ],
          ),
        ),
        PreviewCard(child: _MacroChart(cs: cs)),
      ],
    ),
  ];
}

class _MacroChart extends StatelessWidget {
  const _MacroChart({required this.cs});

  final ShadColorScheme cs;

  LineChartBarData _series(List<double> values, Color color) {
    final int last = values.length - 1;
    return LineChartBarData(
      spots: <FlSpot>[
        for (int i = 0; i < values.length; i++) FlSpot(i.toDouble(), values[i]),
      ],
      isCurved: false,
      color: color,
      barWidth: 2,
      isStrokeCapRound: true,
      // 마지막 값만 8 크기 점 + 2px card 고리
      dotData: FlDotData(
        show: true,
        checkToShowDot: (FlSpot spot, LineChartBarData bar) => spot.x == last,
        getDotPainter:
            (FlSpot spot, double percent, LineChartBarData bar, int index) =>
                FlDotCirclePainter(
                  radius: 4,
                  color: color,
                  strokeWidth: 2,
                  strokeColor: cs.card,
                ),
      ),
      belowBarData: BarAreaData(show: false),
    );
  }

  @override
  Widget build(BuildContext context) {
    final TextStyle axis = AppTextStyles.numSmall.copyWith(
      color: cs.mutedForeground,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Text(
          '매크로 추이',
          style: AppTextStyles.heading.copyWith(color: cs.foreground),
        ),
        const SizedBox(height: AppSpace.s4),
        Text(
          '오늘 탄수화물 165 g · 단백질 69 g · 지방 26 g',
          style: AppTextStyles.bodySmall.copyWith(color: cs.foreground),
        ),
        const SizedBox(height: AppSpace.s16),
        SizedBox(
          height: 180,
          child: LineChart(
            LineChartData(
              minX: 0,
              maxX: 6,
              minY: 0,
              maxY: 240,
              borderData: FlBorderData(show: false),
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: 120,
                getDrawingHorizontalLine: (double value) =>
                    FlLine(color: cs.chartGrid, strokeWidth: 1),
              ),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(),
                rightTitles: const AxisTitles(),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 36,
                    interval: 120,
                    getTitlesWidget: (double value, TitleMeta meta) =>
                        SideTitleWidget(
                          axisSide: meta.axisSide,
                          child: Text(value.toInt().toString(), style: axis),
                        ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 24,
                    interval: 3,
                    getTitlesWidget: (double value, TitleMeta meta) =>
                        SideTitleWidget(
                          axisSide: meta.axisSide,
                          child: Text(_days[value.toInt()], style: axis),
                        ),
                  ),
                ),
              ),
              lineTouchData: LineTouchData(
                touchTooltipData: LineTouchTooltipData(
                  getTooltipColor: (LineBarSpot spot) => cs.popover,
                  getTooltipItems: (List<LineBarSpot> spots) =>
                      <LineTooltipItem>[
                        for (final LineBarSpot s in spots)
                          LineTooltipItem(
                            '${s.y.toInt()} g',
                            AppTextStyles.numSmall.copyWith(
                              color: cs.popoverForeground,
                            ),
                          ),
                      ],
                ),
              ),
              lineBarsData: <LineChartBarData>[
                _series(_protein, cs.chartProtein),
                _series(_carbs, cs.chartCarbs),
                _series(_fat, cs.chartFat),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpace.s12),
        Wrap(
          spacing: AppSpace.s12,
          runSpacing: AppSpace.s8,
          children: <Widget>[
            LegendDot(color: cs.chartProtein, label: '단백질'),
            LegendDot(color: cs.chartCarbs, label: '탄수화물'),
            LegendDot(color: cs.chartFat, label: '지방'),
          ],
        ),
      ],
    );
  }
}
