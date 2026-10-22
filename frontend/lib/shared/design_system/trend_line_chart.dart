// 추이 선 차트 (docs/DESIGN_SYSTEM.md §12-3). fl_chart 단일·다중 시리즈.
// 선 2, 곡선 없음, 가로 격자 1px chartGrid, y축 최소·중간·최대, x축 시작·끝, 마지막 점만 표시.
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_badge.dart';
import 'app_number_format.dart';
import 'trend_scale.dart';

@immutable
class TrendSeries {
  const TrendSeries({
    required this.label,
    required this.color,
    required this.values,
  });

  final String label;

  /// 데이터 대상 색(chartKcal 등). 선과 점에만 쓴다.
  final Color color;

  /// x 위치는 [TrendLineChart.xLabels]의 같은 순번이다.
  final List<double> values;
}

class TrendLineChart extends StatelessWidget {
  const TrendLineChart({
    super.key,
    required this.series,
    required this.xLabels,
    this.unit = '',
    this.valueDecimals = 0,
    this.height = defaultHeight,
    this.semanticLabel,
  });

  /// 축 라벨 영역을 포함한 기본 높이.
  static const double defaultHeight = 160;
  static const double leftAxisWidth = 40;
  static const double bottomAxisHeight = 24;
  static const String sparseMessage = '기록이 2개 이상 쌓이면 추이를 보여드립니다';

  final List<TrendSeries> series;
  final List<String> xLabels;

  /// 툴팁 값 뒤에 붙는 단위(예: "kg").
  final String unit;

  /// 툴팁 값 소수 자릿수(체중 1, 열량 0).
  final int valueDecimals;
  final double height;
  final String? semanticLabel;

