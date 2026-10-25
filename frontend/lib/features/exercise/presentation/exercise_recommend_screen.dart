import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
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
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = _extractErrorMessage(error);
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

    final List<Map<String, dynamic>> suggestedExercises =
        _readSuggestedExercises(_recommendationData);
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

    try {
      for (final Map<String, dynamic> exercise in suggestedExercises) {
        final Map<String, dynamic>? payload = _buildCreatePayload(
          exercise: exercise,
          dateText: dateText,
        );
        if (payload == null) {
          failCount += 1;
          continue;
        }

        try {
          await ref.read(exerciseRepositoryProvider).createExerciseLog(payload);
          successCount += 1;
        } catch (_) {
          failCount += 1;
        }
      }

      if (!mounted) {
        return;
      }
      if (successCount > 0) {
        ref.invalidate(exerciseLogsProvider);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('기록 완료 · 성공 $successCount개 · 실패 $failCount개')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSavingAll = false;
        });
      }
    }
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

    return <String, dynamic>{
      'exercise_date': dateText,
      'exercise_name': exerciseName,
      'muscle_group': muscleGroup,
      'memo': null,
      'sets': List<Map<String, dynamic>>.generate(sets, (int index) {
        return <String, dynamic>{
          'set_number': index + 1,
          'reps': reps,
          'weight_kg': weightKg,
          'is_completed': true,
        };
      }),
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 8, 20, 8),
              child: NeoTopBar(title: 'AI 운동 추천', showBack: true),
            ),
            Expanded(
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
          ],
        ),
      ),
    );
  }

  Widget _buildSuccessBody() {
    final Map<String, dynamic> data =
        _recommendationData ?? <String, dynamic>{};
    final String recommendation =
        data['recommendation']?.toString().trim() ?? '';
    final List<Map<String, dynamic>> exercises = _readSuggestedExercises(data);
    final List<String> sources = _readVerifiedSources(data);

    return Column(
      children: [
        Expanded(
          child: RefreshIndicator(
            color: AppColors.primary,
            backgroundColor: AppColors.surfaceLow,
            onRefresh: _loadRecommendation,
            child: SingleChildScrollView(
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '추천 범위',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  _MuscleFilterRow(
                    selectedMuscleGroup: _selectedMuscleGroup,
                    onSelected: _onSelectMuscleGroup,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  _AIMessageCard(
                    message:
                        recommendation.isEmpty
                            ? '추천 요약을 표시할 수 없습니다.'
                            : recommendation,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  NeoSectionHeader(title: '추천 운동 ${exercises.length}개'),
                  const SizedBox(height: AppSpacing.xs),
                  if (exercises.isEmpty)
                    const NeoStateCard(
                      icon: Icons.fitness_center,
                      title: '추천 운동이 없습니다',
                      message: '다른 근육군을 선택하거나 추천을 다시 요청해 보세요.',
                    )
                  else
                    for (final Map<String, dynamic> exercise in exercises) ...[
                      _SuggestedExerciseCard(exercise: exercise),
                      const SizedBox(height: AppSpacing.md),
                    ],
                  _SourcesView(sources: sources),
                ],
              ),
            ),
          ),
        ),
        if (exercises.isNotEmpty)
          DecoratedBox(
            decoration: BoxDecoration(
              color: AppColors.background,
              border: Border(
                top: BorderSide(
                  color: AppColors.divider.withValues(alpha: 0.7),
                ),
              ),
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
                child: NeoPrimaryButton(
                  label:
                      _isSavingAll ? '기록 중...' : '추천 ${exercises.length}개 기록하기',
                  icon: _isSavingAll ? null : Icons.playlist_add_check,
                  onPressed: _isSavingAll ? null : _saveAllSuggestedExercises,
                ),
              ),
            ),
          ),
      ],
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
    return InkWell(
      borderRadius: BorderRadius.circular(AppRadius.full),
      onTap: onTap,
      child: NeoInfoChip(
        label: label,
        filled: selected,
        color: selected ? AppColors.primary : AppColors.textSecondary,
      ),
    );
  }
}

class _AIMessageCard extends StatelessWidget {
  final String message;

  const _AIMessageCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      highlighted: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: const Icon(
                  Icons.psychology_alt_outlined,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(child: Text('AI 코치 분석', style: AppTypography.h3)),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(message, style: AppTypography.body1),
        ],
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
        exercise['exercise_name']?.toString().trim().isNotEmpty == true
            ? exercise['exercise_name'].toString().trim()
            : '추천 운동';
    final String muscleGroup = exercise['muscle_group']?.toString() ?? '';
    final String muscleLabel = kMuscleGroupLabels[muscleGroup] ?? muscleGroup;
    final int sets = _toInt(exercise['sets']);
    final int reps = _toInt(exercise['reps']);
    final double? weightKg = _toDoubleOrNull(exercise['weight_kg']);
    final String reason = exercise['reason']?.toString().trim() ?? '';
    final String? assetPath = _recommendationAsset(exerciseName);

