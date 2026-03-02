import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/exercise_repository.dart';
import '../domain/exercise_controller.dart';

const Map<String, String> kMuscleGroupLabels = <String, String>{
  'chest': '가슴',
  'back': '등',
  'shoulder': '어깨',
  'legs': '하체',
  'arms': '팔',
  'core': '코어',
  'cardio': '유산소',
  'full_body': '전신',
};

const List<String> kMuscleGroupOrder = <String>[
  'chest',
  'back',
  'shoulder',
  'legs',
  'arms',
  'core',
  'cardio',
  'full_body',
];

class ExerciseScreen extends ConsumerWidget {
  const ExerciseScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final DateTime selectedDate = ref.watch(exerciseDateProvider);
    final String? selectedMuscleGroup = ref.watch(selectedMuscleGroupProvider);
    final AsyncValue<Map<String, dynamic>> exerciseLogsAsync = ref.watch(
      exerciseLogsProvider,
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('운동 기록'),
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
      body: exerciseLogsAsync.when(
        loading: () => const _ExerciseLoadingView(),
        error:
            (Object error, StackTrace _) => _ExerciseErrorView(
              message: _extractErrorMessage(error),
              onRetry: () => ref.invalidate(exerciseLogsProvider),
            ),
        data: (Map<String, dynamic> data) {
          final List<Map<String, dynamic>> allExercises = _readExercises(data);
          final List<Map<String, dynamic>> filteredExercises = _filterExercises(
            allExercises,
            selectedMuscleGroup,
          );

          return RefreshIndicator(
            color: AppColors.primary,
            onRefresh: () async {
              ref.invalidate(exerciseLogsProvider);
              await Future<void>.delayed(const Duration(milliseconds: 300));
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _MuscleGroupFilter(
                    selectedMuscleGroup: selectedMuscleGroup,
                    onSelected: (String? muscleGroup) {
                      ref.read(selectedMuscleGroupProvider.notifier).state =
                          muscleGroup;
                    },
                  ),
                  const SizedBox(height: AppSpacing.md),
                  if (filteredExercises.isEmpty)
                    _EmptyExerciseSection(
                      onAdd: () => _openExerciseAddScreen(context),
                    )
                  else
                    Column(
                      children: [
                        for (final Map<String, dynamic> exercise
                            in filteredExercises) ...[
                          _ExerciseCard(
                            exercise: exercise,
                            onDelete:
                                (int logId) =>
                                    _deleteExerciseLog(context, ref, logId),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                        ],
                      ],
                    ),
                  const SizedBox(height: AppSpacing.md),
                  _BottomActionButtons(
                    onAdd: () => _openExerciseAddScreen(context),
                  ),
                  const SizedBox(height: AppSpacing.xl),
                ],
              ),
            ),
          );
        },
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
    ref.read(exerciseDateProvider.notifier).state = pickedDate;
  }

  Future<bool> _deleteExerciseLog(
    BuildContext context,
    WidgetRef ref,
    int logId,
  ) async {
    try {
      await deleteExerciseLogAndRefresh(ref, logId);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('운동 기록을 삭제했습니다.')));
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
}

class _MuscleGroupFilter extends StatelessWidget {
  final String? selectedMuscleGroup;
  final ValueChanged<String?> onSelected;

  const _MuscleGroupFilter({
    required this.selectedMuscleGroup,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _MuscleChip(
            label: '전체',
            selected: selectedMuscleGroup == null,
            onTap: () => onSelected(null),
          ),
          const SizedBox(width: AppSpacing.xs),
          for (final String muscleGroup in kMuscleGroupOrder) ...[
            _MuscleChip(
              label: kMuscleGroupLabels[muscleGroup] ?? muscleGroup,
              selected: selectedMuscleGroup == muscleGroup,
              onTap: () => onSelected(muscleGroup),
            ),
            const SizedBox(width: AppSpacing.xs),
          ],
        ],
      ),
    );
  }
}

class _MuscleChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _MuscleChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      selectedColor: AppColors.primary,
      backgroundColor: AppColors.surface,
      side: BorderSide(color: selected ? AppColors.primary : AppColors.divider),
      labelStyle: AppTypography.caption.copyWith(
        color: selected ? AppColors.background : AppColors.textSecondary,
        fontWeight: FontWeight.w700,
      ),
      onSelected: (_) => onTap(),
    );
  }
}

class _ExerciseCard extends StatelessWidget {
  final Map<String, dynamic> exercise;
  final Future<bool> Function(int logId) onDelete;

