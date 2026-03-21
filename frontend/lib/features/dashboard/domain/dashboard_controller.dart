import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_repository.dart';

final todayDashboardProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  Ref ref,
) {
  return ref.read(dashboardRepositoryProvider).getToday();
});

final weeklyDashboardProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  Ref ref,
) {
  return ref.read(dashboardRepositoryProvider).getWeekly();
});

final monthlyDashboardProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, String>((
      Ref ref,
      String monthKey,
    ) {
      final ({int year, int month}) resolvedMonth = _parseMonthKey(monthKey);
      return ref.read(dashboardRepositoryProvider).getMonthly(
        year: resolvedMonth.year,
        month: resolvedMonth.month,
      );
    });

final weightHistoryProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((Ref ref) {
      return ref.read(dashboardRepositoryProvider).getWeightHistory();
    });

void refreshDashboard(WidgetRef ref) {
  ref.invalidate(todayDashboardProvider);
  ref.invalidate(weeklyDashboardProvider);
}

({int year, int month}) _parseMonthKey(String monthKey) {
  final List<String> segments = monthKey.split('-');
  if (segments.length != 2) {
    throw const DashboardRepositoryException('월간 리포트 키 형식이 올바르지 않습니다.');
  }

  final int? year = int.tryParse(segments[0]);
  final int? month = int.tryParse(segments[1]);
  if (year == null || month == null || month < 1 || month > 12) {
    throw const DashboardRepositoryException('월간 리포트 키 형식이 올바르지 않습니다.');
  }

  return (year: year, month: month);
}
