// 홈(대시보드) 화면. provider로 상태와 값을 정하고 그리기는 DashboardView가 한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../profile/data/profile_repository.dart';
import '../../profile/domain/profile_controller.dart';
import '../data/dashboard_repository.dart';
import '../domain/dashboard_controller.dart';
import 'dashboard_view.dart';
import 'dashboard_view_data.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final DateTime now = DateTime.now();
    final AsyncValue<Map<String, dynamic>> profileAsync = ref.watch(
      profileControllerProvider,
    );
    final AsyncValue<Map<String, dynamic>> todayAsync = ref.watch(
      todayDashboardProvider,
    );
    final AsyncValue<Map<String, dynamic>> weeklyAsync = ref.watch(
      weeklyDashboardProvider,
    );
    final AsyncValue<List<Map<String, dynamic>>> weightAsync = ref.watch(
      recentWeightHistoryProvider,
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

    final DashboardStatus status = needsProfileSetup
        ? DashboardStatus.profileRequired
        : isLoading
        ? DashboardStatus.loading
        : firstError != null
        ? DashboardStatus.error
        : DashboardStatus.ready;
    final bool ready = status == DashboardStatus.ready;

    return DashboardView(
      status: status,
      // 목표는 profile을 받았을 때만 부제에 붙인다(§21-2).
      subtitle: dashboardSubtitle(
        now,
        profile: ready ? profileAsync.valueOrNull : null,
      ),
      data: ready
          ? DashboardViewData.fromApi(
              profile: profileAsync.valueOrNull ?? <String, dynamic>{},
              today: todayAsync.valueOrNull ?? <String, dynamic>{},
              weekly: weeklyAsync.valueOrNull ?? <String, dynamic>{},
              weightHistory: weightAsync.valueOrNull,
              weightTrendState: weightAsync.hasValue
                  ? WeightTrendState.ready
                  : weightAsync.hasError
                  ? WeightTrendState.error
                  : WeightTrendState.loading,
              now: now,
            )
          : null,
      errorMessage: firstError == null
          ? null
          : _extractErrorMessage(firstError),
      onRefresh: () async {
        _reload(ref);
        await Future<void>.delayed(const Duration(milliseconds: 300));
      },
      onSetupProfile: () => context.push('/profile/edit'),
      onRetry: () => _reload(ref),
      onOpenDiet: () => context.go('/diet'),
      onOpenExercise: () => context.go('/exercise'),
      onOpenCoach: () => context.push('/ai/chat'),
      onOpenMonthly: () => context.push('/dashboard/monthly'),
    );
  }

  static void _reload(WidgetRef ref) {
    refreshDashboard(ref);
    ref.invalidate(profileControllerProvider);
    ref.invalidate(recentWeightHistoryProvider);
  }

  static bool _isProfileNotFound(Object? error) {
    return error is ProfileRepositoryException && error.statusCode == 404;
  }

  static bool _isDashboardNotFound(Object? error) {
    return error is DashboardRepositoryException && error.statusCode == 404;
  }

  static String _extractErrorMessage(Object error) {
    if (error is DashboardRepositoryException) {
      return error.message;
    }
    if (error is ProfileRepositoryException) {
      return error.message;
    }
    return error.toString();
  }
}
