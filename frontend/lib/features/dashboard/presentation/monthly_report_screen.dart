import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
import '../data/dashboard_repository.dart';
import '../domain/dashboard_controller.dart';

const double _chartHeight = 200;

class MonthlyReportScreen extends ConsumerStatefulWidget {
  const MonthlyReportScreen({super.key});

  @override
  ConsumerState<MonthlyReportScreen> createState() =>
      _MonthlyReportScreenState();
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
    return DateTime(_selectedYear, _selectedMonth).isBefore(_currentMonth);
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
    final NeoTopBar header = NeoTopBar(
      title: _monthLabel,
      showBack: true,
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
    );

    final bool isLoading = monthlyAsync.isLoading || weightAsync.isLoading;
    if (isLoading) {
      return NeoPage(
        header: header,
        onRefresh: _refreshSelectedMonth,
        children: const [
          NeoStateCard(
            icon: Icons.hourglass_top,
            title: '월간 기록을 불러오는 중',
            message: '식단, 운동, 체중 기록을 집계하고 있습니다.',
          ),
        ],
      );
    }

    final Object? firstError =
        monthlyAsync.asError?.error ?? weightAsync.asError?.error;
    if (firstError != null) {
      return NeoPage(
        header: header,
        onRefresh: _refreshSelectedMonth,
        children: [
          NeoStateCard(
            icon: Icons.error_outline,
            title: '월간 리포트를 불러오지 못했습니다',
            message: _extractErrorMessage(firstError),
            actionLabel: '다시 시도',
            onAction: _refreshSelectedMonth,
          ),
        ],
      );
    }

    final Map<String, dynamic> monthlyData = monthlyAsync.requireValue;
    final List<Map<String, dynamic>> nutritionDays = _asMapList(
      monthlyData['nutrition_days'],
    );
    final List<Map<String, dynamic>> recordedNutritionDays = nutritionDays
        .where(_hasNutritionRecord)
        .toList();
    final List<Map<String, dynamic>> exerciseDays = _asMapList(
      monthlyData['exercise_days'],
    );
    final int apiTotalDays = _toRoundedInt(monthlyData['total_days']);
    final int totalDays = apiTotalDays > 0
        ? apiTotalDays
        : DateUtils.getDaysInMonth(_selectedYear, _selectedMonth);
    final List<Map<String, dynamic>> selectedMonthWeightHistory = weightAsync
        .requireValue
        .where((Map<String, dynamic> item) {
          final DateTime? logDate = _tryDateTime(item['log_date']);
          return logDate != null &&
              logDate.year == _selectedYear &&
              logDate.month == _selectedMonth;
        })
        .toList();

    return NeoPage(
      header: header,
      onRefresh: _refreshSelectedMonth,
      children: [
        Text('월간 리포트', style: AppTypography.h1),
        const SizedBox(height: AppSpacing.xs),
        Text(
          '선택한 달에 저장된 실제 기록만 집계합니다.',
          style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.lg),
        _MonthlyActivityCard(
          nutritionDays: recordedNutritionDays,
          exerciseDays: exerciseDays,
        ),
        const SizedBox(height: AppSpacing.md),
        _AverageNutritionCard(
          data: monthlyData,
          hasRecords: recordedNutritionDays.isNotEmpty,
        ),
        const SizedBox(height: AppSpacing.md),
        _ChartCard(
          title: '일별 섭취 열량',
          child: recordedNutritionDays.isEmpty
              ? const _ChartEmptyState(label: '식단 기록 없음')
              : _DailyCaloriesChart(
                  totalDays: totalDays,
                  nutritionDays: recordedNutritionDays,
                ),
        ),
        const SizedBox(height: AppSpacing.md),
        _ChartCard(
          title: '영양소 추이',
          footer: recordedNutritionDays.isEmpty
              ? null
              : const _NutrientLegend(),
          child: recordedNutritionDays.isEmpty
              ? const _ChartEmptyState(label: '영양소 기록 없음')
              : _NutrientTrendChart(
                  totalDays: totalDays,
                  nutritionDays: recordedNutritionDays,
                ),
        ),
        const SizedBox(height: AppSpacing.md),
        _ChartCard(
          title: '체중 변화',
          child: selectedMonthWeightHistory.isEmpty
              ? const _ChartEmptyState(label: '체중 기록 없음')
              : _WeightTrendChart(
                  totalDays: totalDays,
                  weightHistory: selectedMonthWeightHistory,
                ),
        ),
      ],
    );
  }

  static String _extractErrorMessage(Object error) {
    if (error is DashboardRepositoryException) {
      return error.message;
    }
    return error.toString();
  }
}

