// 토큰(app_tokens.dart·app_text_styles.dart)에서 ShadThemeData를 만든다.
// 근거는 shadcn_ui 0.57.1 소스(theme/data.dart, themes/default_theme_variant.dart)다.
import 'package:flutter/widgets.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'app_text_styles.dart';
import 'app_tokens.dart';

abstract final class AppShadTheme {
  /// 배지 안쪽 여백(§24). 아이콘 16 + 위아래 4 = 높이 24. shadcn 기본 10/2는 4 격자에서 벗어난다.
  static const EdgeInsets badgePadding = EdgeInsets.symmetric(
    horizontal: AppSpace.s8,
    vertical: AppSpace.s4,
  );
  static const ShadBadgeTheme _badgeTheme = ShadBadgeTheme(
    padding: badgePadding,
  );

  static ShadThemeData light() => build(AppColorTokens.light);
  static ShadThemeData dark() => build(AppColorTokens.dark);

  static ShadColorScheme colorScheme(AppColorTokens t) {
    return ShadColorScheme(
      background: t.background,
      foreground: t.foreground,
      card: t.card,
      cardForeground: t.cardForeground,
      popover: t.popover,
      popoverForeground: t.popoverForeground,
      primary: t.primary,
      primaryForeground: t.primaryForeground,
      secondary: t.secondary,
      secondaryForeground: t.secondaryForeground,
      muted: t.muted,
      mutedForeground: t.mutedForeground,
      accent: t.accent,
      accentForeground: t.accentForeground,
      destructive: t.destructive,
      destructiveForeground: t.destructiveForeground,
      border: t.border,
      input: t.input,
      ring: t.ring,
      selection: t.selection,
      custom: t.customMap,
    );
  }

  /// §4-2 매핑. 색은 넣지 않는다. shadcn 컴포넌트가 이 스타일에
  /// `fallback(color:)`으로 색을 입히므로, 여기서 색을 넣으면 그 색이 이긴다.
  static ShadTextTheme textTheme() {
    return ShadTextTheme(
      family: AppTextStyles.textFamily,
      h1Large: AppTextStyles.numHero,
      h1: AppTextStyles.display,
      h2: AppTextStyles.title,
      h3: AppTextStyles.heading,
      h4: AppTextStyles.heading,
      p: AppTextStyles.body,
      list: AppTextStyles.body,
      blockquote: AppTextStyles.body,
      large: AppTextStyles.bodyStrong,
      small: AppTextStyles.bodySmall,
      muted: AppTextStyles.bodySmall,
      table: AppTextStyles.numSmall,
      custom: const <String, TextStyle>{
        'caption': AppTextStyles.caption,
        'numHero': AppTextStyles.numHero,
        'numLarge': AppTextStyles.numLarge,
        'numMedium': AppTextStyles.numMedium,
        'numSmall': AppTextStyles.numSmall,
      },
    );
  }

