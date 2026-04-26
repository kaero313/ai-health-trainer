import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/diet_repository.dart';
import '../domain/diet_controller.dart';

class DietScreen extends ConsumerWidget {
  const DietScreen({super.key});

  static const List<String> _mealOrder = <String>[
    'breakfast',
    'lunch',
    'dinner',
    'snack',
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final DateTime selectedDate = ref.watch(selectedDietDateProvider);
    final AsyncValue<Map<String, dynamic>> dietLogsAsync = ref.watch(
      dietLogsProvider,
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('식단 기록'),
        actions: [
          TextButton.icon(
            onPressed: () => _pickDate(context, ref, selectedDate),
            icon: const Icon(
              Icons.calendar_today,
              size: 16,
              color: AppColors.primary,
            ),
            label: Text(
              DateFormat('yyyy-MM-dd').format(selectedDate),
              style: AppTypography.body2.copyWith(color: AppColors.primary),
            ),
          ),
        ],
      ),
      body: dietLogsAsync.when(
        loading: () => const _DietLoadingView(),
        error:
            (Object error, StackTrace _) => _DietErrorView(
              message: _extractErrorMessage(error),
              onRetry: () => ref.invalidate(dietLogsProvider),
            ),
        data:
            (Map<String, dynamic> data) => RefreshIndicator(
              color: AppColors.primary,
              onRefresh: () async {
                ref.invalidate(dietLogsProvider);
                await Future<void>.delayed(const Duration(milliseconds: 300));
              },
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final String mealType in _mealOrder) ...[
                      _MealSection(
                        mealType: mealType,
                        mealLabel: _mealLabel(mealType),
                        logs: _readMealLogs(data, mealType),
                        onDelete:
                            (int logId) => _deleteLog(context, ref, logId),
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    _DailySummaryCard(data: data),
                    const SizedBox(height: AppSpacing.md),
                    const _BottomActionButtons(),
                    const SizedBox(height: AppSpacing.xl),
                  ],
                ),
              ),
            ),
      ),
    );
  }

  Future<void> _pickDate(
    BuildContext context,
    WidgetRef ref,
    DateTime currentDate,
  ) async {
    final DateTime now = DateTime.now();
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: currentDate,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 2),
      locale: const Locale('ko'),
    );
    if (pickedDate == null) {
      return;
    }
    ref.read(selectedDietDateProvider.notifier).state = pickedDate;
  }

  Future<bool> _deleteLog(
    BuildContext context,
    WidgetRef ref,
    int logId,
  ) async {
    try {
      await deleteDietLogAndRefresh(ref, logId);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('식단 기록을 삭제했습니다.')));
      }
      return true;
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_extractErrorMessage(error))));
      }
      return false;
    }
  }

  List<Map<String, dynamic>> _readMealLogs(
    Map<String, dynamic> data,
    String mealType,
  ) {
    final Map<String, dynamic> meals =
        data['meals'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final List<dynamic> mealLogs =
        meals[mealType] as List<dynamic>? ?? <dynamic>[];
    return mealLogs.whereType<Map<String, dynamic>>().toList();
  }
}

class _MealSection extends StatelessWidget {
  final String mealType;
  final String mealLabel;
  final List<Map<String, dynamic>> logs;
  final Future<bool> Function(int logId) onDelete;