class _MonthlyActivityCard extends StatelessWidget {
  final List<Map<String, dynamic>> nutritionDays;
  final List<Map<String, dynamic>> exerciseDays;

  const _MonthlyActivityCard({
    required this.nutritionDays,
    required this.exerciseDays,
  });

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> recordedExerciseDays = exerciseDays
        .where((day) => day['exercised'] == true)
        .toList();
    final int totalSets = recordedExerciseDays.fold<int>(
      0,
      (int total, Map<String, dynamic> day) =>
          total + _toRoundedInt(day['total_sets']),
    );

    return NeoGlassCard(
      highlighted: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('이번 달 기록', style: AppTypography.h2),
          const SizedBox(height: AppSpacing.lg),
          Row(
            children: [
              Expanded(
                child: _SummaryMetric(
                  label: '식단 기록',
                  value: '${nutritionDays.length}일',
                  color: AppColors.secondary,
                ),
              ),
              const _MetricDivider(),
              Expanded(
                child: _SummaryMetric(
                  label: '운동 기록',
                  value: '${recordedExerciseDays.length}일',
                  color: AppColors.primary,
                ),
              ),
              const _MetricDivider(),
              Expanded(
                child: _SummaryMetric(
                  label: '총 세트',
                  value: '$totalSets세트',
                  color: AppColors.tertiary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AverageNutritionCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final bool hasRecords;

  const _AverageNutritionCard({required this.data, required this.hasRecords});

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('평균 영양 섭취', style: AppTypography.h2),
          const SizedBox(height: AppSpacing.lg),
          Row(
            children: [
              Expanded(
                child: _SummaryMetric(
                  label: '칼로리',
                  value: hasRecords
                      ? '${_formatMetric(_toDouble(data['avg_calories']))} kcal'
                      : '--',
                  color: AppColors.calories,
                ),
              ),
              const _MetricDivider(),
              Expanded(
                child: _SummaryMetric(
                  label: '단백질',
                  value: hasRecords
                      ? '${_formatMetric(_toDouble(data['avg_protein_g']))} g'
                      : '--',
                  color: AppColors.protein,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: _SummaryMetric(
                  label: '탄수화물',
                  value: hasRecords
                      ? '${_formatMetric(_toDouble(data['avg_carbs_g']))} g'
                      : '--',
                  color: AppColors.carbs,
                ),
              ),
              const _MetricDivider(),
              Expanded(
                child: _SummaryMetric(
                  label: '지방',
                  value: hasRecords
                      ? '${_formatMetric(_toDouble(data['avg_fat_g']))} g'
                      : '--',
                  color: AppColors.fat,
                ),
              ),
            ],
          ),
        ],
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
        Text(label, style: AppTypography.caption, textAlign: TextAlign.center),
        const SizedBox(height: AppSpacing.xs),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            value,
            style: AppTypography.body1.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
            textAlign: TextAlign.center,
          ),
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
      height: 48,
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
      color: AppColors.divider,
    );
  }
}

class _ChartCard extends StatelessWidget {
  final String title;
  final Widget child;
  final Widget? footer;

  const _ChartCard({required this.title, required this.child, this.footer});

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTypography.h2),
          const SizedBox(height: AppSpacing.lg),
          SizedBox(height: _chartHeight, child: child),
          if (footer != null) ...[
            const SizedBox(height: AppSpacing.md),
            footer!,
          ],
        ],
      ),
    );
  }
}

