import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/exercise_repository.dart';
import '../domain/exercise_controller.dart';
import 'exercise_screen.dart';

class ExerciseRecommendScreen extends ConsumerStatefulWidget {
  const ExerciseRecommendScreen({super.key});

  @override
  ConsumerState<ExerciseRecommendScreen> createState() =>
      _ExerciseRecommendScreenState();
}

class _ExerciseRecommendScreenState
    extends ConsumerState<ExerciseRecommendScreen> {
  bool _isLoading = true;
  bool _isSavingAll = false;
  String? _errorMessage;
  String? _selectedMuscleGroup;
  Map<String, dynamic>? _recommendationData;

  @override
  void initState() {
    super.initState();
    _loadRecommendation();
  }

  Future<void> _loadRecommendation() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final Map<String, dynamic> data = await ref
          .read(exerciseRepositoryProvider)
          .getRecommendation(muscleGroup: _selectedMuscleGroup);

      if (!mounted) {
        return;
      }
      setState(() {
        _recommendationData = data;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = _extractErrorMessage(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _onSelectMuscleGroup(String? muscleGroup) async {
    if (_selectedMuscleGroup == muscleGroup) {
      return;
    }
    setState(() {
      _selectedMuscleGroup = muscleGroup;
    });
    await _loadRecommendation();
  }

  Future<void> _saveAllSuggestedExercises() async {
    if (_isSavingAll) {
      return;
    }

    final Map<String, dynamic> data =
        _recommendationData ?? <String, dynamic>{};
    final List<Map<String, dynamic>> suggestedExercises =
        (data['suggested_exercises'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();

    if (suggestedExercises.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('저장할 추천 운동이 없습니다.')));
      return;
    }

    setState(() {
      _isSavingAll = true;
    });

    final DateTime selectedDate = ref.read(exerciseDateProvider);
    final String dateText = DateFormat('yyyy-MM-dd').format(selectedDate);

    int successCount = 0;
    int failCount = 0;

    for (final Map<String, dynamic> exercise in suggestedExercises) {
      final String exerciseName =
          exercise['exercise_name']?.toString().trim() ?? '알 수 없는 운동';

      try {
        final Map<String, dynamic>? payload = _buildCreatePayload(
          exercise: exercise,
          dateText: dateText,
        );

        if (payload == null) {
          failCount += 1;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('$exerciseName 저장에 필요한 데이터가 부족합니다.')),
            );
          }
          continue;
        }

        await ref.read(exerciseRepositoryProvider).createExerciseLog(payload);
        successCount += 1;
      } catch (e) {
        failCount += 1;
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('$exerciseName 실패: ${_extractErrorMessage(e)}'),
            ),
          );
        }
      }
    }

    if (!mounted) {
      return;
    }

    if (successCount > 0) {
      ref.invalidate(exerciseLogsProvider);
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('저장 완료: 성공 $successCount건, 실패 $failCount건')),
    );

    setState(() {
      _isSavingAll = false;
    });
  }

  Map<String, dynamic>? _buildCreatePayload({
    required Map<String, dynamic> exercise,
    required String dateText,
  }) {
    final String exerciseName =
        exercise['exercise_name']?.toString().trim() ?? '';
    final String muscleGroup =
        exercise['muscle_group']?.toString().trim() ?? '';
    final int sets = _toInt(exercise['sets']);
    final int reps = _toInt(exercise['reps']);
    final double? weightKg = _toDoubleOrNull(exercise['weight_kg']);

    if (exerciseName.isEmpty ||
        !kMuscleGroupOrder.contains(muscleGroup) ||
        sets <= 0 ||
        reps <= 0) {
      return null;
    }

    final List<Map<String, dynamic>> setsPayload =
        List<Map<String, dynamic>>.generate(sets, (int index) {
          return <String, dynamic>{
            'set_number': index + 1,
            'reps': reps,
            'weight_kg': weightKg,
            'is_completed': true,
          };
        });

    return <String, dynamic>{
      'exercise_date': dateText,
      'exercise_name': exerciseName,
      'muscle_group': muscleGroup,
      'memo': null,
      'sets': setsPayload,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('AI 운동 추천')),
      body: SafeArea(
        child:
            _isLoading
                ? const _RecommendLoadingView()
                : _errorMessage != null
                ? _RecommendErrorView(
                  message: _errorMessage!,
                  onRetry: _loadRecommendation,
                )
                : _buildSuccessBody(),
      ),
    );
  }

  Widget _buildSuccessBody() {
    final Map<String, dynamic> data =
        _recommendationData ?? <String, dynamic>{};
    final String recommendation = data['recommendation']?.toString() ?? '';
    final List<Map<String, dynamic>> exercises =
        (data['suggested_exercises'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final List<String> sources =
        (data['sources'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic value) => value.toString())
            .where((String value) => value.isNotEmpty)
            .toList();

    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: _loadRecommendation,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _MuscleFilterRow(
              selectedMuscleGroup: _selectedMuscleGroup,
              onSelected: _onSelectMuscleGroup,
            ),
            const SizedBox(height: AppSpacing.md),
            _AIMessageCard(
              message:
                  recommendation.isEmpty ? '추천 메시지가 없습니다.' : recommendation,
            ),
            const SizedBox(height: AppSpacing.md),
            Text('추천 운동', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.sm),
            if (exercises.isEmpty)
              DecoratedBox(
                decoration: cardDecoration,
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Text(
                    '추천할 운동이 없습니다',
                    style: AppTypography.body2.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              )
            else
              Column(
                children: [
                  for (int i = 0; i < exercises.length; i++) ...[
                    _SuggestedExerciseCard(exercise: exercises[i]),
                    if (i != exercises.length - 1)
                      const SizedBox(height: AppSpacing.sm),
                  ],
                ],
              ),
            const SizedBox(height: AppSpacing.lg),
            if (sources.isNotEmpty) _SourcesView(sources: sources),
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              height: 52,
              child: DecoratedBox(
                decoration: primaryButtonDecoration,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    onTap: _isSavingAll ? null : _saveAllSuggestedExercises,
                    child: Center(
                      child:
                          _isSavingAll
                              ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: AppColors.background,
                                ),
                              )
                              : Text(
                                '전체 추천 기록하기',
                                style: AppTypography.body1.copyWith(
                                  color: AppColors.background,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
        ),
      ),
    );
  }
}

class _MuscleFilterRow extends StatelessWidget {
  final String? selectedMuscleGroup;
  final ValueChanged<String?> onSelected;

  const _MuscleFilterRow({
    required this.selectedMuscleGroup,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _FilterChip(
            label: '전체',
            selected: selectedMuscleGroup == null,
            onTap: () => onSelected(null),
          ),
          const SizedBox(width: AppSpacing.xs),
          for (final String muscleGroup in kMuscleGroupOrder) ...[
            _FilterChip(
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

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip({
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

class _AIMessageCard extends StatelessWidget {
  final String message;

  const _AIMessageCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: glassCardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('🤖', style: TextStyle(fontSize: 24)),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: Text(message, style: AppTypography.body1)),
          ],
        ),
      ),
    );
  }
}

class _SuggestedExerciseCard extends StatelessWidget {
  final Map<String, dynamic> exercise;

  const _SuggestedExerciseCard({required this.exercise});

  @override
  Widget build(BuildContext context) {
    final String exerciseName =
        exercise['exercise_name']?.toString() ?? '추천 운동';
    final String muscleGroup = exercise['muscle_group']?.toString() ?? '';
    final String muscleLabel = kMuscleGroupLabels[muscleGroup] ?? muscleGroup;
    final int sets = _toInt(exercise['sets']);
    final int reps = _toInt(exercise['reps']);
    final double? weightKg = _toDoubleOrNull(exercise['weight_kg']);
    final String reason =
        exercise['reason']?.toString().trim().isNotEmpty == true
            ? exercise['reason'].toString().trim()
            : '추천 이유가 없습니다.';
    final String weightText =
        weightKg == null ? '맨몸' : '${_formatNumber(weightKg)}kg';

    return DecoratedBox(
      decoration: cardDecoration,
      child: Container(
        decoration: const BoxDecoration(
          border: Border(left: BorderSide(color: AppColors.primary, width: 4)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                exerciseName,
                style: AppTypography.body1.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '$sets세트 · $reps회 · $weightText',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
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
              const SizedBox(height: AppSpacing.xs),
              Text(
                '💡 $reason',
                style: AppTypography.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () {
                    context.push(
                      '/exercise/add',
                      extra: <String, dynamic>{
                        'exercise_name': exerciseName,
                        'muscle_group': muscleGroup,
                        'sets': sets,
                        'reps': reps,
                        'weight_kg': weightKg,
                      },
                    );
                  },
                  child: Text(
                    '이 운동 기록하기',
                    style: AppTypography.body2.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SourcesView extends StatelessWidget {
  final List<String> sources;

  const _SourcesView({required this.sources});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children:
          sources.map((String source) {
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Text(
                '📚 $source',
                style: AppTypography.caption.copyWith(color: AppColors.info),
              ),
            );
          }).toList(),
    );
  }
}

class _RecommendLoadingView extends StatelessWidget {
  const _RecommendLoadingView();

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.surface,
      highlightColor: AppColors.surfaceLight,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: [
            _skeleton(height: 56),
            const SizedBox(height: AppSpacing.md),
            _skeleton(height: 132),
            const SizedBox(height: AppSpacing.md),
            _skeleton(height: 156),
            const SizedBox(height: AppSpacing.sm),
            _skeleton(height: 156),
            const SizedBox(height: AppSpacing.sm),
            _skeleton(height: 156),
          ],
        ),
      ),
    );
  }

  Widget _skeleton({required double height}) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
    );
  }
}

class _RecommendErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _RecommendErrorView({required this.message, required this.onRetry});

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

String _extractErrorMessage(Object error) {
  if (error is ExerciseRepositoryException) {
    return error.message;
  }
  return error.toString();
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
