// 목업 갤러리(내부 전용): 위에 System/Light/Dark 선택, 아래에 Theme Preview와 Dashboard 상태별 목록.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_motion.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import '../../shared/design_system/design_system.dart';
import 'dashboard_mockup_data.dart';
import 'mockup_route.dart';

class MockupGalleryScreen extends StatelessWidget {
  const MockupGalleryScreen({
    super.key,
    required this.mode,
    required this.onModeChanged,
  });

  final ThemeMode mode;
  final ValueChanged<ThemeMode> onModeChanged;

  static const Map<DashboardMockupState, (String, String, IconData)> _states =
      <DashboardMockupState, (String, String, IconData)>{
        DashboardMockupState.data: (
          'Dashboard · data',
          '캡처 기준 값',
          LucideIcons.house,
        ),
        DashboardMockupState.loading: (
          'Dashboard · loading',
          '첫 진입 스켈레톤',
          LucideIcons.loader,
        ),
        DashboardMockupState.empty: (
          'Dashboard · empty',
          '프로필 없음',
          LucideIcons.userRound,
        ),
        DashboardMockupState.sparse: (
          'Dashboard · sparse',
          '기록 부족',
          LucideIcons.chartLine,
        ),
        DashboardMockupState.error: (
          'Dashboard · error',
          '불러오기 실패',
          LucideIcons.circleX,
        ),
      };

  void _open(BuildContext context, MockupRoute route) {
    Navigator.of(context).pushNamed(route.location);
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const AppHeader.root(
            title: 'Design Mockups',
            subtitle: '내부 전용 · 가짜 데이터',
          ),
          const SizedBox(height: AppSpace.s24),
          _ModeSelector(mode: mode, onChanged: onModeChanged),
          const SizedBox(height: AppSpace.s24),
          NavRowCard(
            icon: LucideIcons.palette,
            title: 'Theme Preview',
            subtitle: '토큰·컴포넌트 견본',
            onTap: () => _open(
              context,
              MockupRoute(page: MockupPage.tokens, mode: mode),
            ),
          ),
          for (final MapEntry<DashboardMockupState, (String, String, IconData)>
              e
              in _states.entries) ...<Widget>[
            const SizedBox(height: AppSpace.s12),
            NavRowCard(
              icon: e.value.$3,
              title: e.value.$1,
              subtitle: e.value.$2,
              onTap: () => _open(
                context,
                MockupRoute(
                  page: MockupPage.dashboard,
                  state: e.key,
                  mode: mode,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// §11-3 세그먼트: muted 트랙 + 선택 항목 card 면.
class _ModeSelector extends StatelessWidget {
  const _ModeSelector({required this.mode, required this.onChanged});

  final ThemeMode mode;
  final ValueChanged<ThemeMode> onChanged;

  static const List<(ThemeMode, String, IconData)> _options =
      <(ThemeMode, String, IconData)>[
        (ThemeMode.system, 'System', LucideIcons.monitor),
        (ThemeMode.light, 'Light', LucideIcons.sun),
        (ThemeMode.dark, 'Dark', LucideIcons.moon),
      ];

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Container(
      height: 48,
      padding: const EdgeInsets.all(AppSpace.s4),
      decoration: BoxDecoration(
        color: cs.muted,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Row(
        children: <Widget>[
          for (final (ThemeMode value, String label, IconData icon) in _options)
            Expanded(
              child: Semantics(
                button: true,
                selected: value == mode,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => onChanged(value),
                  child: AnimatedContainer(
                    duration: AppMotion.selection,
                    decoration: BoxDecoration(
                      color: value == mode ? cs.card : cs.muted,
                      borderRadius: BorderRadius.circular(AppRadii.sm),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: <Widget>[
                        Icon(
                          icon,
                          size: 16,
                          color: value == mode
                              ? cs.foreground
                              : cs.mutedForeground,
                        ),
                        const SizedBox(width: AppSpace.s4),
                        Text(
                          label,
                          style: AppTextStyles.caption.copyWith(
                            color: value == mode
                                ? cs.foreground
                                : cs.mutedForeground,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