class _ChartEmptyState extends StatelessWidget {
  final String label;

  const _ChartEmptyState({required this.label});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.query_stats,
            color: AppColors.textDisabled,
            size: 30,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            label,
            style: AppTypography.body2.copyWith(color: AppColors.textDisabled),
          ),
        ],
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
    final List<FlSpot> spots = _buildDateSpots(
      nutritionDays,
      dateKey: 'date',
      valueKey: 'calories',
    );
    final ({double minY, double maxY}) range = _resolveChartRange(
      spots.map((spot) => spot.y).toList(),
      startAtZero: true,
    );

    return LineChart(
      LineChartData(
        minX: 1,
        maxX: totalDays.toDouble(),
        minY: range.minY,
        maxY: range.maxY,
        gridData: _gridData,
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: _formatAxisValue,
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) =>
              '${spot.x.toInt()}일\n${spot.y.round()} kcal',
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
    final List<FlSpot> proteinSpots = _buildDateSpots(
      nutritionDays,
      dateKey: 'date',
      valueKey: 'protein_g',
    );
    final List<FlSpot> carbsSpots = _buildDateSpots(
      nutritionDays,
      dateKey: 'date',
      valueKey: 'carbs_g',
    );
    final List<FlSpot> fatSpots = _buildDateSpots(
      nutritionDays,
      dateKey: 'date',
      valueKey: 'fat_g',
    );
    final List<double> allValues = [
      ...proteinSpots.map((spot) => spot.y),
      ...carbsSpots.map((spot) => spot.y),
      ...fatSpots.map((spot) => spot.y),
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
        gridData: _gridData,
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: _formatAxisValue,
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) =>
              '${spot.x.toInt()}일\n${_formatMetric(spot.y)} g',
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
    final List<FlSpot> spots = _buildDateSpots(
      weightHistory,
      dateKey: 'log_date',
      valueKey: 'weight_kg',
    );
    final ({double minY, double maxY}) range = _resolveChartRange(
      spots.map((spot) => spot.y).toList(),
      startAtZero: false,
    );

    return LineChart(
      LineChartData(
        minX: 1,
        maxX: totalDays.toDouble(),
        minY: range.minY,
        maxY: range.maxY,
        gridData: _gridData,
        borderData: FlBorderData(show: false),
        titlesData: _buildTitlesData(
          totalDays: totalDays,
          leftInterval: _resolveLeftInterval(range.maxY - range.minY),
          leftLabelBuilder: _formatMetric,
        ),
        lineTouchData: _buildTouchData(
          valueBuilder: (LineBarSpot spot) =>
              '${spot.x.toInt()}일\n${_formatMetric(spot.y)} kg',
        ),
        lineBarsData: [
          _buildLineBarData(
            spots: spots,
            color: AppColors.primary,
            showArea: true,
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

  const _LegendItem({required this.label, required this.color});

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

const FlGridData _gridData = FlGridData(show: false);

List<FlSpot> _buildDateSpots(
  List<Map<String, dynamic>> items, {
  required String dateKey,
  required String valueKey,
}) {
  final List<FlSpot> spots = [];
  for (final Map<String, dynamic> item in items) {
    final DateTime? date = _tryDateTime(item[dateKey]);
    final double? value = _toNullableDouble(item[valueKey]);
    if (date != null && value != null) {
      spots.add(FlSpot(date.day.toDouble(), value));
    }
  }
  spots.sort((a, b) => a.x.compareTo(b.x));
  return spots;
}

LineChartBarData _buildLineBarData({
  required List<FlSpot> spots,
  required Color color,
  bool showArea = false,
}) {
  return LineChartBarData(
    spots: spots,
    color: color,
    barWidth: 3,
    isCurved: spots.length > 2,
    isStrokeCapRound: true,
    dotData: FlDotData(
      show: spots.length <= 8,
      getDotPainter: (_, __, ___, ____) =>
          FlDotCirclePainter(radius: 3, color: color, strokeWidth: 0),
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
        reservedSize: 24,
        interval: bottomInterval,
        getTitlesWidget: (double value, TitleMeta meta) {
          final int day = value.round();
          final bool shouldShow =
              day == 1 || day == totalDays || day % bottomInterval == 0;
          if (!shouldShow || day < 1 || day > totalDays) {
            return const SizedBox.shrink();
          }
          return SideTitleWidget(
            axisSide: meta.axisSide,
            space: AppSpacing.sm,
            child: Text(
              '$day',
              style: AppTypography.caption.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          );
        },
      ),
    ),
    leftTitles: AxisTitles(
      sideTitles: SideTitles(
        showTitles: true,
        reservedSize: 42,
        interval: leftInterval,
        getTitlesWidget: (double value, TitleMeta meta) => SideTitleWidget(
          axisSide: meta.axisSide,
          space: AppSpacing.xs,
          child: Text(
            leftLabelBuilder(value),
            style: AppTypography.caption.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
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
      tooltipRoundedRadius: AppRadius.sm,
      tooltipPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      tooltipMargin: AppSpacing.sm,
      getTooltipColor: (_) => AppColors.surfaceHigh,
      getTooltipItems: (List<LineBarSpot> spots) => spots
          .map(
            (spot) => LineTooltipItem(
              valueBuilder(spot),
              AppTypography.caption.copyWith(
                color: spot.bar.color ?? AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          )
          .toList(),
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
  final double minValue = values.reduce(math.min);
  final double maxValue = values.reduce(math.max);
  if (startAtZero) {
    return (minY: 0, maxY: math.max(maxValue * 1.2, 1));
  }
  final double span = maxValue - minValue;
  final double padding = math.max(span * 0.2, 1);
  return (minY: math.max(minValue - padding, 0), maxY: maxValue + padding);
}

double _resolveLeftInterval(double span) {
  if (span <= 1) return 0.2;
  if (span <= 2) return 0.5;
  if (span <= 5) return 1;
  if (span <= 10) return 2;
  if (span <= 25) return 5;
  if (span <= 50) return 10;
  if (span <= 100) return 20;
  if (span <= 250) return 50;
  if (span <= 500) return 100;
  return math.max((span / 4).roundToDouble(), 1);
}

List<Map<String, dynamic>> _asMapList(Object? value) {
  if (value is! List) {
    return <Map<String, dynamic>>[];
  }
  return value
      .whereType<Map>()
      .map(
        (item) => item.map<String, dynamic>(
          (key, value) => MapEntry<String, dynamic>(key.toString(), value),
        ),
      )
      .toList();
}

bool _hasNutritionRecord(Map<String, dynamic> day) {
  return _toDouble(day['calories']) > 0 ||
      _toDouble(day['protein_g']) > 0 ||
      _toDouble(day['carbs_g']) > 0 ||
      _toDouble(day['fat_g']) > 0;
}

double _toDouble(Object? value) => _toNullableDouble(value) ?? 0;

double? _toNullableDouble(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

int _toRoundedInt(Object? value) => _toDouble(value).round();

DateTime? _tryDateTime(Object? value) {
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value?.toString() ?? '');
}

String _formatAxisValue(double value) {
  if (value >= 1000) {
    return '${(value / 1000).toStringAsFixed(value >= 10000 ? 0 : 1)}k';
  }
  return _formatMetric(value);
}

String _formatMetric(double value) {
  return value % 1 == 0 ? value.toStringAsFixed(0) : value.toStringAsFixed(1);
}
