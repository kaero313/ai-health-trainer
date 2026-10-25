import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
import '../data/diet_repository.dart';
import '../domain/diet_controller.dart';

class DietRecommendScreen extends ConsumerStatefulWidget {
  const DietRecommendScreen({super.key});

  @override
  ConsumerState<DietRecommendScreen> createState() =>
      _DietRecommendScreenState();
}

class _DietRecommendScreenState extends ConsumerState<DietRecommendScreen> {
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _errorMessage;
  String? _actionErrorMessage;
  Map<String, dynamic>? _recommendationData;
  final Set<int> _addingIndexes = <int>{};
  final Set<int> _addedIndexes = <int>{};

  @override
  void initState() {
    super.initState();
    _loadRecommendation();
  }

  Future<void> _loadRecommendation({bool refresh = false}) async {
    setState(() {
      if (refresh) {
        _isRefreshing = true;
      } else {
        _isLoading = true;
      }
      _errorMessage = null;
      _actionErrorMessage = null;
      _addingIndexes.clear();
      _addedIndexes.clear();
    });

    final String todayText = DateFormat('yyyy-MM-dd').format(DateTime.now());
    try {
      final Map<String, dynamic> data = await ref
          .read(dietRepositoryProvider)
          .getRecommendation(date: todayText);

      if (!mounted) {
        return;
      }
      setState(() {
        _recommendationData = data;
        _isLoading = false;
        _isRefreshing = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = _extractErrorMessage(e);
        _isLoading = false;
        _isRefreshing = false;
      });
    }
  }

  Future<void> _addSuggestedFood(Map<String, dynamic> food, int index) async {
    if (_addingIndexes.contains(index) || _addedIndexes.contains(index)) {
      return;
    }

    setState(() {
      _addingIndexes.add(index);
      _actionErrorMessage = null;
    });

    final String todayText = DateFormat('yyyy-MM-dd').format(DateTime.now());
    final Map<String, dynamic> payload = <String, dynamic>{
      'log_date': todayText,
      'meal_type': 'snack',
      'items': <Map<String, dynamic>>[
        <String, dynamic>{
          'food_name': food['food_name']?.toString() ?? '추천 음식',
          'serving_size': _nullableString(food['serving_size']),
          'calories': _toDouble(food['calories']),
          'protein_g': _toDouble(food['protein_g']),
          'carbs_g': _toDouble(food['carbs_g']),
          'fat_g': _toDouble(food['fat_g']),
        },
      ],
    };

    try {
      await ref.read(dietRepositoryProvider).createDietLog(payload);
      ref.invalidate(dietLogsProvider);

      if (!mounted) {
        return;
      }
      setState(() {
        _addedIndexes.add(index);
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      final String message = _extractErrorMessage(e);
      setState(() {
        _actionErrorMessage = message;
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } finally {
      if (mounted) {
        setState(() {
          _addingIndexes.remove(index);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: NeoTopBar(title: 'AI 식단 추천', showBack: true),
            ),
            Expanded(
              child:
                  _isLoading
                      ? const _RecommendationLoadingView()
                      : _errorMessage != null
                      ? _RecommendationErrorView(
                        message: _errorMessage!,
                        onRetry: () => _loadRecommendation(refresh: true),
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
    final Map<String, dynamic> remaining =
        data['remaining_nutrients'] as Map<String, dynamic>? ??
        <String, dynamic>{};
    final String recommendation = data['recommendation']?.toString() ?? '';
    final List<Map<String, dynamic>> suggestedFoods =
        (data['suggested_foods'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    final List<String> sources =
        (data['sources'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic e) => e.toString())
            .where((String s) => s.isNotEmpty)
            .toList();

    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: () => _loadRecommendation(refresh: true),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _AICoachMessageCard(
              message:
                  recommendation.isEmpty ? '추천 메시지가 없습니다.' : recommendation,
            ),
            const SizedBox(height: AppSpacing.md),
            _RemainingNutrientsCard(remaining: remaining),
            const SizedBox(height: AppSpacing.md),
            const NeoSectionHeader(title: '추천 음식'),
            const SizedBox(height: AppSpacing.sm),
            if (suggestedFoods.isEmpty)
              const NeoStateCard(
                icon: Icons.no_food_outlined,
                title: '추천 음식이 없습니다',
                message: '현재 남은 영양소 기준으로 추가할 음식이 없습니다.',
              )
            else
              Column(
                children: List<Widget>.generate(suggestedFoods.length, (
                  int index,
                ) {
                  final Map<String, dynamic> food = suggestedFoods[index];
                  return Padding(
                    padding: EdgeInsets.only(
                      bottom:
                          index == suggestedFoods.length - 1
                              ? 0
                              : AppSpacing.sm,
                    ),
                    child: _SuggestedFoodCard(
                      food: food,
                      isAdded: _addedIndexes.contains(index),
                      isSaving: _addingIndexes.contains(index),
                      onAdd: () => _addSuggestedFood(food, index),
                    ),
                  );
                }),
              ),
            if (_actionErrorMessage != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                _actionErrorMessage!,
                style: AppTypography.caption.copyWith(color: AppColors.error),
              ),
            ],
            if (_isRefreshing) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                '추천을 새로고침하는 중...',
                style: AppTypography.caption.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            if (sources.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.lg),
              _SourcesView(sources: sources),
            ],
            const SizedBox(height: AppSpacing.lg),
          ],
        ),
      ),
    );
  }
}

class _AICoachMessageCard extends StatelessWidget {
  final String message;

  const _AICoachMessageCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      highlighted: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.primary),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'AI 코치 분석',
                style: AppTypography.h3.copyWith(color: AppColors.primary),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(message, style: AppTypography.body1),
        ],
      ),
    );
  }
}

