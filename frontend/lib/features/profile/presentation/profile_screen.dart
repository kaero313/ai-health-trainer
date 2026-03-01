import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../auth/domain/auth_state_provider.dart';
import '../data/profile_repository.dart';
import '../domain/profile_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<Map<String, dynamic>> profileAsync = ref.watch(
      profileControllerProvider,
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('프로필'),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: AppSpacing.md),
            child: Icon(Icons.settings, color: AppColors.textSecondary),
          ),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
        error: (Object error, _) {
          if (_isNotFoundError(error)) {
            return _NoProfileView(
              message: '프로필을 설정해주세요.',
              onSetup: () => context.push('/profile/edit'),
            );
          }

          return _ErrorView(
            message: _extractErrorMessage(error),
            onRetry: () => ref.invalidate(profileControllerProvider),
          );
        },
        data: (Map<String, dynamic> data) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _ProfileHeaderCard(
                  displayName: data['email']?.toString() ?? '사용자',
                  email: data['email']?.toString() ?? '사용자',
                ),
                const SizedBox(height: AppSpacing.md),
                _BodyInfoCard(data: data),
                const SizedBox(height: AppSpacing.md),
                _GoalCard(data: data),
                const SizedBox(height: AppSpacing.md),
                _PreferencesCard(data: data),
                const SizedBox(height: AppSpacing.lg),
                OutlinedButton(
                  onPressed: () => context.push('/profile/edit'),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.divider),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                  ),
                  child: Text(
                    '수정하기',
                    style: AppTypography.body1.copyWith(color: AppColors.textPrimary),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                TextButton(
                  onPressed: () async {
                    await ref.read(authStateProvider.notifier).logout();
                  },
                  child: Text(
                    '로그아웃',
                    style: AppTypography.body2.copyWith(
                      color: AppColors.error,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  bool _isNotFoundError(Object error) {
    return error is ProfileRepositoryException && error.statusCode == 404;
  }

  String _extractErrorMessage(Object error) {
    if (error is ProfileRepositoryException) {
      return error.message;
    }
    return error.toString();
  }
}

class _NoProfileView extends StatelessWidget {
  final String message;
  final VoidCallback onSetup;

  const _NoProfileView({
    required this.message,
    required this.onSetup,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.person_outline, color: AppColors.textSecondary, size: 56),
            const SizedBox(height: AppSpacing.md),
            Text(
              message,
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
                        '설정하기',
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

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorView({
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

class _ProfileHeaderCard extends StatelessWidget {
  final String displayName;
  final String email;

  const _ProfileHeaderCard({
    required this.displayName,
    required this.email,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: AppColors.surfaceLight,
              child: Text(
                displayName.isNotEmpty ? displayName[0].toUpperCase() : 'U',
                style: AppTypography.h3.copyWith(color: AppColors.primary),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    displayName,
                    style: AppTypography.h3,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    email,
                    style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BodyInfoCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _BodyInfoCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: '신체 정보',
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _MetricColumn(label: '키', value: '${_formatNumber(data['height_cm'])}cm'),
          _MetricColumn(label: '몸무게', value: '${_formatNumber(data['weight_kg'])}kg'),
          _MetricColumn(label: '나이', value: '${_formatNumber(data['age'])}세'),
        ],
      ),
    );
  }
}

class _GoalCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _GoalCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final String goal = data['goal']?.toString() ?? 'maintain';
    final String activity = data['activity_level']?.toString() ?? 'moderate';

    return _SectionCard(
      title: '목표',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
              '🎯 ${_goalLabel(goal)}',
              style: AppTypography.body2.copyWith(
                color: AppColors.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '활동 수준: ${_activityLevelLabel(activity)}',
            style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '목표 칼로리: ${_formatNumber(data['target_calories'])} kcal',
            style: AppTypography.body2,
          ),
          Text(
            '단백질: ${_formatNumber(data['target_protein_g'])}g',
            style: AppTypography.body2,
          ),
          Text(
            '탄수화물: ${_formatNumber(data['target_carbs_g'])}g',
            style: AppTypography.body2,
          ),
          Text(
            '지방: ${_formatNumber(data['target_fat_g'])}g',
            style: AppTypography.body2,
          ),
        ],
      ),
    );
  }
}

class _PreferencesCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _PreferencesCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final List<dynamic> allergies = data['allergies'] as List<dynamic>? ?? <dynamic>[];
    final List<dynamic> preferences =
        data['food_preferences'] as List<dynamic>? ?? <dynamic>[];

    return _SectionCard(
      title: '기타 설정',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('알레르기', style: AppTypography.body2.copyWith(color: AppColors.textSecondary)),
          const SizedBox(height: AppSpacing.xs),
          _TagWrap(tags: allergies.map((dynamic e) => e.toString()).toList()),
          const SizedBox(height: AppSpacing.md),
          Text('선호 식품', style: AppTypography.body2.copyWith(color: AppColors.textSecondary)),
          const SizedBox(height: AppSpacing.xs),
          _TagWrap(tags: preferences.map((dynamic e) => e.toString()).toList()),
        ],
      ),
    );
  }
}

class _TagWrap extends StatelessWidget {
  final List<String> tags;

  const _TagWrap({required this.tags});

  @override
  Widget build(BuildContext context) {
    if (tags.isEmpty) {
      return Text(
        '없음',
        style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
      );
    }

    return Wrap(
      spacing: AppSpacing.xs,
      runSpacing: AppSpacing.xs,
      children: tags
          .map(
            (String tag) => Chip(
              backgroundColor: AppColors.surfaceLight,
              side: BorderSide.none,
              label: Text(
                tag,
                style: AppTypography.caption.copyWith(color: AppColors.textPrimary),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _SectionCard({
    required this.title,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: AppTypography.h3),
            const SizedBox(height: AppSpacing.sm),
            child,
          ],
        ),
      ),
    );
  }
}

class _MetricColumn extends StatelessWidget {
  final String label;
  final String value;

  const _MetricColumn({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: AppTypography.numberSmall),
        const SizedBox(height: AppSpacing.xs),
        Text(label, style: AppTypography.caption),
      ],
    );
  }
}

String _formatNumber(dynamic value) {
  if (value == null) {
    return '-';
  }

  if (value is int) {
    return value.toString();
  }

  if (value is double) {
    if (value == value.roundToDouble()) {
      return value.toInt().toString();
    }
    return value.toStringAsFixed(1);
  }

  final String parsed = value.toString();
  final double? asDouble = double.tryParse(parsed);
  if (asDouble == null) {
    return parsed;
  }
  if (asDouble == asDouble.roundToDouble()) {
    return asDouble.toInt().toString();
  }
  return asDouble.toStringAsFixed(1);
}

String _goalLabel(String goal) {
  switch (goal) {
    case 'bulk':
      return '벌크업 (+300kcal)';
    case 'diet':
      return '다이어트 (-500kcal)';
    case 'maintain':
      return '유지';
    default:
      return goal;
  }
}

String _activityLevelLabel(String activity) {
  switch (activity) {
    case 'sedentary':
      return '비활동적';
    case 'light':
      return '가벼운';
    case 'moderate':
      return '보통 (주 3~5)';
    case 'active':
      return '활발 (주 6~7)';
    case 'very_active':
      return '매우 활발';
    default:
      return activity;
  }
}
