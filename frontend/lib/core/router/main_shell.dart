import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  final String currentLocation;

  const MainShell({
    super.key,
    required this.child,
    required this.currentLocation,
  });

  int _selectedIndex() {
    if (currentLocation.startsWith('/dashboard')) {
      return 0;
    }
    if (currentLocation.startsWith('/diet')) {
      return 1;
    }
    if (currentLocation.startsWith('/exercise')) {
      return 2;
    }
    if (currentLocation.startsWith('/profile')) {
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
        context.go('/diet');
        return;
      case 2:
        context.go('/exercise');
        return;
      case 3:
        context.go('/profile');
        return;
      default:
        context.go('/dashboard');
        return;
    }
  }

  void _showQuickActionSheet(BuildContext outerContext) {
    showModalBottomSheet<void>(
      context: outerContext,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
      ),
      builder: (BuildContext sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _QuickActionTile(
                icon: Icons.restaurant,
                title: '🍽 식단 추가',
                onTap:
                    () => _closeSheetThenPush(
                      sheetContext: sheetContext,
                      outerContext: outerContext,
                      route: '/diet/add',
                    ),
              ),
              _QuickActionTile(
                icon: Icons.photo_camera,
                title: '📷 사진 분석',
                onTap:
                    () => _closeSheetThenPush(
                      sheetContext: sheetContext,
                      outerContext: outerContext,
                      route: '/diet/analyze',
                    ),
              ),
              _QuickActionTile(
                icon: Icons.fitness_center,
                title: '💪 운동 추가',
                onTap:
                    () => _closeSheetThenPush(
                      sheetContext: sheetContext,
                      outerContext: outerContext,
                      route: '/exercise/add',
                    ),
              ),
              _QuickActionTile(
                icon: Icons.smart_toy,
                title: '🤖 AI 코칭',
                onTap:
                    () => _closeSheetThenPush(
                      sheetContext: sheetContext,
                      outerContext: outerContext,
                      route: '/ai/chat',
                    ),
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
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
      body: child,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton(
        shape: const CircleBorder(),
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        onPressed: () => _showQuickActionSheet(context),
        child: const Icon(Icons.add),
      ),
      bottomNavigationBar: BottomAppBar(
        color: AppColors.surface,
        shape: const CircularNotchedRectangle(),
        notchMargin: 6,
        child: SizedBox(
          height: 68,
          child: Row(
            children: [
              _NavItem(
                label: '대시보드',
                icon: Icons.home,
                active: selectedIndex == 0,
                onTap: () => _onTabTap(context, 0),
              ),
              _NavItem(
                label: '식단',
                icon: Icons.restaurant,
                active: selectedIndex == 1,
                onTap: () => _onTabTap(context, 1),
              ),
              const SizedBox(width: 56),
              _NavItem(
                label: '운동',
                icon: Icons.fitness_center,
                active: selectedIndex == 2,
                onTap: () => _onTabTap(context, 2),
              ),
              _NavItem(
                label: '프로필',
                icon: Icons.person,
                active: selectedIndex == 3,
                onTap: () => _onTabTap(context, 3),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _QuickActionTile({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(
        title,
        style: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
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
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
