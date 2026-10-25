// Dashboard 목업 화면(내부 전용). 실제 홈과 같은 DashboardView에 가짜 데이터를 넣고,
// 앱 셸 대신 새 하단 탭(AppBottomNav)을 붙인다. provider·repository·API는 쓰지 않는다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../features/dashboard/presentation/dashboard_view.dart';
import '../../shared/design_system/design_system.dart';
import 'dashboard_mockup_data.dart';

/// 하단 5탭(§11-1). 순서는 현행 그대로다.
const List<AppBottomNavItem> mockupTabs = <AppBottomNavItem>[
  AppBottomNavItem(icon: LucideIcons.house, label: '홈'),
  AppBottomNavItem(icon: LucideIcons.chartLine, label: '통계'),
  AppBottomNavItem(icon: LucideIcons.dumbbell, label: '플랜'),
  AppBottomNavItem(icon: LucideIcons.utensils, label: '식단'),
  AppBottomNavItem(icon: LucideIcons.scanLine, label: '스캔'),
];

class DashboardMockupScreen extends StatefulWidget {
  const DashboardMockupScreen({super.key, required this.state});

  static const Key scrollKey = DashboardView.scrollKey;
  static const Key lastBlockKey = DashboardView.lastBlockKey;

  final DashboardMockupState state;

  @override
  State<DashboardMockupScreen> createState() => _DashboardMockupScreenState();
}

class _DashboardMockupScreenState extends State<DashboardMockupScreen> {
  int _tab = 0;

  // 목업은 동작을 흉내만 낸다. 실제 이동은 하지 않는다.
  void _noop() {}

  Future<void> _refresh() =>
      Future<void>.delayed(const Duration(milliseconds: 600));

  @override
  Widget build(BuildContext context) {
    final DashboardMockupState state = widget.state;
    return DashboardView(
      status: switch (state) {
        DashboardMockupState.data ||
        DashboardMockupState.sparse => DashboardStatus.ready,
        DashboardMockupState.loading => DashboardStatus.loading,
        DashboardMockupState.empty => DashboardStatus.profileRequired,
        DashboardMockupState.error => DashboardStatus.error,
      },
      subtitle: switch (state) {
        DashboardMockupState.data ||
        DashboardMockupState.sparse => dashboardMockupSubtitle,
        DashboardMockupState.loading ||
        DashboardMockupState.empty ||
        DashboardMockupState.error => dashboardMockupDate,
      },
      data: switch (state) {
        DashboardMockupState.data => dashboardMockupFull,
        DashboardMockupState.sparse => dashboardMockupSparse,
        _ => null,
      },
      bottomNav: AppBottomNav(
        items: mockupTabs,
        selectedIndex: _tab,
        onSelected: (int i) => setState(() => _tab = i),
      ),
      onRefresh: _refresh,
      onSetupProfile: _noop,
      onRetry: _noop,
      onOpenDiet: _noop,
      onOpenExercise: _noop,
      onOpenCoach: _noop,
      onOpenMonthly: _noop,
    );
  }
}
