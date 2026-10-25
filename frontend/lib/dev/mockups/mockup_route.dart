// 목업 앱 라우트: URL(경로 + state·mode 쿼리)과 화면을 서로 바꾼다.
// 예: /dashboard?state=sparse&mode=dark. 웹에서는 #/dashboard?state=data&mode=dark로 연다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_tokens.dart';
import 'dashboard_mockup_data.dart';

enum MockupPage { gallery, tokens, dashboard }

/// app: 이 앱의 디자인 토큰. shadcn: shadcn_ui 기본 테마(비교용).
enum MockupThemeFlavor { app, shadcn }

@immutable
class MockupRoute {
  const MockupRoute({
    required this.page,
    this.state = DashboardMockupState.data,
    this.mode = ThemeMode.system,
    this.flavor = MockupThemeFlavor.app,
  });

  static const String galleryPath = '/';
  static const String tokensPath = '/tokens';
  static const String dashboardPath = '/dashboard';

  final MockupPage page;
  final DashboardMockupState state;
  final ThemeMode mode;
  final MockupThemeFlavor flavor;

  /// 알 수 없는 경로면 null. 알 수 없는 state·mode·theme 값은 기본값(data, system, app)이다.
  static MockupRoute? parse(String? location) {
    final Uri uri = Uri.parse(
      (location == null || location.isEmpty) ? '/' : location,
    );
    final Map<String, String> q = uri.queryParameters;
    final ThemeMode mode =
        ThemeMode.values.asNameMap()[q['mode']] ?? ThemeMode.system;
    final DashboardMockupState state =
        DashboardMockupState.values.asNameMap()[q['state']] ??
        DashboardMockupState.data;
    final MockupThemeFlavor flavor =
        MockupThemeFlavor.values.asNameMap()[q['theme']] ??
        MockupThemeFlavor.app;
    final String path = uri.path.isEmpty ? galleryPath : uri.path;
    final MockupPage? page = switch (path) {
      galleryPath => MockupPage.gallery,
      tokensPath => MockupPage.tokens,
      dashboardPath => MockupPage.dashboard,
      _ => null,
    };
    if (page == null) return null;
    return MockupRoute(page: page, state: state, mode: mode, flavor: flavor);
  }

  /// 이 라우트의 URL. theme는 기본값(app)이 아닐 때만 붙인다.
  String get location => switch (page) {
    MockupPage.gallery => '$galleryPath?mode=${mode.name}',
    MockupPage.tokens => '$tokensPath?mode=${mode.name}',
    MockupPage.dashboard =>
      '$dashboardPath?state=${state.name}&mode=${mode.name}'
          '${flavor == MockupThemeFlavor.app ? '' : '&theme=${flavor.name}'}',
  };

  @override
  bool operator ==(Object other) =>
      other is MockupRoute &&
      other.page == page &&
      other.state == state &&
      other.mode == mode &&
      other.flavor == flavor;

  @override
  int get hashCode => Object.hash(page, state, mode, flavor);

  @override
  String toString() => 'MockupRoute($location)';
}

/// 라우트별 테마 모드. system이면 기기 밝기를 따른다.
/// 앱 전체 모드와 별개로 URL의 mode만으로 목업 화면의 Light/Dark를 고정한다.
class MockupThemeScope extends StatelessWidget {
  const MockupThemeScope({
    super.key,
    required this.mode,
    required this.child,
    this.flavor = MockupThemeFlavor.app,
  });

  final ThemeMode mode;
  final MockupThemeFlavor flavor;
  final Widget child;

  /// shadcn_ui 기본 테마(비교용). 색·글자·반경·컴포넌트 테마는 shadcn 기본값(Slate)이다.
  /// 템플릿이 읽는 앱 전용 색(차트·상태·primaryMuted)은 기본 테마에 없으므로 custom으로만 넣고,
  /// 시스템 한글 폰트가 없는 환경(위젯 렌더링)에서도 한글이 보이도록 NotoSansKR fallback만 더한다.
  static ShadThemeData shadcnDefault(Brightness brightness) {
    final AppColorTokens t = AppColorTokens.of(brightness);
    return ShadThemeData(
      brightness: brightness,
      colorScheme: brightness == Brightness.dark
          ? ShadSlateColorScheme.dark(custom: t.customMap)
          : ShadSlateColorScheme.light(custom: t.customMap),
      textTheme: ShadTextTheme().apply(
        fontFamilyFallback: const <String>['NotoSansKR'],
      ),
    );
  }

  static Brightness resolve(ThemeMode mode, BuildContext context) =>
      switch (mode) {
        ThemeMode.light => Brightness.light,
        ThemeMode.dark => Brightness.dark,
        ThemeMode.system => MediaQuery.platformBrightnessOf(context),
      };

  /// ShadApp의 Material 테마 구성을 토큰에서 같은 방식으로 만든다.
  static ThemeData materialTheme(ShadThemeData shad) {
    final ShadColorScheme c = shad.colorScheme;
    return ThemeData(
      brightness: shad.brightness,
      fontFamily: shad.textTheme.family,
      colorScheme: ColorScheme(
        brightness: shad.brightness,
        primary: c.primary,
        onPrimary: c.primaryForeground,
        secondary: c.secondary,
        onSecondary: c.secondaryForeground,
        error: c.destructive,
        onError: c.destructiveForeground,
        surface: c.background,
        onSurface: c.foreground,
      ),
      scaffoldBackgroundColor: c.background,
      dividerTheme: DividerThemeData(color: c.border, thickness: 1),
    );
  }

  @override
  Widget build(BuildContext context) {
    final Brightness brightness = resolve(mode, context);
    final ShadThemeData shad = switch (flavor) {
      MockupThemeFlavor.shadcn => shadcnDefault(brightness),
      MockupThemeFlavor.app =>
        brightness == Brightness.dark
            ? AppShadTheme.dark()
            : AppShadTheme.light(),
    };
    return ShadTheme(
      data: shad,
      child: Theme(data: materialTheme(shad), child: child),
    );
  }
}