class _RemainingNutrientsCard extends StatelessWidget {
  final Map<String, dynamic> remaining;

  const _RemainingNutrientsCard({required this.remaining});

  @override
  Widget build(BuildContext context) {
    final double calories = _toDouble(remaining['calories']);
    final double protein = _toDouble(remaining['protein_g']);
    final double carbs = _toDouble(remaining['carbs_g']);
    final double fat = _toDouble(remaining['fat_g']);

    return NeoGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('남은 영양소', style: AppTypography.h3),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '${_formatNumber(calories)} kcal',
            style: AppTypography.numberSmall.copyWith(
              color: AppColors.calories,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.xs,
            children: [
              _MacroText(
                label: '단백질',
                value: protein,
                color: AppColors.protein,
              ),
              _MacroText(label: '탄수화물', value: carbs, color: AppColors.carbs),
              _MacroText(label: '지방', value: fat, color: AppColors.fat),
            ],
          ),
        ],
      ),
    );
  }
}

class _MacroText extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _MacroText({
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

class _SuggestedFoodCard extends StatelessWidget {
  final Map<String, dynamic> food;
  final bool isAdded;
  final bool isSaving;
  final VoidCallback onAdd;

  const _SuggestedFoodCard({
    required this.food,
    required this.isAdded,
    required this.isSaving,
    required this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    final String foodName = food['food_name']?.toString() ?? '추천 음식';
    final String servingSize = _nullableString(food['serving_size']) ?? '1회분';
    final double calories = _toDouble(food['calories']);
    final double protein = _toDouble(food['protein_g']);
    final double carbs = _toDouble(food['carbs_g']);
    final double fat = _toDouble(food['fat_g']);
    final String reason = _nullableString(food['reason']) ?? '추천 이유가 없습니다.';

    return NeoGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(foodName, style: AppTypography.h3),
          const SizedBox(height: AppSpacing.xs),
          Text(
            servingSize,
            style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              NeoInfoChip(
                label: '${_formatNumber(calories)} kcal',
                color: AppColors.primary,
              ),
              NeoInfoChip(
                label: 'P ${_formatNumber(protein)}g',
                color: AppColors.textSecondary,
              ),
              NeoInfoChip(
                label: 'C ${_formatNumber(carbs)}g',
                color: AppColors.secondary,
              ),
              NeoInfoChip(
                label: 'F ${_formatNumber(fat)}g',
                color: AppColors.tertiary,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            reason,
            style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.md),
          NeoOutlineButton(
            label:
                isSaving
                    ? '추가 중...'
                    : isAdded
                    ? '간식으로 추가됨'
                    : '간식으로 추가',
            icon: isAdded ? Icons.check : Icons.add,
            onPressed: (isAdded || isSaving) ? null : onAdd,
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
        Row(
          children: [
            const Icon(
              Icons.verified_outlined,
              color: AppColors.primary,
              size: 18,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text('검증된 출처', style: AppTypography.h3),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children:
              sources
                  .map(
                    (String source) =>
                        NeoInfoChip(label: source, color: AppColors.primary),
                  )
                  .toList(),
        ),
      ],
    );
  }
}

class _RecommendationLoadingView extends StatelessWidget {
  const _RecommendationLoadingView();

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.surface,
      highlightColor: AppColors.surfaceLight,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: [
            _skeletonCard(height: 132),
            const SizedBox(height: AppSpacing.md),
            _skeletonCard(height: 112),
            const SizedBox(height: AppSpacing.md),
            _skeletonCard(height: 148),
            const SizedBox(height: AppSpacing.sm),
            _skeletonCard(height: 148),
            const SizedBox(height: AppSpacing.sm),
            _skeletonCard(height: 148),
          ],
        ),
      ),
    );
  }

  Widget _skeletonCard({required double height}) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
    );
  }
}

class _RecommendationErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _RecommendationErrorView({
    required this.message,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Center(
        child: NeoStateCard(
          icon: Icons.psychology_alt_outlined,
          title: '추천을 불러오지 못했습니다',
          message: _cleanRecommendationError(message),
          actionLabel: '다시 시도',
          onAction: onRetry,
        ),
      ),
    );
  }
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return error.toString();
}

String _cleanRecommendationError(String message) {
  final String normalized =
      message.replaceAll(r'\n', ' ').replaceAll('"', '').trim();
  if (normalized.contains('recommendation')) {
    return 'AI 응답 형식이 맞지 않아 추천을 표시하지 못했습니다. 잠시 후 다시 시도해 주세요.';
  }
  return normalized.isEmpty ? '요청 처리 중 오류가 발생했습니다.' : normalized;
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

String? _nullableString(dynamic value) {
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  if (text.isEmpty) {
    return null;
  }
  return text;
}

String _formatNumber(double value) {
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toStringAsFixed(1);
}
