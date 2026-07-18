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

  static const List<_NavigationDestination> _destinations =
      <_NavigationDestination>[
        _NavigationDestination('홈', Icons.grid_view_rounded, '/dashboard'),
        _NavigationDestination('통계', Icons.monitor_heart_outlined, '/profile'),
        _NavigationDestination('플랜', Icons.fitness_center, '/exercise'),
        _NavigationDestination('식단', Icons.restaurant_outlined, '/diet'),
        _NavigationDestination(
          '스캔',
          Icons.center_focus_strong,
          '/diet/analyze',
        ),
      ];

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

  @override
  Widget build(BuildContext context) {
    final int selectedIndex = _selectedIndex();

    return Scaffold(
      extendBody: true,
      backgroundColor: AppColors.background,
      body: child,
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
          child: Container(
            height: AppSpacing.bottomNavHeight,
            decoration: BoxDecoration(
              color: AppColors.surface.withValues(alpha: 0.94),
              borderRadius: BorderRadius.circular(AppRadius.xl),
              border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.64),
                  blurRadius: 26,
                  offset: const Offset(0, -8),
                ),
              ],
            ),
            child: Row(
              children: <Widget>[
                for (int index = 0; index < _destinations.length; index++)
                  _NavItem(
                    destination: _destinations[index],
                    active: selectedIndex == index,
                    onTap: () => context.go(_destinations[index].route),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavigationDestination {
  final String label;
  final IconData icon;
  final String route;

  const _NavigationDestination(this.label, this.icon, this.route);
}

class _NavItem extends StatelessWidget {
  final _NavigationDestination destination;
  final bool active;
  final VoidCallback onTap;

  const _NavItem({
    required this.destination,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color color = active ? AppColors.primary : AppColors.textSecondary;

    return Expanded(
      child: Semantics(
        selected: active,
        button: true,
        label: '${destination.label} 탭',
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          onTap: onTap,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOutCubic,
                width: 42,
                height: 30,
                decoration: BoxDecoration(
                  color: active ? AppColors.primarySoft : Colors.transparent,
                  borderRadius: BorderRadius.circular(AppRadius.full),
                ),
                child: Icon(destination.icon, color: color, size: 19),
              ),
              const SizedBox(height: 3),
              Text(
                destination.label,
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
      ),
    );
  }
}