  int get _pointCount => series.fold<int>(
    0,
    (int n, TrendSeries s) => math.max(n, s.values.length),
  );

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    if (_pointCount < 2) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpace.s12),
        child: Text(
          sparseMessage,
          style: AppTextStyles.bodySmall.copyWith(color: cs.mutedForeground),
        ),
      );
    }
    final Widget chart = Semantics(
      label: semanticLabel,
      excludeSemantics: semanticLabel != null,
      child: SizedBox(
        height: height,
        child: LineChart(
          _data(cs, MediaQuery.textScalerOf(context).scale(1)),
          duration: Duration.zero,
        ),
      ),
    );
    if (series.length < 2) return chart;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        chart,
        const SizedBox(height: AppSpace.s12),
        Wrap(
          spacing: AppSpace.s12,
          runSpacing: AppSpace.s8,
          children: <Widget>[
            for (final TrendSeries s in series)
              AppLegendDot(color: s.color, label: s.label),
          ],
        ),
      ],
    );
  }

  /// [textScale]: 큰 글자 배율에서 축 라벨이 잘리지 않게 라벨 영역을 같은 비율로 넓힌다.
  LineChartData _data(ShadColorScheme cs, double textScale) {
    final List<double> all = <double>[
      for (final TrendSeries s in series) ...s.values,
    ];
    final TrendScale scale = TrendScale.fit(
      all.reduce(math.min),
      all.reduce(math.max),
    );
    final TextStyle axis = AppTextStyles.numSmall.copyWith(
      color: cs.mutedForeground,
    );
    final int lastX = _pointCount - 1;
    return LineChartData(
      minX: 0,
      maxX: lastX.toDouble(),
      minY: scale.min,
      maxY: scale.max,
      borderData: FlBorderData(show: false),
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: scale.step,
        getDrawingHorizontalLine: (double _) =>
            FlLine(color: cs.chartGrid, strokeWidth: 1),
      ),
      titlesData: FlTitlesData(
        topTitles: const AxisTitles(),
        rightTitles: const AxisTitles(),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: leftAxisWidth * textScale,
            interval: scale.step,
            getTitlesWidget: (double value, TitleMeta meta) => SideTitleWidget(
              axisSide: meta.axisSide,
              space: AppSpace.s8,
              child: Text(
                scale.format(value),
                maxLines: 1,
                softWrap: false,
                style: axis,
              ),
            ),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: bottomAxisHeight * textScale,
            interval: lastX.toDouble(),
            getTitlesWidget: (double value, TitleMeta meta) {
              final int i = value.round();
              if (i != 0 && i != lastX) return const SizedBox.shrink();
              return SideTitleWidget(
                axisSide: meta.axisSide,
                space: AppSpace.s8,
                fitInside: SideTitleFitInsideData.fromTitleMeta(
                  meta,
                  distanceFromEdge: 0,
                ),
                child: Text(i < xLabels.length ? xLabels[i] : '', style: axis),
              );
            },
          ),
        ),
      ),
      lineTouchData: LineTouchData(
        // 선택한 값: 1px 세로 기준선 + 지름 8 점 + 2px card 고리
        getTouchedSpotIndicator: (LineChartBarData bar, List<int> indexes) =>
            <TouchedSpotIndicatorData>[
              for (final int _ in indexes)
                TouchedSpotIndicatorData(
                  FlLine(color: cs.mutedForeground, strokeWidth: 1),
                  FlDotData(
                    getDotPainter:
                        (FlSpot _, double _, LineChartBarData _, int _) =>
                            FlDotCirclePainter(
                              radius: 4,
                              color: bar.color ?? cs.foreground,
                              strokeWidth: 2,
                              strokeColor: cs.card,
                            ),
                  ),
                ),
            ],
        touchTooltipData: LineTouchTooltipData(
          getTooltipColor: (LineBarSpot _) => cs.popover,
          tooltipBorder: BorderSide(color: cs.border),
          tooltipRoundedRadius: AppRadii.md,
          tooltipPadding: const EdgeInsets.symmetric(
            horizontal: AppSpace.s12,
            vertical: AppSpace.s8,
          ),
          fitInsideHorizontally: true,
          fitInsideVertically: true,
          getTooltipItems: (List<LineBarSpot> spots) => <LineTooltipItem>[
            for (final LineBarSpot s in spots)
              LineTooltipItem(
                _tooltipText(s, scale),
                AppTextStyles.numSmall.copyWith(color: cs.popoverForeground),
              ),
          ],
        ),
      ),
      lineBarsData: <LineChartBarData>[
        for (final TrendSeries s in series)
          _bar(s, cs, fill: series.length == 1),
      ],
    );
  }

  String _tooltipText(LineBarSpot spot, TrendScale scale) {
    final int i = spot.x.round();
    final String date = i < xLabels.length ? xLabels[i] : '';
    final String name = series.length > 1
        ? '${series[spot.barIndex].label} '
        : '';
    final String suffix = unit.isEmpty ? '' : ' $unit';
    return '$date · $name${formatNumber(spot.y, decimals: valueDecimals)}$suffix';
  }

  LineChartBarData _bar(
    TrendSeries s,
    ShadColorScheme cs, {
    required bool fill,
  }) {
    final int last = s.values.length - 1;
    return LineChartBarData(
      spots: <FlSpot>[
        for (int i = 0; i < s.values.length; i++)
          FlSpot(i.toDouble(), s.values[i]),
      ],
      isCurved: false,
      color: s.color,
      barWidth: 2,
      isStrokeCapRound: true,
      // 마지막 값만 지름 8 점 + 2px card 고리
      dotData: FlDotData(
        show: true,
        checkToShowDot: (FlSpot spot, LineChartBarData _) => spot.x == last,
        getDotPainter: (FlSpot _, double _, LineChartBarData _, int _) =>
            FlDotCirclePainter(
              radius: 4,
              color: s.color,
              strokeWidth: 2,
              strokeColor: cs.card,
            ),
      ),
      // 면 채우기는 단일 시리즈만 10%
      belowBarData: BarAreaData(
        show: fill,
        color: s.color.withValues(alpha: 0.1),
      ),
    );
  }
}
