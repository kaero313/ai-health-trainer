// 새 디자인 시스템 토큰. 값의 원본은 docs/DESIGN_SYSTEM.md §3·§5·§6·§12-2다.
// 옛 토큰(lib/core/theme/)과 별개이며, 확정 전까지 Theme Preview에서만 쓴다.
import 'dart:math' as math;

import 'package:flutter/widgets.dart';

/// Light/Dark 색 토큰. 같은 이름에 값만 다르다(§2-3).
@immutable
class AppColorTokens {
  const AppColorTokens({
    required this.brightness,
    required this.background,
    required this.foreground,
    required this.card,
    required this.cardForeground,
    required this.popover,
    required this.popoverForeground,
    required this.primary,
    required this.primaryForeground,
    required this.secondary,
    required this.secondaryForeground,
    required this.muted,
    required this.mutedForeground,
    required this.accent,
    required this.accentForeground,
    required this.destructive,
    required this.destructiveForeground,
    required this.border,
    required this.input,
    required this.ring,
    required this.selection,
    required this.primaryMuted,
    required this.success,
    required this.successMuted,
    required this.warning,
    required this.warningMuted,
    required this.info,
    required this.infoMuted,
    required this.error,
    required this.errorMuted,
    required this.chartGrid,
    required this.chartKcal,
    required this.chartProtein,
    required this.chartCarbs,
    required this.chartFat,
    required this.chartExercise,
  });

  final Brightness brightness;

  // shadcn 기본 20개 (§3-2)
  final Color background;
  final Color foreground;
  final Color card;
  final Color cardForeground;
  final Color popover;
  final Color popoverForeground;
  final Color primary;
  final Color primaryForeground;
  final Color secondary;
  final Color secondaryForeground;
  final Color muted;
  final Color mutedForeground;
  final Color accent;
  final Color accentForeground;
  final Color destructive;
  final Color destructiveForeground;
  final Color border;
  final Color input;
  final Color ring;
  final Color selection;

  // 앱 확장 (§3-3, §12-2)
  final Color primaryMuted;
  final Color success;
  final Color successMuted;
  final Color warning;
  final Color warningMuted;
  final Color info;
  final Color infoMuted;

  /// 오류 글자·아이콘·입력 테두리. 버튼 면은 destructive를 쓴다(§3-2).
  final Color error;
  final Color errorMuted;
  final Color chartGrid;
  final Color chartKcal;
  final Color chartProtein;
  final Color chartCarbs;
  final Color chartFat;
  final Color chartExercise;

  static const AppColorTokens light = AppColorTokens(
    brightness: Brightness.light,
    background: Color(0xFFF4F4F5),
    foreground: Color(0xFF09090B),
    card: Color(0xFFFFFFFF),
    cardForeground: Color(0xFF09090B),
    popover: Color(0xFFFFFFFF),
    popoverForeground: Color(0xFF09090B),
    primary: Color(0xFF0E7490),
    primaryForeground: Color(0xFFFFFFFF),
    // 은은한 면 3종(secondary·muted·accent)은 배경 #F4F4F5보다 한 단계 진하게 둔다.
    // 배경과 같으면 트랙·Secondary 버튼·눌림 효과가 보이지 않는다(2026-10-03 확정).
    secondary: Color(0xFFE4E4E7),
    secondaryForeground: Color(0xFF18181B),
    muted: Color(0xFFE4E4E7),
    mutedForeground: Color(0xFF65656E),
    accent: Color(0xFFE4E4E7),
    accentForeground: Color(0xFF18181B),
    destructive: Color(0xFFDC2626),
    destructiveForeground: Color(0xFFFFFFFF),
    border: Color(0xFFE4E4E7),
    input: Color(0xFF8A8A93),
    ring: Color(0xFF0E7490),
    selection: Color(0x330E7490), // primary 20%
    primaryMuted: Color(0xFFECFEFF),
    success: Color(0xFF15803D),
    successMuted: Color(0xFFF0FDF4),
    warning: Color(0xFFB45309),
    warningMuted: Color(0xFFFFFBEB),
    info: Color(0xFF1D4ED8),
    infoMuted: Color(0xFFEFF6FF),
    error: Color(0xFFDC2626),
    errorMuted: Color(0xFFFEF2F2),
    chartGrid: Color(0xFFE4E4E7),
    chartKcal: Color(0xFF0891B2),
    chartProtein: Color(0xFF7C3AED),
    chartCarbs: Color(0xFFD97706),
    chartFat: Color(0xFFDB2777),
    chartExercise: Color(0xFF65A30D),
  );

