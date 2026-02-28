import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_colors.dart';

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
      case 1:
        context.go('/diet');
      case 2:
        context.go('/exercise');
      case 3:
        context.go('/profile');
      default:
        context.go('/dashboard');
    }
  }

  @override
  Widget build(BuildContext context) {
    final int selectedIndex = _selectedIndex();

    return Scaffold(
      body: child,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.background,
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('빠른 기록 기능은 다음 단계에서 구현됩니다')),
          );
        },
        child: const Icon(Icons.add),
      ),
      bottomNavigationBar: BottomAppBar(
        color: AppColors.surface,
        shape: const CircularNotchedRectangle(),
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
