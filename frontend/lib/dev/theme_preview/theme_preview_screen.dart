// Theme Preview 화면 뼈대: 상단 고정 영역(제목, 모드 선택, 적용 밝기)과 섹션 목록.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'sections/card_sections.dart';
import 'sections/chart_section.dart';
import 'sections/color_sections.dart';
import 'sections/component_sections.dart';
import 'sections/type_sections.dart';

class ThemePreviewScreen extends StatelessWidget {
  const ThemePreviewScreen({
    super.key,
    required this.mode,
    required this.onModeChanged,
  });

  static const Key scrollKey = ValueKey<String>('theme-preview-scroll');

  final ThemeMode mode;
  final ValueChanged<ThemeMode> onModeChanged;

  @override
  Widget build(BuildContext context) {
    final ShadThemeData theme = ShadTheme.of(context);
    final ShadColorScheme cs = theme.colorScheme;
    return Scaffold(
      backgroundColor: cs.background,
      body: SafeArea(
        child: DefaultTextStyle(
          style: AppTextStyles.body.copyWith(color: cs.foreground),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _Header(
                mode: mode,
                brightness: theme.brightness,
                onModeChanged: onModeChanged,
              ),
              Expanded(
                child: SingleChildScrollView(
                  key: scrollKey,
                  padding: const EdgeInsets.fromLTRB(
                    AppSpace.s20,
                    0,
                    AppSpace.s20,
                    AppSpace.s48,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      ...colorSections(context),
                      ...typographySections(context),
                      ...buttonInputSections(context),
                      ...cardBadgeProgressSections(context),
                      ...chartSections(context),
                      ...radiusSpacingSections(context),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.mode,
    required this.brightness,
    required this.onModeChanged,
  });

  final ThemeMode mode;
  final Brightness brightness;
  final ValueChanged<ThemeMode> onModeChanged;

  static const List<(ThemeMode, String, IconData)> _options =
      <(ThemeMode, String, IconData)>[
        (ThemeMode.system, 'System', LucideIcons.monitor),
        (ThemeMode.light, 'Light', LucideIcons.sun),
        (ThemeMode.dark, 'Dark', LucideIcons.moon),
      ];

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final String applied = brightness == Brightness.dark ? 'Dark' : 'Light';
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s20,
        AppSpace.s16,
        AppSpace.s20,
        AppSpace.s12,
      ),
      decoration: BoxDecoration(
        color: cs.background,
        border: Border(bottom: BorderSide(color: cs.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            'Theme Preview',
            style: AppTextStyles.title.copyWith(color: cs.foreground),
          ),
          const SizedBox(height: AppSpace.s12),
          // §11-3 세그먼트: muted 트랙 + 선택 항목 card 면. 시안으로 채우지 않는다.
          Container(
            height: 48,
            padding: const EdgeInsets.all(AppSpace.s4),
            decoration: BoxDecoration(
              color: cs.muted,
              borderRadius: BorderRadius.circular(AppRadii.md),
            ),
            child: Row(
              children: <Widget>[
                for (final (ThemeMode value, String label, IconData icon)
                    in _options)
                  Expanded(
                    child: _Segment(
                      label: label,
                      icon: icon,
                      selected: value == mode,
                      onTap: () => onModeChanged(value),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: AppSpace.s8),
          Text(
            '적용된 밝기: $applied',
            style: AppTextStyles.bodySmall.copyWith(color: cs.mutedForeground),
          ),
        ],
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Color fg = selected ? cs.foreground : cs.mutedForeground;
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          decoration: BoxDecoration(
            color: selected ? cs.card : cs.muted,
            borderRadius: BorderRadius.circular(AppRadii.sm),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(icon, size: 16, color: fg),
              const SizedBox(width: AppSpace.s4),
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.caption.copyWith(color: fg),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
