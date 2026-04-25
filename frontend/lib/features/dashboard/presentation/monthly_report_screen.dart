import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/dashboard_repository.dart';
import '../domain/dashboard_controller.dart';

const double _chartHeight = 200;

final BoxDecoration _reportCardDecoration = BoxDecoration(
  color: AppColors.surface,
  borderRadius: BorderRadius.circular(AppRadius.lg),
  border: Border.all(color: AppColors.divider, width: 0.5),
);

class MonthlyReportScreen extends ConsumerStatefulWidget {
  const MonthlyReportScreen({super.key});

  @override
  ConsumerState<MonthlyReportScreen> createState() => _MonthlyReportScreenState();
}

class _MonthlyReportScreenState extends ConsumerState<MonthlyReportScreen> {
  late final DateTime _currentMonth;
  late int _selectedYear;
  late int _selectedMonth;

  @override
  void initState() {
    super.initState();
    final DateTime now = DateTime.now();
    _currentMonth = DateTime(now.year, now.month);
    _selectedYear = _currentMonth.year;
    _selectedMonth = _currentMonth.month;
  }

  String get _monthKey =>
      '${_selectedYear.toString().padLeft(4, '0')}-${_selectedMonth.toString().padLeft(2, '0')}';

  String get _monthLabel =>
      DateFormat('yyyy년 M월').format(DateTime(_selectedYear, _selectedMonth));

  bool get _canMoveNext {
    final DateTime selectedMonth = DateTime(_selectedYear, _selectedMonth);
    return selectedMonth.isBefore(_currentMonth);
  }

  void _changeMonth(int offset) {
    final DateTime nextMonth = DateTime(_selectedYear, _selectedMonth + offset);
    final DateTime normalizedMonth = DateTime(nextMonth.year, nextMonth.month);
    if (normalizedMonth.isAfter(_currentMonth)) {
      return;
    }

    setState(() {
      _selectedYear = normalizedMonth.year;
      _selectedMonth = normalizedMonth.month;
    });
  }

  Future<void> _refreshSelectedMonth() async {
    final String monthKey = _monthKey;
    ref.invalidate(monthlyDashboardProvider(monthKey));
    ref.invalidate(weightHistoryProvider(monthKey));
    await Future<void>.delayed(const Duration(milliseconds: 300));
  }