  static const AppColorTokens dark = AppColorTokens(
    brightness: Brightness.dark,
    background: Color(0xFF09090B),
    foreground: Color(0xFFFAFAFA),
    card: Color(0xFF18181B),
    cardForeground: Color(0xFFFAFAFA),
    popover: Color(0xFF18181B),
    popoverForeground: Color(0xFFFAFAFA),
    primary: Color(0xFF22D3EE),
    primaryForeground: Color(0xFF083344),
    secondary: Color(0xFF27272A),
    secondaryForeground: Color(0xFFFAFAFA),
    muted: Color(0xFF27272A),
    mutedForeground: Color(0xFFA1A1AA),
    accent: Color(0xFF27272A),
    accentForeground: Color(0xFFFAFAFA),
    // 버튼 면. 오류 글자는 error(#F87171)를 쓴다(2026-10-03 확정).
    destructive: Color(0xFFDC2626),
    destructiveForeground: Color(0xFFFFFFFF),
    border: Color(0xFF27272A),
    input: Color(0xFF71717A),
    ring: Color(0xFF22D3EE),
    selection: Color(0x4D22D3EE), // primary 30%
    primaryMuted: Color(0xFF0B2B33),
    success: Color(0xFF4ADE80),
    successMuted: Color(0x1F4ADE80), // success 12%
    warning: Color(0xFFFBBF24),
    warningMuted: Color(0x1FFBBF24), // warning 12%
    info: Color(0xFF60A5FA),
    infoMuted: Color(0x1F60A5FA), // info 12%
    error: Color(0xFFF87171),
    errorMuted: Color(0x1FF87171), // error 12%
    chartGrid: Color(0xFF27272A),
    // 차트 5색은 두 모드 공통이다(§12-2).
    chartKcal: Color(0xFF0891B2),
    chartProtein: Color(0xFF7C3AED),
    chartCarbs: Color(0xFFD97706),
    chartFat: Color(0xFFDB2777),
    chartExercise: Color(0xFF65A30D),
  );

  static AppColorTokens of(Brightness brightness) =>
      brightness == Brightness.dark ? dark : light;

  /// shadcn 기본 토큰 20개 (이름, 색).
  List<(String, Color)> get shadcnEntries => <(String, Color)>[
    ('background', background),
    ('foreground', foreground),
    ('card', card),
    ('cardForeground', cardForeground),
    ('popover', popover),
    ('popoverForeground', popoverForeground),
    ('primary', primary),
    ('primaryForeground', primaryForeground),
    ('secondary', secondary),
    ('secondaryForeground', secondaryForeground),
    ('muted', muted),
    ('mutedForeground', mutedForeground),
    ('accent', accent),
    ('accentForeground', accentForeground),
    ('destructive', destructive),
    ('destructiveForeground', destructiveForeground),
    ('border', border),
    ('input', input),
    ('ring', ring),
    ('selection', selection),
  ];

  /// 앱 확장 토큰 (이름, 색). 이름은 ShadColorScheme.custom 키와 같다.
  List<(String, Color)> get appEntries => <(String, Color)>[
    ('primaryMuted', primaryMuted),
    ('success', success),
    ('successMuted', successMuted),
    ('warning', warning),
    ('warningMuted', warningMuted),
    ('info', info),
    ('infoMuted', infoMuted),
    ('error', error),
    ('errorMuted', errorMuted),
    ('chartGrid', chartGrid),
    ...chartEntries,
  ];

  /// 차트 시리즈 5색 (이름, 색).
  List<(String, Color)> get chartEntries => <(String, Color)>[
    ('chartKcal', chartKcal),
    ('chartProtein', chartProtein),
    ('chartCarbs', chartCarbs),
    ('chartFat', chartFat),
    ('chartExercise', chartExercise),
  ];

  List<(String, Color)> get entries => <(String, Color)>[
    ...shadcnEntries,
    ...appEntries,
  ];

  /// ShadColorScheme.custom에 넣는 맵.
  Map<String, Color> get customMap => <String, Color>{
    for (final (String name, Color color) in appEntries) name: color,
  };
}

/// WCAG 2.x 대비 계산과 표시용 hex 문자열.
abstract final class AppContrast {
  /// [foreground]가 반투명이면 [background] 위에 합성한 뒤 계산한다.
  static double ratio(Color foreground, Color background) {
    final Color fg = foreground.a < 1
        ? Color.alphaBlend(foreground, background)
        : foreground;
    final double l1 = fg.computeLuminance();
    final double l2 = background.computeLuminance();
    return (math.max(l1, l2) + 0.05) / (math.min(l1, l2) + 0.05);
  }

  /// 본문 4.5, 큰 글자·UI 경계 3.0 기준 등급.
  static String grade(double ratio) {
    if (ratio >= 4.5) return 'AA';
    if (ratio >= 3.0) return 'AA Large·UI';
    return '미달';
  }

  /// '#RRGGBB', 반투명이면 '#RRGGBB 12%'.
  static String hex(Color color) {
    final int argb = color.toARGB32();
    final String rgb = (argb & 0xFFFFFF)
        .toRadixString(16)
        .padLeft(6, '0')
        .toUpperCase();
    final int alpha = (argb >> 24) & 0xFF;
    if (alpha == 0xFF) return '#$rgb';
    return '#$rgb ${(alpha / 255 * 100).round()}%';
  }
}

/// 간격 (§5). 4의 배수만 쓴다.
abstract final class AppSpace {
  static const double s4 = 4;
  static const double s8 = 8;
  static const double s12 = 12;
  static const double s16 = 16;
  static const double s20 = 20;
  static const double s24 = 24;
  static const double s32 = 32;
  static const double s48 = 48;

  static const List<(String, double)> all = <(String, double)>[
    ('s4', s4),
    ('s8', s8),
    ('s12', s12),
    ('s16', s16),
    ('s20', s20),
    ('s24', s24),
    ('s32', s32),
    ('s48', s48),
  ];
}

/// 반경 (§6).
abstract final class AppRadii {
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double full = 999;

  static const List<(String, double)> all = <(String, double)>[
    ('sm', sm),
    ('md', md),
    ('lg', lg),
    ('xl', xl),
    ('full', full),
  ];
}