    return NeoGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (assetPath != null)
                NeoAssetImage(path: assetPath, width: 68, height: 68)
              else
                Container(
                  width: 68,
                  height: 68,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.glassBorder),
                  ),
                  child: const Icon(
                    Icons.fitness_center,
                    color: AppColors.primary,
                  ),
                ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(exerciseName, style: AppTypography.h3),
                    const SizedBox(height: AppSpacing.sm),
                    if (muscleLabel.isNotEmpty)
                      NeoInfoChip(
                        label: muscleLabel,
                        color: AppColors.secondary,
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              NeoInfoChip(label: '$sets세트', color: AppColors.primary),
              NeoInfoChip(label: '$reps회', color: AppColors.primary),
              NeoInfoChip(
                label:
                    weightKg == null
                        ? '중량 미지정'
                        : '${_formatNumber(weightKg)}kg',
                color: AppColors.primary,
              ),
            ],
          ),
          if (reason.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.lightbulb_outline,
                  color: AppColors.secondary,
                  size: 18,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    reason,
                    style: AppTypography.body2.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          NeoOutlineButton(
            label: '이 운동 기록하기',
            icon: Icons.add,
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
          ),
        ],
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
      children: [
        Text('검증된 출처', style: AppTypography.h3),
        const SizedBox(height: AppSpacing.sm),
        if (sources.isEmpty)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.info_outline,
                color: AppColors.warning,
                size: 18,
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  '표시할 수 있는 출처 정보가 없습니다.',
                  style: AppTypography.body2.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          )
        else
          for (final String source in sources) ...[
            _VerifiedSourceChip(source: source),
            const SizedBox(height: AppSpacing.sm),
          ],
      ],
    );
  }
}

class _VerifiedSourceChip extends StatelessWidget {
  final String source;

  const _VerifiedSourceChip({required this.source});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.secondarySoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.secondary.withValues(alpha: 0.42)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.verified_outlined,
            color: AppColors.secondary,
            size: 18,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              source,
              style: AppTypography.caption.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
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
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: Column(
          children: [
            _skeleton(height: 44),
            const SizedBox(height: AppSpacing.lg),
            _skeleton(height: 148),
            const SizedBox(height: AppSpacing.md),
            _skeleton(height: 220),
            const SizedBox(height: AppSpacing.md),
            _skeleton(height: 220),
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
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: NeoStateCard(
        icon: Icons.psychology_alt_outlined,
        title: '추천을 불러오지 못했습니다',
        message: _cleanRecommendationError(message),
        actionLabel: '다시 시도',
        onAction: onRetry,
      ),
    );
  }
}

List<Map<String, dynamic>> _readSuggestedExercises(Map<String, dynamic>? data) {
  final List<dynamic> raw =
      data?['suggested_exercises'] as List<dynamic>? ?? <dynamic>[];
  return raw.whereType<Map<String, dynamic>>().toList();
}

List<String> _readVerifiedSources(Map<String, dynamic> data) {
  final Set<String> sources = <String>{};
  for (final dynamic value
      in data['sources'] as List<dynamic>? ?? <dynamic>[]) {
    final String source = value.toString().trim();
    if (source.isNotEmpty) {
      sources.add(source);
    }
  }
  return sources.toList();
}

String? _recommendationAsset(String exerciseName) {
  final String normalized = exerciseName.toLowerCase();
  if (normalized.contains('스쿼트') || normalized.contains('squat')) {
    return 'assets/stitch/workout_squat.jpg';
  }
  if (normalized.contains('레그 익스텐션') || normalized.contains('leg extension')) {
    return 'assets/stitch/workout_leg_extension.jpg';
  }
  if (normalized.contains('로우') || normalized.contains('row')) {
    return 'assets/stitch/workout_row.jpg';
  }
  return null;
}

String _extractErrorMessage(Object error) {
  if (error is ExerciseRepositoryException) {
    return error.message;
  }
  return '운동 추천을 처리하는 중 오류가 발생했습니다.';
}

String _cleanRecommendationError(String message) {
  final String normalized =
      message.replaceAll(r'\n', ' ').replaceAll('"', '').trim();
  if (normalized.contains('recommendation')) {
    return 'AI 응답 형식이 맞지 않아 추천을 표시하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  }
  return normalized.isEmpty ? '요청 처리 중 오류가 발생했습니다.' : normalized;
}

int _toInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}

double? _toDoubleOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

String _formatNumber(double value) {
  if (value == value.roundToDouble()) {
    return value.toStringAsFixed(0);
  }
  return value.toStringAsFixed(1);
}