  static ShadThemeData build(AppColorTokens t) {
    const BorderRadius radius = BorderRadius.all(Radius.circular(AppRadii.md));
    const BorderRadius cardRadius = BorderRadius.all(
      Radius.circular(AppRadii.lg),
    );
    final TextStyle label = AppTextStyles.withWeight(
      AppTextStyles.bodySmall,
      FontWeight.w600,
    ).copyWith(color: t.foreground);
    final TextStyle fieldText = AppTextStyles.body.copyWith(
      color: t.foreground,
    );
    final TextStyle placeholder = AppTextStyles.body.copyWith(
      color: t.mutedForeground,
    );
    final ShadDecoration fieldDecoration = ShadDecoration(
      color: t.card,
      border: ShadBorder.all(color: t.input, width: 1, radius: radius),
      // 오류 표시는 error 토큰(Dark에서 destructive 면 색은 글자·선 대비가 부족하다).
      errorBorder: ShadBorder.all(color: t.error, width: 1, radius: radius),
    );
    // 버튼 라벨은 §8 bodyStrong. 0.57.1은 크기별 라벨 스타일이 없어
    // compact(sm)는 호출부에서 AppTextStyles.buttonCompact를 넘긴다.
    const TextStyle buttonLabel = AppTextStyles.bodyStrong;

    return ShadThemeData(
      brightness: t.brightness,
      colorScheme: colorScheme(t),
      radius: radius,
      textTheme: textTheme(),
      // ShadButtonSizesTheme: 기본값 regular 40·sm 36·lg 44를 덮어쓴다.
      buttonSizesTheme: const ShadButtonSizesTheme(
        regular: ShadButtonSizeTheme(
          height: 48,
          padding: EdgeInsets.symmetric(horizontal: AppSpace.s16),
        ),
        sm: ShadButtonSizeTheme(
          height: 40,
          padding: EdgeInsets.symmetric(horizontal: AppSpace.s12),
        ),
        // §8: 아이콘 버튼은 누르는 영역 48(아이콘 20).
        icon: ShadButtonSizeTheme(
          height: 48,
          width: 48,
          padding: EdgeInsets.zero,
        ),
      ),
      primaryButtonTheme: const ShadButtonTheme(textStyle: buttonLabel),
      secondaryButtonTheme: const ShadButtonTheme(textStyle: buttonLabel),
      destructiveButtonTheme: const ShadButtonTheme(textStyle: buttonLabel),
      // 0.57.1 기본값은 outline·ghost 글자를 primary로 칠한다. §3-4에 따라 foreground로 둔다.
      outlineButtonTheme: ShadButtonTheme(
        textStyle: buttonLabel,
        foregroundColor: t.foreground,
        hoverForegroundColor: t.accentForeground,
        pressedBackgroundColor: t.accent,
      ),
      ghostButtonTheme: ShadButtonTheme(
        textStyle: buttonLabel,
        foregroundColor: t.foreground,
        hoverForegroundColor: t.accentForeground,
        pressedBackgroundColor: t.accent,
      ),
      linkButtonTheme: const ShadButtonTheme(textStyle: buttonLabel),
      primaryBadgeTheme: _badgeTheme,
      secondaryBadgeTheme: _badgeTheme,
      destructiveBadgeTheme: _badgeTheme,
      outlineBadgeTheme: _badgeTheme,
      cardTheme: ShadCardTheme(
        backgroundColor: t.card,
        padding: const EdgeInsets.all(AppSpace.s16),
        radius: cardRadius,
        border: ShadBorder.all(color: t.border, width: 1),
        shadows: const <BoxShadow>[],
      ),
      decoration: ShadDecoration(
        labelStyle: label,
        errorLabelStyle: label,
        errorStyle: AppTextStyles.bodySmall.copyWith(color: t.error),
        descriptionStyle: AppTextStyles.bodySmall.copyWith(
          color: t.mutedForeground,
        ),
      ),
      inputTheme: ShadInputTheme(
        style: fieldText,
        placeholderStyle: placeholder,
        cursorColor: t.primary,
        // body 22 + 위아래 12 + 테두리 2 = 48 (§10)
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.s12,
          vertical: AppSpace.s12,
        ),
        decoration: fieldDecoration,
      ),
      textareaTheme: ShadTextareaTheme(
        style: fieldText,
        placeholderStyle: placeholder,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.s12,
          vertical: AppSpace.s12,
        ),
        // body 3줄 66 + 위아래 24 + 테두리 2
        minHeight: 92,
        resizable: false,
        decoration: fieldDecoration,
      ),
      selectTheme: ShadSelectTheme(
        placeholderStyle: placeholder,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.s12,
          vertical: AppSpace.s12,
        ),
        decoration: fieldDecoration,
      ),
      optionTheme: ShadOptionTheme(
        textStyle: AppTextStyles.body.copyWith(color: t.popoverForeground),
        selectedTextStyle: AppTextStyles.body.copyWith(
          color: t.popoverForeground,
        ),
        hoveredBackgroundColor: t.accent,
      ),
      progressTheme: ShadProgressTheme(
        minHeight: 6,
        color: t.primary,
        backgroundColor: t.muted,
        borderRadius: const BorderRadius.all(Radius.circular(AppRadii.full)),
        innerBorderRadius: const BorderRadius.all(
          Radius.circular(AppRadii.full),
        ),
      ),
      primaryAlertTheme: ShadAlertTheme(
        titleStyle: AppTextStyles.bodyStrong.copyWith(color: t.foreground),
        descriptionStyle: AppTextStyles.bodySmall.copyWith(color: t.foreground),
      ),
      destructiveAlertTheme: ShadAlertTheme(
        iconColor: t.error,
        titleStyle: AppTextStyles.bodyStrong.copyWith(color: t.error),
        descriptionStyle: AppTextStyles.bodySmall.copyWith(color: t.foreground),
        decoration: ShadDecoration(
          color: t.errorMuted,
          border: ShadBorder.all(
            color: t.error,
            width: 1,
            radius: radius,
            padding: const EdgeInsets.all(AppSpace.s16),
          ),
        ),
      ),
    );
  }
}

/// 앱 확장 색 토큰 getter (§3-1). 예: `ShadTheme.of(context).colorScheme.success`.
extension AppColorSchemeX on ShadColorScheme {
  Color get primaryMuted => custom['primaryMuted']!;
  Color get success => custom['success']!;
  Color get successMuted => custom['successMuted']!;
  Color get warning => custom['warning']!;
  Color get warningMuted => custom['warningMuted']!;
  Color get info => custom['info']!;
  Color get infoMuted => custom['infoMuted']!;
  Color get error => custom['error']!;
  Color get errorMuted => custom['errorMuted']!;
  Color get chartGrid => custom['chartGrid']!;
  Color get chartKcal => custom['chartKcal']!;
  Color get chartProtein => custom['chartProtein']!;
  Color get chartCarbs => custom['chartCarbs']!;
  Color get chartFat => custom['chartFat']!;
  Color get chartExercise => custom['chartExercise']!;
}

/// custom 텍스트 토큰 getter.
extension AppTextThemeX on ShadTextTheme {
  TextStyle get caption => custom['caption']!;
  TextStyle get numHero => custom['numHero']!;
  TextStyle get numLarge => custom['numLarge']!;
  TextStyle get numMedium => custom['numMedium']!;
  TextStyle get numSmall => custom['numSmall']!;
}
