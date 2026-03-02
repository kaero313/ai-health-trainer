import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../profile/data/profile_repository.dart';
import '../../profile/domain/profile_controller.dart';
import '../data/dashboard_repository.dart';
import '../domain/dashboard_controller.dart';
import 'widgets/calorie_ring.dart';
import 'widgets/nutrient_bar.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<Map<String, dynamic>> profileAsync = ref.watch(
      profileControllerProvider,
    );
    final AsyncValue<Map<String, dynamic>> todayAsync = ref.watch(
      todayDashboardProvider,
    );
    final AsyncValue<Map<String, dynamic>> weeklyAsync = ref.watch(
      weeklyDashboardProvider,
    );

    final Object? profileError = profileAsync.asError?.error;
    final Object? todayError = todayAsync.asError?.error;
    final Object? weeklyError = weeklyAsync.asError?.error;

    final bool needsProfileSetup =
        _isProfileNotFound(profileError) ||
        _isDashboardNotFound(todayError) ||
        _isDashboardNotFound(weeklyError);

    final bool isLoading =
        profileAsync.isLoading || todayAsync.isLoading || weeklyAsync.isLoading;

    final Object? firstError = profileError ?? todayError ?? weeklyError;
    final bool hasUnhandledError = !needsProfileSetup && firstError != null;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          'Good Morning, ${_extractDisplayName(profileAsync)}',
          style: AppTypography.h3,
        ),
      ),
      body: Builder(
        builder: (BuildContext context) {
          if (needsProfileSetup) {
            return _ProfileRequiredView(
              onSetup: () => context.push('/profile/edit'),
            );
          }

          if (isLoading) {
            return const _DashboardLoadingView();
          }

          if (hasUnhandledError) {
            return _DashboardErrorView(
              message: _extractErrorMessage(firstError),
              onRetry: () => refreshDashboard(ref),
            );
          }

          final Map<String, dynamic> today = todayAsync.requireValue;
          final Map<String, dynamic> weekly = weeklyAsync.requireValue;

          return RefreshIndicator(
            color: AppColors.primary,
            onRefresh: () async {
              refreshDashboard(ref);
              await Future<void>.delayed(const Duration(milliseconds: 300));
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _TodayNutritionCard(data: today),
                  const SizedBox(height: AppSpacing.md),
                  _TodayExerciseCard(data: today),
                  const SizedBox(height: AppSpacing.md),
                  _WeeklySummaryCard(today: today, weekly: weekly),
                  const SizedBox(height: AppSpacing.md),
                  const _AiCoachingCard(),
                  const SizedBox(height: AppSpacing.xl),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  bool _isProfileNotFound(Object? error) {
    return error is ProfileRepositoryException && error.statusCode == 404;
  }

  bool _isDashboardNotFound(Object? error) {
    return error is DashboardRepositoryException && error.statusCode == 404;
  }

  String _extractDisplayName(AsyncValue<Map<String, dynamic>> profileAsync) {
    if (!profileAsync.hasValue) {
      return '사용자';
    }

    final Map<String, dynamic> data = profileAsync.requireValue;
    final String? email = data['email']?.toString();
    if (email == null || email.isEmpty || !email.contains('@')) {
      return '사용자';
    }
    return email.split('@').first;
  }

  String _extractErrorMessage(Object error) {
    if (error is DashboardRepositoryException) {
      return error.message;
    }
    if (error is ProfileRepositoryException) {
      return error.message;
    }
    return error.toString();
  }
}

class _TodayNutritionCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _TodayNutritionCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> nutrition =
        data['nutrition'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final Map<String, dynamic> consumed =
        nutrition['consumed'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final Map<String, dynamic> target =
        nutrition['target'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final Map<String, dynamic> progressPercent =
        nutrition['progress_percent'] as Map<String, dynamic>? ??
        <String, dynamic>{};

    final int consumedCalories = _toRoundedInt(consumed['calories']);
    final int targetCalories = _toRoundedInt(target['calories']);
    final double caloriesProgressPercent = _toDouble(
      progressPercent['calories'],
    );

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('오늘의 영양', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.md),
            Center(
              child: CalorieRing(
                progress: caloriesProgressPercent / 100,
                consumed: consumedCalories,
                target: targetCalories,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            NutrientBar(
              label: '단백질',
              current: _toDouble(consumed['protein_g']),
              target: _toDouble(target['protein_g']),
              color: AppColors.protein,
              delay: Duration.zero,
            ),
            const SizedBox(height: AppSpacing.sm),
            NutrientBar(
              label: '탄수화물',
              current: _toDouble(consumed['carbs_g']),
              target: _toDouble(target['carbs_g']),
              color: AppColors.carbs,
              delay: const Duration(milliseconds: 50),
            ),
            const SizedBox(height: AppSpacing.sm),
            NutrientBar(
              label: '지방',
              current: _toDouble(consumed['fat_g']),
              target: _toDouble(target['fat_g']),
              color: AppColors.fat,
              delay: const Duration(milliseconds: 100),
            ),
          ],
        ),
      ),
    );
  }
}

class _TodayExerciseCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _TodayExerciseCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> exercise =
        data['exercise'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final List<dynamic> rawGroups =
        exercise['muscle_groups_trained'] as List<dynamic>? ?? <dynamic>[];
    final List<String> groups =
        rawGroups
            .map((dynamic group) => _muscleGroupLabel(group.toString()))
            .toList();

    final int exercisesCount = _toRoundedInt(exercise['exercises_count']);
    final int totalSets = _toRoundedInt(exercise['total_sets']);
    final bool completed = exercise['completed'] == true;

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('오늘의 운동', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.sm),
            Text(
              groups.isEmpty ? '기록 없음' : groups.join(' + '),
              style: AppTypography.body1,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              '$exercisesCount개 운동 · $totalSets세트',
              style: AppTypography.body2.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
              decoration: BoxDecoration(
                color:
                    completed ? AppColors.primarySoft : AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(AppRadius.full),
              ),
              child: Text(
                completed ? '✅ 완료' : '⏳ 미완료',
                style: AppTypography.caption.copyWith(
                  color:
                      completed ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WeeklySummaryCard extends StatelessWidget {
  final Map<String, dynamic> today;
  final Map<String, dynamic> weekly;

  const _WeeklySummaryCard({required this.today, required this.weekly});

  @override
  Widget build(BuildContext context) {
    final DateTime weekStart = _toDateTime(weekly['week_start']);
    final List<dynamic> dailyBreakdown =
        weekly['daily_breakdown'] as List<dynamic>? ?? <dynamic>[];
    final Map<String, bool> exercisedByDate = _toExerciseMap(dailyBreakdown);

    final List<bool> sevenDayExercised = List<bool>.generate(7, (int index) {
      final DateTime day = weekStart.add(Duration(days: index));
      final String key = DateFormat('yyyy-MM-dd').format(day);
      return exercisedByDate[key] ?? false;
    });

    final Map<String, dynamic> streak =
        today['streak'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final int exerciseStreakDays = _toRoundedInt(streak['exercise_days']);

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('이번 주 요약', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.md),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: List<Widget>.generate(7, (int index) {
                return Column(
                  children: [
                    Text(_weekdayLabel(index), style: AppTypography.caption),
                    const SizedBox(height: AppSpacing.xs),
                    Container(
                      width: 14,
                      height: 14,
                      decoration: BoxDecoration(
                        color:
                            sevenDayExercised[index]
                                ? AppColors.primary
                                : AppColors.divider,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                );
              }),
            ),
            const SizedBox(height: AppSpacing.md),
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
                '🔥 $exerciseStreakDays일 연속 기록 중!',
                style: AppTypography.body2.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Map<String, bool> _toExerciseMap(List<dynamic> dailyBreakdown) {
    final Map<String, bool> map = <String, bool>{};
    for (final dynamic item in dailyBreakdown) {
      if (item is! Map<String, dynamic>) {
        continue;
      }
      final DateTime date = _toDateTime(item['date']);
      final String key = DateFormat('yyyy-MM-dd').format(date);
      map[key] = item['exercised'] == true;
    }
    return map;
  }
}

class _AiCoachingCard extends StatelessWidget {
  const _AiCoachingCard();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: glassCardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('🤖'),
                const SizedBox(width: AppSpacing.xs),
                Text('AI 코칭', style: AppTypography.h3),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '식단, 운동에 대한 맞춤 코칭을 받아보세요',
              style: AppTypography.body2.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => context.push('/ai/chat'),
                child: Text(
                  '채팅 시작',
                  style: AppTypography.body2.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileRequiredView extends StatelessWidget {
  final VoidCallback onSetup;

  const _ProfileRequiredView({required this.onSetup});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.person_outline,
              color: AppColors.textSecondary,
              size: 56,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              '프로필을 먼저 설정해주세요',
              style: AppTypography.body1,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              height: 48,
              child: DecoratedBox(
                decoration: primaryButtonDecoration,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    onTap: onSetup,
                    child: Center(
                      child: Text(
                        '프로필 설정',
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
          ],
        ),
      ),
    );
  }
}

class _DashboardLoadingView extends StatelessWidget {
  const _DashboardLoadingView();

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
            4,
            (int index) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Container(
                height: index == 0 ? 360 : 130,
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

class _DashboardErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _DashboardErrorView({required this.message, required this.onRetry});

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

String _weekdayLabel(int index) {
  const List<String> labels = <String>['월', '화', '수', '목', '금', '토', '일'];
  return labels[min(max(index, 0), labels.length - 1)];
}

String _muscleGroupLabel(String group) {
  switch (group) {
    case 'chest':
      return '가슴';
    case 'back':
      return '등';
    case 'shoulder':
      return '어깨';
    case 'legs':
      return '하체';
    case 'arms':
      return '팔';
    case 'core':
      return '코어';
    case 'cardio':
      return '유산소';
    case 'full_body':
      return '전신';
    default:
      return group;
  }
}