  const _MealSection({
    required this.mealType,
    required this.mealLabel,
    required this.logs,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final double sectionCalories = logs.fold<double>(
      0,
      (double total, Map<String, dynamic> log) => total + _logCalories(log),
    );

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(mealLabel, style: AppTypography.h3),
                Text(
                  '${_formatNumber(sectionCalories)} kcal',
                  style: AppTypography.body2.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            if (logs.isEmpty)
              _EmptyMealSection(mealType: mealType)
            else
              Column(
                children: [
                  for (final Map<String, dynamic> log in logs) ...[
                    _DietLogCard(log: log, onDelete: onDelete),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                ],
              ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () => _openDietAddScreen(context, mealType),
                child: Text(
                  '+ 추가하기',
                  style: AppTypography.body2.copyWith(color: AppColors.primary),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyMealSection extends StatelessWidget {
  final String mealType;

  const _EmptyMealSection({required this.mealType});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '아직 기록이 없습니다.',
          style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.xs),
        TextButton(
          onPressed: () => _openDietAddScreen(context, mealType),
          child: Text(
            '[+ 기록하기]',
            style: AppTypography.body2.copyWith(color: AppColors.primary),
          ),
        ),
      ],
    );
  }
}

class _DietLogCard extends StatelessWidget {
  final Map<String, dynamic> log;
  final Future<bool> Function(int logId) onDelete;

  const _DietLogCard({required this.log, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final int logId = _toInt(log['id']);
    final List<Map<String, dynamic>> items = _readLogItems(log);
    final String foodsLabel = items
        .map(
          (Map<String, dynamic> item) => item['food_name']?.toString() ?? '음식',
        )
        .join(', ');

    final double calories = items.fold<double>(
      0,
      (double total, Map<String, dynamic> item) =>
          total + _toDouble(item['calories']),
    );
    final double protein = items.fold<double>(
      0,
      (double total, Map<String, dynamic> item) =>
          total + _toDouble(item['protein_g']),
    );
    final double carbs = items.fold<double>(
      0,
      (double total, Map<String, dynamic> item) =>
          total + _toDouble(item['carbs_g']),
    );
    final double fat = items.fold<double>(
      0,
      (double total, Map<String, dynamic> item) =>
          total + _toDouble(item['fat_g']),
    );
    final double? sugar = _sumOptionalNutrition(items, 'sugar_g');
    final double? saturatedFat = _sumOptionalNutrition(
      items,
      'saturated_fat_g',
    );
    final double? unsaturatedFat = _sumOptionalNutrition(
      items,
      'unsaturated_fat_g',
    );
    final List<String> optionalNutrients = <String>[
      if (sugar != null) '당 ${_formatNumber(sugar)}g',
      if (saturatedFat != null) '포화 ${_formatNumber(saturatedFat)}g',
      if (unsaturatedFat != null) '불포화 ${_formatNumber(unsaturatedFat)}g',
    ];

    return Dismissible(
      key: ValueKey<String>('diet-log-$logId'),
      direction: DismissDirection.endToStart,
      background: Container(
        decoration: BoxDecoration(
          color: AppColors.error,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        child: const Icon(Icons.delete, color: AppColors.textPrimary),
      ),
      confirmDismiss: (DismissDirection _) => onDelete(logId),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: AppColors.divider),
        ),
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              foodsLabel.isEmpty ? '음식' : foodsLabel,
              style: AppTypography.body1.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              '${_formatNumber(calories)} kcal',
              style: AppTypography.body2.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                Text(
                  '단 ${_formatNumber(protein)}g',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.protein,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '탄 ${_formatNumber(carbs)}g',
                  style: AppTypography.caption.copyWith(color: AppColors.carbs),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '지 ${_formatNumber(fat)}g',
                  style: AppTypography.caption.copyWith(color: AppColors.fat),
                ),
              ],
            ),
            if (optionalNutrients.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.xs,
                children: [
                  for (final String label in optionalNutrients)
                    Text(
                      label,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  List<Map<String, dynamic>> _readLogItems(Map<String, dynamic> rawLog) {
    final List<dynamic> rawItems =
        rawLog['items'] as List<dynamic>? ?? <dynamic>[];
    return rawItems.whereType<Map<String, dynamic>>().toList();
  }
}

class _DailySummaryCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _DailySummaryCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> dailyTotal =
        data['daily_total'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final Map<String, dynamic>? targetRemaining =
        data['target_remaining'] as Map<String, dynamic>?;

    final double calories = _toDouble(dailyTotal['calories']);
    final double protein = _toDouble(dailyTotal['protein_g']);
    final double carbs = _toDouble(dailyTotal['carbs_g']);
    final double fat = _toDouble(dailyTotal['fat_g']);

    final double progress = _calorieProgress(
      consumedCalories: calories,
      remainingCalories:
          targetRemaining == null
              ? null
              : _toDouble(targetRemaining['calories']),
    );

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('일일 합계', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '칼로리 ${_formatNumber(calories)} kcal',
              style: AppTypography.body1,
            ),
            const SizedBox(height: AppSpacing.xs),
            ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.full),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 8,
                valueColor: const AlwaysStoppedAnimation<Color>(
                  AppColors.primary,
                ),
                backgroundColor: AppColors.surfaceLight,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                _MacroSummary(
                  label: '단백질',
                  value: protein,
                  color: AppColors.protein,
                ),
                const SizedBox(width: AppSpacing.md),
                _MacroSummary(
                  label: '탄수화물',
                  value: carbs,
                  color: AppColors.carbs,
                ),
                const SizedBox(width: AppSpacing.md),
                _MacroSummary(label: '지방', value: fat, color: AppColors.fat),
              ],
            ),
            if (targetRemaining != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                '남은 칼로리 ${_formatNumber(_toDouble(targetRemaining['calories']))} kcal',
                style: AppTypography.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  double _calorieProgress({
    required double consumedCalories,
    required double? remainingCalories,
  }) {
    if (remainingCalories == null) {
      return 0;
    }
    final double targetCalories = consumedCalories + remainingCalories;
    if (targetCalories <= 0) {
      return 0;
    }
    return (consumedCalories / targetCalories).clamp(0, 1);
  }
}

class _MacroSummary extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _MacroSummary({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Text(
      '$label ${_formatNumber(value)}g',
      style: AppTypography.caption.copyWith(color: color),
    );
  }
}

class _BottomActionButtons extends StatelessWidget {
  const _BottomActionButtons();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 44,
            child: OutlinedButton(
              onPressed: () => context.push('/diet/analyze'),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.divider),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
              child: Text(
                '📷 분석',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: SizedBox(
            height: 44,
            child: DecoratedBox(
              decoration: primaryButtonDecoration,
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  onTap: () => context.push('/diet/recommend'),
                  child: Center(
                    child: Text(
                      '🤖 AI 추천',
                      style: AppTypography.body2.copyWith(
                        color: AppColors.background,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _DietLoadingView extends StatelessWidget {
  const _DietLoadingView();

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.surface,
      highlightColor: AppColors.surfaceLight,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: List<Widget>.generate(
            6,
            (int index) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Container(
                height: index < 4 ? 136 : 88,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DietErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _DietErrorView({required this.message, required this.onRetry});

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
              onPressed: onRetry,
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

Future<void> _openDietAddScreen(BuildContext context, String mealType) async {
  final bool? created = await context.push<bool>(
    '/diet/add?meal_type=$mealType',
  );
  if (!context.mounted || created != true) {
    return;
  }
  ScaffoldMessenger.of(
    context,
  ).showSnackBar(const SnackBar(content: Text('식단이 추가되었습니다')));
}

String _mealLabel(String mealType) {
  switch (mealType) {
    case 'breakfast':
      return '아침';
    case 'lunch':
      return '점심';
    case 'dinner':
      return '저녁';
    case 'snack':
      return '간식';
    default:
      return mealType;
  }
}

double _logCalories(Map<String, dynamic> log) {
  final List<dynamic> rawItems = log['items'] as List<dynamic>? ?? <dynamic>[];
  return rawItems.fold<double>(0, (double total, dynamic item) {
    if (item is! Map<String, dynamic>) {
      return total;
    }
    return total + _toDouble(item['calories']);
  });
}

double? _sumOptionalNutrition(
  List<Map<String, dynamic>> items,
  String fieldName,
) {
  bool hasValue = false;
  double total = 0;
  for (final Map<String, dynamic> item in items) {
    if (item[fieldName] == null) {
      continue;
    }
    hasValue = true;
    total += _toDouble(item[fieldName]);
  }
  return hasValue ? total : null;
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

int _toInt(dynamic value) {
  if (value is int) {
    return value;
  }
  return int.tryParse(value.toString()) ?? 0;
}

String _formatNumber(double value) {
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toStringAsFixed(1);
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return error.toString();
}
