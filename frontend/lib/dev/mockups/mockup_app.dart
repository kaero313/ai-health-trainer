// 내부 전용 디자인 목업 앱. 앱 라우터·내비게이션에 넣지 않고 main_design_mockups.dart로만 띄운다.
// 목업 화면 위에는 개발용 컨트롤을 덮지 않는다(캡처에 섞이지 않게).
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../theme_preview/theme_preview_screen.dart';
import 'dashboard_mockup_screen.dart';
import 'mockup_gallery_screen.dart';
import 'mockup_route.dart';

class MockupApp extends StatefulWidget {
  /// [initialRoute]가 없으면 플랫폼 기본 라우트(웹은 # 뒤 경로)를 쓴다.
  const MockupApp({super.key, this.initialRoute});

  final String? initialRoute;

  @override
  State<MockupApp> createState() => _MockupAppState();
}

class _MockupAppState extends State<MockupApp> {
  late final String _initialRoute =
      widget.initialRoute ??
      WidgetsBinding.instance.platformDispatcher.defaultRouteName;

  // 라우트 builder는 페이지를 캐시하므로 모드는 notifier로 내려보낸다.
  late final ValueNotifier<ThemeMode> _mode = ValueNotifier<ThemeMode>(
    MockupRoute.parse(_initialRoute)?.mode ?? ThemeMode.system,
  );
  final ShadThemeData _light = AppShadTheme.light();
  final ShadThemeData _dark = AppShadTheme.dark();

  void _setMode(ThemeMode mode) => _mode.value = mode;

  @override
  void dispose() {
    _mode.dispose();
    super.dispose();
  }

  Route<void>? _onGenerateRoute(RouteSettings settings) {
    final MockupRoute? route = MockupRoute.parse(settings.name);
    if (route == null) return null;
    return MaterialPageRoute<void>(
      settings: settings,
      builder: (BuildContext context) => _page(route),
    );
  }

  Widget _withMode(Widget Function(ThemeMode mode) builder) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: _mode,
      builder: (BuildContext context, ThemeMode mode, Widget? _) =>
          builder(mode),
    );
  }

  Widget _page(MockupRoute route) {
    switch (route.page) {
      case MockupPage.gallery:
        return _withMode(
          (ThemeMode mode) =>
              MockupGalleryScreen(mode: mode, onModeChanged: _setMode),
        );
      case MockupPage.tokens:
        return _withMode(
          (ThemeMode mode) =>
              ThemePreviewScreen(mode: mode, onModeChanged: _setMode),
        );
      case MockupPage.dashboard:
        // URL의 mode가 이 화면의 Light/Dark를 정한다.
        return MockupThemeScope(
          mode: route.mode,
          flavor: route.flavor,
          child: DashboardMockupScreen(state: route.state),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: _mode,
      // Theme Preview 앱과 같은 구성: ShadApp.custom이 테마를 고르고 MaterialApp이 받는다.
      builder: (BuildContext context, ThemeMode mode, Widget? _) =>
          ShadApp.custom(
            theme: _light,
            darkTheme: _dark,
            themeMode: mode,
            appBuilder: _materialApp,
          ),
    );
  }

  Widget _materialApp(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Design Mockups',
      theme: Theme.of(context),
      locale: const Locale('ko'),
      supportedLocales: const <Locale>[Locale('ko'), Locale('en')],
      localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
        GlobalShadLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      builder: (BuildContext context, Widget? child) {
        return ShadAppBuilder(child: child!);
      },
      initialRoute: _initialRoute,
      onGenerateRoute: _onGenerateRoute,
      onUnknownRoute: (RouteSettings settings) => MaterialPageRoute<void>(
        settings: const RouteSettings(name: MockupRoute.galleryPath),
        builder: (BuildContext context) =>
            _page(const MockupRoute(page: MockupPage.gallery)),
      ),
    );
  }
}
