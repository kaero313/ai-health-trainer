// 배지와 범례 점 (docs/DESIGN_SYSTEM.md §3-4, §12-3, §13-1).
// 중립 배지는 정보·수치용이고, 상태 배지는 아이콘 + 문구로 상태를 전한다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

enum AppBadgeTone { neutral, outline, success, warning, error, info }

class AppBadge extends StatelessWidget {
  /// 중립 배지: secondary 면. 정보·연속 기록·변화량처럼 판단이 없는 값.
  const AppBadge.neutral({
    super.key,
    required this.label,
    this.icon,
    this.semanticLabel,
  }) : tone = AppBadgeTone.neutral;

  /// 중립 외곽선 배지: 면 없음, 1px border.
  const AppBadge.outline({
    super.key,
    required this.label,
    this.icon,
    this.semanticLabel,
  }) : tone = AppBadgeTone.outline;

  /// 상태 배지: 아이콘 16 + caption, 배경 xxxMuted, 글자·아이콘 xxx (§13-1).
  /// [icon]을 주지 않으면 상태별 기본 Lucide 아이콘을 쓴다.
  const AppBadge.status({
    super.key,
    required this.tone,
    required this.label,
    this.icon,
    this.semanticLabel,
  }) : assert(
         tone != AppBadgeTone.neutral && tone != AppBadgeTone.outline,
         '상태 배지는 success·warning·error·info만 쓴다',
       );

  final AppBadgeTone tone;
  final String label;
  final IconData? icon;

  /// 화면 낭독기용 문구. 아이콘이 의미를 더하면(예: 감소 화살표) 반드시 준다.
  final String? semanticLabel;

  /// 상태별 기본 아이콘(§13-1). 중립 배지는 기본 아이콘이 없다.
  static IconData? defaultIcon(AppBadgeTone tone) => switch (tone) {
    AppBadgeTone.success => LucideIcons.circleCheck,
    AppBadgeTone.warning => LucideIcons.triangleAlert,
    AppBadgeTone.error => LucideIcons.circleX,
    AppBadgeTone.info => LucideIcons.info,
    AppBadgeTone.neutral || AppBadgeTone.outline => null,
  };

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final (Color fg, Color? bg) = switch (tone) {
      AppBadgeTone.neutral => (cs.secondaryForeground, cs.secondary),
      AppBadgeTone.outline => (cs.foreground, null),
      AppBadgeTone.success => (cs.success, cs.successMuted),
      AppBadgeTone.warning => (cs.warning, cs.warningMuted),
      AppBadgeTone.error => (cs.error, cs.errorMuted),
      AppBadgeTone.info => (cs.info, cs.infoMuted),
    };
    final IconData? effectiveIcon = icon ?? defaultIcon(tone);
    final Widget content = Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        if (effectiveIcon != null) ...<Widget>[
          Icon(effectiveIcon, size: 16, color: fg),
          const SizedBox(width: AppSpace.s4),
        ],
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.caption.copyWith(color: fg),
          ),
        ),
      ],
    );
    // 안쪽 여백 8/4는 테마(AppShadTheme.badgePadding)가 정한다.
    final Widget badge = tone == AppBadgeTone.outline
        ? ShadBadge.outline(foregroundColor: fg, child: content)
        : ShadBadge.raw(
            variant: tone == AppBadgeTone.neutral
                ? ShadBadgeVariant.secondary
                : ShadBadgeVariant.primary,
            backgroundColor: bg,
            hoverBackgroundColor: bg,
            foregroundColor: fg,
            child: content,
          );
    return Semantics(
      label: semanticLabel ?? label,
      excludeSemantics: true,
      child: badge,
    );
  }
}

/// 범례 점 + caption 라벨. 점만 시리즈 색이고 글자는 foreground다(§12-3).
class AppLegendDot extends StatelessWidget {
  const AppLegendDot({
    super.key,
    required this.color,
    required this.label,
    this.dotSize = 8,
  });

  final Color color;
  final String label;
  final double dotSize;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Container(
          width: dotSize,
          height: dotSize,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: AppSpace.s4),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.caption.copyWith(color: cs.foreground),
          ),
        ),
      ],
    );
  }
}
