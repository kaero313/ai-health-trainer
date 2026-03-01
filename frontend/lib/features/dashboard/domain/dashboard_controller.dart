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

void refreshDashboard(WidgetRef ref) {
  ref.invalidate(todayDashboardProvider);
  ref.invalidate(weeklyDashboardProvider);
}