  const _ExerciseCard({required this.exercise, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final int logId = _toInt(exercise['id']);
    final String exerciseName = exercise['exercise_name']?.toString() ?? '운동';
    final String muscleGroup = exercise['muscle_group']?.toString() ?? '';
    final String muscleLabel = kMuscleGroupLabels[muscleGroup] ?? muscleGroup;
    final String memo = exercise['memo']?.toString().trim() ?? '';
    final List<Map<String, dynamic>> sets = _readSets(exercise);

    final int setCount = sets.length;
    final int avgReps = _calculateAverageReps(sets);
    final double? maxWeight = _maxWeight(sets);
    final String summary =
        maxWeight == null
            ? '$setCount세트 · $avgReps회 · 맨몸'
            : '$setCount세트 · $avgReps회 · ${_formatNumber(maxWeight)}kg';

    return Dismissible(
      key: ValueKey<String>('exercise-log-$logId'),
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
      child: DecoratedBox(
        decoration: cardDecoration,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      exerciseName,
                      style: AppTypography.body1.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.primarySoft,
                      borderRadius: BorderRadius.circular(AppRadius.full),
                    ),
                    child: Text(
                      muscleLabel,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                summary,
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              if (memo.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  memo,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyExerciseSection extends StatelessWidget {
  final VoidCallback onAdd;

  const _EmptyExerciseSection({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: [
            Text(
              '오늘 운동 기록이 없습니다',
              style: AppTypography.body1,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.sm),
            TextButton(
              onPressed: onAdd,
              child: Text(
                '운동 추가하기',
                style: AppTypography.body2.copyWith(color: AppColors.primary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BottomActionButtons extends StatelessWidget {
  final VoidCallback onAdd;

  const _BottomActionButtons({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 44,
            child: OutlinedButton(
              onPressed: onAdd,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.divider),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
              child: Text(
                '+ 추가',
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
                  onTap: () => context.push('/exercise/recommend'),
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

class _ExerciseLoadingView extends StatelessWidget {
  const _ExerciseLoadingView();

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
                height: index == 0 ? 56 : 92,
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

class _ExerciseErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ExerciseErrorView({required this.message, required this.onRetry});

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

Future<void> _openExerciseAddScreen(BuildContext context) async {
  final bool? created = await context.push<bool>('/exercise/add');
  if (!context.mounted || created != true) {
    return;
  }
  ScaffoldMessenger.of(
    context,
  ).showSnackBar(const SnackBar(content: Text('운동이 추가되었습니다')));
}

List<Map<String, dynamic>> _readExercises(Map<String, dynamic> data) {
  final List<dynamic> rawExercises =
      data['exercises'] as List<dynamic>? ?? <dynamic>[];
  return rawExercises.whereType<Map<String, dynamic>>().toList();
}

List<Map<String, dynamic>> _filterExercises(
  List<Map<String, dynamic>> exercises,
  String? selectedMuscleGroup,
) {
  if (selectedMuscleGroup == null) {
    return exercises;
  }
  return exercises.where((Map<String, dynamic> exercise) {
    return exercise['muscle_group']?.toString() == selectedMuscleGroup;
  }).toList();
}

List<Map<String, dynamic>> _readSets(Map<String, dynamic> exercise) {
  final List<dynamic> rawSets =
      exercise['sets'] as List<dynamic>? ?? <dynamic>[];
  return rawSets.whereType<Map<String, dynamic>>().toList();
}

int _calculateAverageReps(List<Map<String, dynamic>> sets) {
  if (sets.isEmpty) {
    return 0;
  }
  final int totalReps = sets.fold<int>(0, (
    int sum,
    Map<String, dynamic> setData,
  ) {
    return sum + _toInt(setData['reps']);
  });
  return (totalReps / sets.length).round();
}

double? _maxWeight(List<Map<String, dynamic>> sets) {
  final List<double> weights =
      sets
          .map(
            (Map<String, dynamic> setData) =>
                _toDoubleOrNull(setData['weight_kg']),
          )
          .whereType<double>()
          .toList();
  if (weights.isEmpty) {
    return null;
  }
  weights.sort();
  return weights.last;
}

int _toInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double? _toDoubleOrNull(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

String _formatNumber(double value) {
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toStringAsFixed(1);
}

String _extractErrorMessage(Object error) {
  if (error is ExerciseRepositoryException) {
    return error.message;
  }
  return error.toString();
}