  @override
  Widget build(BuildContext context) {
    final String monthKey = _monthKey;
    final AsyncValue<Map<String, dynamic>> monthlyAsync = ref.watch(
      monthlyDashboardProvider(monthKey),
    );
    final AsyncValue<List<Map<String, dynamic>>> weightAsync = ref.watch(
      weightHistoryProvider(monthKey),
    );

    final bool isLoading = monthlyAsync.isLoading || weightAsync.isLoading;
    final Object? firstError = monthlyAsync.asError?.error ?? weightAsync.asError?.error;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        titleSpacing: AppSpacing.sm,
        title: Text(_monthLabel, style: AppTypography.h3),
        actions: [
          IconButton(
            onPressed: () => _changeMonth(-1),
            icon: const Icon(Icons.chevron_left),
            color: AppColors.textPrimary,
            tooltip: '이전 달',
          ),
          IconButton(
            onPressed: _canMoveNext ? () => _changeMonth(1) : null,
            icon: const Icon(Icons.chevron_right),
            color: _canMoveNext ? AppColors.textPrimary : AppColors.textDisabled,
            tooltip: '다음 달',
          ),
        ],
      ),
      body: Builder(
        builder: (BuildContext context) {
          if (isLoading) {
            return const _MonthlyReportLoadingView();
          }

          if (firstError != null) {
            return _MonthlyReportErrorView(
              message: _extractErrorMessage(firstError),
              onRetry: _refreshSelectedMonth,
            );
          }

          final Map<String, dynamic> monthlyData = monthlyAsync.requireValue;
          final List<Map<String, dynamic>> nutritionDays = _asMapList(
            monthlyData['nutrition_days'],
          );
          final int totalDays = max(
            _toRoundedInt(monthlyData['total_days']),
            nutritionDays.length,
          );
          final List<Map<String, dynamic>> selectedMonthWeightHistory =
              weightAsync.requireValue.where((Map<String, dynamic> item) {
                final DateTime logDate = _toDateTime(item['log_date']);
                return logDate.year == _selectedYear && logDate.month == _selectedMonth;
              }).toList();

          return RefreshIndicator(
            color: AppColors.primary,
            onRefresh: _refreshSelectedMonth,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _AverageNutritionSummaryCard(data: monthlyData),
                  const SizedBox(height: AppSpacing.md),
                  _ChartCard(
                    title: '일별 칼로리 라인 차트',
                    child: _DailyCaloriesChart(
                      totalDays: totalDays,
                      nutritionDays: nutritionDays,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _ChartCard(
                    title: '영양소 트렌드 차트',
                    footer: const _NutrientLegend(),
                    child: _NutrientTrendChart(
                      totalDays: totalDays,
                      nutritionDays: nutritionDays,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _ChartCard(
                    title: '체중 변화 차트',
                    child: _WeightTrendChart(
                      totalDays: totalDays,
                      weightHistory: selectedMonthWeightHistory,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  String _extractErrorMessage(Object error) {
    if (error is DashboardRepositoryException) {
      return error.message;
    }
    return error.toString();
  }
}

class _AverageNutritionSummaryCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _AverageNutritionSummaryCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: _reportCardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '평균 영양소 요약',
              style: AppTypography.body1.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: _SummaryMetric(
                    label: '칼로리',
                    value: '${_formatMetric(_toDouble(data['avg_calories']))}kcal',
                    color: AppColors.calories,
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _SummaryMetric(
                    label: '단백질',
                    value: '${_formatMetric(_toDouble(data['avg_protein_g']))}g',
                    color: AppColors.protein,
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _SummaryMetric(
                    label: '탄수화물',
                    value: '${_formatMetric(_toDouble(data['avg_carbs_g']))}g',
                    color: AppColors.carbs,
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _SummaryMetric(
                    label: '지방',
                    value: '${_formatMetric(_toDouble(data['avg_fat_g']))}g',
                    color: AppColors.fat,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryMetric extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _SummaryMetric({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          value,
          style: AppTypography.body1.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _MetricDivider extends StatelessWidget {
  const _MetricDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: AppSpacing.xxl,
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
      color: AppColors.divider,
    );
  }
}

class _ChartCard extends StatelessWidget {
  final String title;
  final Widget child;
  final Widget? footer;

  const _ChartCard({
    required this.title,
    required this.child,
    this.footer,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: _reportCardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: AppTypography.body1.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.md),
            SizedBox(height: _chartHeight, child: child),
            if (footer != null) ...[
              const SizedBox(height: AppSpacing.md),
              footer!,
            ],
          ],
        ),
      ),
    );
  }
}

class _DailyCaloriesChart extends StatelessWidget {
  final int totalDays;
  final List<Map<String, dynamic>> nutritionDays;

  const _DailyCaloriesChart({
    required this.totalDays,
    required this.nutritionDays,
  });

  @override
  Widget build(BuildContext context) {
    final List<FlSpot> spots = nutritionDays
        .map(
          (Map<String, dynamic> item) => FlSpot(
            _toDateTime(item['date']).day.toDouble(),
            _toDouble(item['calories']),
          ),
        )
        .toList();
    final ({double minY, double maxY}) range = _resolveChartRange(
      spots.map((FlSpot spot) => spot.y).toList(),
      startAtZero: true,
    );

    return LineChart(
      LineChartData(
        minX: 1,
        maxX: totalDays.toDouble(),
        minY: range.minY,
        maxY: range.maxY,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: (double value) => _formatAxisValue(value),
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) => '${spot.x.toInt()}일\n${spot.y.round()} kcal',
        ),
        lineBarsData: [
          _buildLineBarData(
            spots: spots,
            color: AppColors.calories,
            showArea: true,
          ),
        ],
      ),
    );
  }
}

class _NutrientTrendChart extends StatelessWidget {
  final int totalDays;
  final List<Map<String, dynamic>> nutritionDays;

  const _NutrientTrendChart({
    required this.totalDays,
    required this.nutritionDays,
  });

  @override
  Widget build(BuildContext context) {
    final List<FlSpot> proteinSpots = _buildNutritionSpots(
      nutritionDays,
      'protein_g',
    );
    final List<FlSpot> carbsSpots = _buildNutritionSpots(
      nutritionDays,
      'carbs_g',
    );
    final List<FlSpot> fatSpots = _buildNutritionSpots(
      nutritionDays,
      'fat_g',
    );
    final List<double> allValues = [
      ...proteinSpots.map((FlSpot spot) => spot.y),
      ...carbsSpots.map((FlSpot spot) => spot.y),
      ...fatSpots.map((FlSpot spot) => spot.y),
    ];
    final ({double minY, double maxY}) range = _resolveChartRange(
      allValues,
      startAtZero: true,
    );

    return LineChart(
      LineChartData(
        minX: 1,
        maxX: totalDays.toDouble(),
        minY: range.minY,
        maxY: range.maxY,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: (double value) => _formatAxisValue(value),
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) => '${spot.x.toInt()}일\n${_formatMetric(spot.y)}g',
        ),
        lineBarsData: [
          _buildLineBarData(spots: proteinSpots, color: AppColors.protein),
          _buildLineBarData(spots: carbsSpots, color: AppColors.carbs),
          _buildLineBarData(spots: fatSpots, color: AppColors.fat),
        ],
      ),
    );
  }
}

class _WeightTrendChart extends StatelessWidget {
  final int totalDays;
  final List<Map<String, dynamic>> weightHistory;

  const _WeightTrendChart({
    required this.totalDays,
    required this.weightHistory,
  });

  @override
  Widget build(BuildContext context) {
    if (weightHistory.isEmpty) {
      return Center(
        child: Text(
          '체중 기록이 없습니다',
          style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
        ),
      );
    }

    final List<FlSpot> spots = weightHistory
        .map(
          (Map<String, dynamic> item) => FlSpot(
            _toDateTime(item['log_date']).day.toDouble(),
            _toDouble(item['weight_kg']),
          ),
        )
        .toList();
    final ({double minY, double maxY}) range = _resolveChartRange(
      spots.map((FlSpot spot) => spot.y).toList(),
      startAtZero: false,
    );

    return LineChart(
      LineChartData(
        minX: 1,
        maxX: totalDays.toDouble(),
        minY: range.minY,
        maxY: range.maxY,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: (double value) => _formatMetric(value),
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) => '${spot.x.toInt()}일\n${_formatMetric(spot.y)}kg',
        ),
        lineBarsData: [
          _buildLineBarData(
            spots: spots,
            color: AppColors.primary,
            showArea: true,
            showDots: spots.length == 1,
          ),
        ],
      ),
    );
  }
}

class _NutrientLegend extends StatelessWidget {
  const _NutrientLegend();

  @override
  Widget build(BuildContext context) {
    return const Wrap(
      spacing: AppSpacing.md,
      runSpacing: AppSpacing.sm,
      children: [
        _LegendItem(label: '단백질', color: AppColors.protein),
        _LegendItem(label: '탄수화물', color: AppColors.carbs),
        _LegendItem(label: '지방', color: AppColors.fat),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  final String label;
  final Color color;

  const _LegendItem({
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: AppSpacing.sm,
          height: AppSpacing.sm,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(AppSpacing.xs),
          ),
        ),
        const SizedBox(width: AppSpacing.xs),
        Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

class _MonthlyReportLoadingView extends StatelessWidget {
  const _MonthlyReportLoadingView();

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.surface,
      highlightColor: AppColors.surfaceLight,
      child: ColoredBox(
        color: AppColors.background,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.lg),
          children: [
            _buildSkeletonCard(height: AppSpacing.xxl * 2 + AppSpacing.sm),
            const SizedBox(height: AppSpacing.md),
            _buildSkeletonCard(height: _chartHeight + AppSpacing.xxl),
            const SizedBox(height: AppSpacing.md),
            _buildSkeletonCard(
              height: _chartHeight + AppSpacing.xxl + AppSpacing.md,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildSkeletonCard(height: _chartHeight + AppSpacing.xxl),
          ],
        ),
      ),
    );
  }

  Widget _buildSkeletonCard({required double height}) {
    return DecoratedBox(
      decoration: _reportCardDecoration.copyWith(color: AppColors.surface),
      child: SizedBox(height: height),
    );
  }
}

class _MonthlyReportErrorView extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;

  const _MonthlyReportErrorView({
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body2.copyWith(color: AppColors.error),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton(
              onPressed: () => onRetry(),
              child: Text(
                '다시 시도',
                style: AppTypography.body2.copyWith(color: AppColors.primary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

List<FlSpot> _buildNutritionSpots(
  List<Map<String, dynamic>> nutritionDays,
  String key,
) {
  return nutritionDays
      .map(
        (Map<String, dynamic> item) => FlSpot(
          _toDateTime(item['date']).day.toDouble(),
          _toDouble(item[key]),
        ),
      )
      .toList();
}

LineChartBarData _buildLineBarData({
  required List<FlSpot> spots,
  required Color color,
  bool showArea = false,
  bool showDots = false,
}) {
  return LineChartBarData(
    spots: spots,
    color: color,
    barWidth: AppSpacing.xs - 1,
    isCurved: true,
    isStrokeCapRound: true,
    dotData: FlDotData(
      show: showDots,
      getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
        radius: AppSpacing.xs - 1,
        color: color,
        strokeWidth: 0,
      ),
    ),
    belowBarData: BarAreaData(
      show: showArea,
      color: color.withValues(alpha: 0.16),
    ),
  );
}

FlTitlesData _buildTitlesData({
  required int totalDays,
  required double leftInterval,
  required String Function(double value) leftLabelBuilder,
}) {
  final double bottomInterval = totalDays <= 10 ? 1 : 5;

  return FlTitlesData(
    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    bottomTitles: AxisTitles(
      sideTitles: SideTitles(
        showTitles: true,
        reservedSize: AppSpacing.lg,
        interval: bottomInterval,
        getTitlesWidget: (double value, TitleMeta meta) {
          final int day = value.round();
          final bool shouldShow = day == 1 || day == totalDays || day % bottomInterval == 0;
          if (!shouldShow || day < 1 || day > totalDays) {
            return const SizedBox.shrink();
          }

          return SideTitleWidget(
            axisSide: meta.axisSide,
            space: AppSpacing.sm,
            child: Text(
              '$day',
              style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
            ),
          );
        },
      ),
    ),
    leftTitles: AxisTitles(
      sideTitles: SideTitles(
        showTitles: true,
        reservedSize: AppSpacing.xxl,
        interval: leftInterval,
        getTitlesWidget: (double value, TitleMeta meta) {
          return SideTitleWidget(
            axisSide: meta.axisSide,
            space: AppSpacing.sm,
            child: Text(
              leftLabelBuilder(value),
              style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
            ),
          );
        },
      ),
    ),
  );
}

LineTouchData _buildTouchData({
  required String Function(LineBarSpot spot) valueBuilder,
}) {
  return LineTouchData(
    handleBuiltInTouches: true,
    touchTooltipData: LineTouchTooltipData(
      fitInsideHorizontally: true,
      fitInsideVertically: true,
      tooltipRoundedRadius: AppRadius.md,
      tooltipPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      tooltipMargin: AppSpacing.md,
      getTooltipColor: (_) => AppColors.surfaceLight,
      getTooltipItems: (List<LineBarSpot> touchedSpots) {
        return touchedSpots.map((LineBarSpot spot) {
          final Color labelColor = spot.bar.color ?? AppColors.textPrimary;
          return LineTooltipItem(
            valueBuilder(spot),
            AppTypography.caption.copyWith(
              color: labelColor,
              fontWeight: FontWeight.w700,
            ),
          );
        }).toList();
      },
    ),
  );
}

({double minY, double maxY}) _resolveChartRange(
  List<double> values, {
  required bool startAtZero,
}) {
  if (values.isEmpty) {
    return (minY: 0, maxY: 1);
  }

  final double minValue = values.reduce(min);
  final double maxValue = values.reduce(max);

  if (startAtZero) {
    return (minY: 0, maxY: max(maxValue * 1.2, 1));
  }

  final double span = maxValue - minValue;
  final double padding = max(span * 0.2, 1);

  if (span == 0) {
    return (
      minY: max(minValue - padding, 0),
      maxY: maxValue + padding,
    );
  }

  return (
    minY: max(minValue - padding, 0),
    maxY: maxValue + padding,
  );
}

double _resolveLeftInterval(double span) {
  if (span <= 1) {
    return 0.2;
  }
  if (span <= 2) {
    return 0.5;
  }
  if (span <= 5) {
    return 1;
  }
  if (span <= 10) {
    return 2;
  }
  if (span <= 25) {
    return 5;
  }
  if (span <= 50) {
    return 10;
  }
  if (span <= 100) {
    return 20;
  }
  if (span <= 250) {
    return 50;
  }
  if (span <= 500) {
    return 100;
  }
  return max((span / 4).roundToDouble(), 1);
}

List<Map<String, dynamic>> _asMapList(dynamic value) {
  if (value is! List<dynamic>) {
    return <Map<String, dynamic>>[];
  }

  return value
      .whereType<Map<dynamic, dynamic>>()
      .map(
        (Map<dynamic, dynamic> item) => item.map<String, dynamic>(
          (dynamic key, dynamic value) => MapEntry<String, dynamic>(
            key.toString(),
            value,
          ),
        ),
      )
      .toList();
}

String _formatAxisValue(double value) {
  if (value >= 1000) {
    return value.round().toString();
  }
  if (value % 1 == 0) {
    return value.toStringAsFixed(0);
  }
  return value.toStringAsFixed(1);
}

String _formatMetric(double value) {
  if (value % 1 == 0) {
    return value.toStringAsFixed(0);
  }
  return value.toStringAsFixed(1);
}

double _toDouble(dynamic value) {
  if (value == null) {
    return 0;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString()) ?? 0;
}

int _toRoundedInt(dynamic value) {
  return _toDouble(value).round();
}

DateTime _toDateTime(dynamic value) {
  if (value is DateTime) {
    return value;
  }

  final String raw = value?.toString() ?? '';
  final DateTime? parsed = DateTime.tryParse(raw);
  if (parsed != null) {
    return parsed;
  }
  return DateTime.now();
}
