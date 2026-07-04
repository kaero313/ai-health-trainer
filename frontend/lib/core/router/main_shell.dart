import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_typography.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  final String currentLocation;

  const MainShell({
    super.key,
    required this.child,
    required this.currentLocation,
  });

  int _selectedIndex() {
    if (currentLocation.startsWith('/profile')) {
      return 1;
    }
    if (currentLocation.startsWith('/exercise')) {
      return 2;
    }
    if (currentLocation.startsWith('/diet/analyze')) {
      return 4;
    }
    if (currentLocation.startsWith('/diet')) {
      return 3;
    }
    return 0;
  }

  void _onTabTap(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/dashboard');
        return;
      case 1:
        context.go('/profile');
        return;
      case 2:
        context.go('/exercise');
        return;
      case 3:
        context.go('/diet');
        return;
      case 4:
        context.go('/diet/analyze');
        return;
    }
  }

  void _showQuickActionSheet(BuildContext outerContext) {
    showModalBottomSheet<void>(
      context: outerContext,
      backgroundColor: AppColors.surfaceLow,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
      ),
      builder: (BuildContext sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('빠른 실행', style: AppTypography.h3),
                const SizedBox(height: AppSpacing.sm),
                _QuickActionTile(
                  icon: Icons.restaurant_menu,
                  title: '식단 기록 추가',
                  subtitle: '오늘 먹은 음식을 직접 입력합니다.',
                  onTap:
                      () => _closeSheetThenPush(
                        sheetContext: sheetContext,
                        outerContext: outerContext,
                        route: '/diet/add',
                      ),
                ),
                _QuickActionTile(
                  icon: Icons.add_a_photo_outlined,
                  title: '사진으로 식단 분석',
                  subtitle: '음식 사진을 AI로 분석합니다.',
                  onTap:
                      () => _closeSheetThenPush(
                        sheetContext: sheetContext,
                        outerContext: outerContext,
                        route: '/diet/analyze',
                      ),
                ),
                _QuickActionTile(
                  icon: Icons.fitness_center,
                  title: '운동 기록 추가',
                  subtitle: '세트, 반복, 중량을 기록합니다.',
                  onTap:
                      () => _closeSheetThenPush(
                        sheetContext: sheetContext,
                        outerContext: outerContext,
                        route: '/exercise/add',
                      ),
                ),
                _QuickActionTile(
                  icon: Icons.psychology_alt_outlined,
                  title: 'AI 코치에게 질문',
                  subtitle: '식단과 운동 맥락으로 답변을 받습니다.',
                  onTap:
                      () => _closeSheetThenPush(
                        sheetContext: sheetContext,
                        outerContext: outerContext,
                        route: '/ai/chat',
                      ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _closeSheetThenPush({
    required BuildContext sheetContext,
    required BuildContext outerContext,
    required String route,
  }) {
    Navigator.of(sheetContext).pop();
    Future<void>.microtask(() {
      if (!outerContext.mounted) {
        return;
      }
      outerContext.push(route);
    });
  }

  @override
  Widget build(BuildContext context) {
    final int selectedIndex = _selectedIndex();

    return Scaffold(
      extendBody: true,
      backgroundColor: AppColors.background,
      body: child,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: Container(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.28),
              blurRadius: 28,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: FloatingActionButton(
          shape: const CircleBorder(),
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.background,
          elevation: 0,
          onPressed: () => _showQuickActionSheet(context),
          child: const Icon(Icons.add, size: 24),
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
          child: Container(
            height: 72,
            decoration: BoxDecoration(
              color: AppColors.surface.withValues(alpha: 0.94),
              borderRadius: BorderRadius.circular(AppRadius.xl),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.55),
                  blurRadius: 26,
                  offset: const Offset(0, -8),
                ),
              ],
            ),
            child: Row(
              children: [
                _NavItem(
                  label: '홈',
                  icon: Icons.grid_view_rounded,
                  active: selectedIndex == 0,
                  onTap: () => _onTabTap(context, 0),
                ),
                _NavItem(
                  label: '통계',
                  icon: Icons.monitor_heart_outlined,
                  active: selectedIndex == 1,
                  onTap: () => _onTabTap(context, 1),
                ),
                _NavItem(
                  label: '플랜',
                  icon: Icons.fitness_center,
                  active: selectedIndex == 2,
                  onTap: () => _onTabTap(context, 2),
                ),
                _NavItem(
                  label: '식단',
                  icon: Icons.restaurant,
                  active: selectedIndex == 3,
                  onTap: () => _onTabTap(context, 3),
                ),
                _NavItem(
                  label: '스캔',
                  icon: Icons.center_focus_strong,
                  active: selectedIndex == 4,
                  onTap: () => _onTabTap(context, 4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _QuickActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.primarySoft,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Icon(icon, color: AppColors.primary, size: 20),
      ),
      title: Text(title, style: AppTypography.body1),
      subtitle: Text(
        subtitle,
        style: AppTypography.caption.copyWith(color: AppColors.textDisabled),
      ),
      onTap: onTap,
    );
  }
}

class _NavItem extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  const _NavItem({
    required this.label,
    required this.icon,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color color = active ? AppColors.primary : AppColors.textSecondary;

    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: active ? 42 : 28,
              height: 30,
              decoration: BoxDecoration(
                color: active ? AppColors.primarySoft : Colors.transparent,
                borderRadius: BorderRadius.circular(AppRadius.full),
              ),
              child: Icon(icon, color: color, size: 19),
            ),
            const SizedBox(height: 3),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.caption.copyWith(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
