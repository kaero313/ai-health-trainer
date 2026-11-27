// 새 디자인 시스템 화면을 앱 루트(main.dart)와 같은 구성으로 띄우는 테스트 도구
// (docs/DESIGN_SYSTEM.md §18 "위젯 테스트 공통 래퍼").
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_shad_theme.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// ShadApp.custom 아래 MaterialApp으로 [child]를 띄운다.
/// Dark는 지금 앱처럼 옛 AppTheme을, Light는 ShadApp이 토큰에서 만든 Material 테마를 쓴다
/// (전환이 끝나 Light를 열 때의 구성).
Widget designSystemHost(
  Widget child, {
  Brightness brightness = Brightness.dark,
  List<Override> overrides = const <Override>[],
}) {
  final bool dark = brightness == Brightness.dark;
  return ProviderScope(
    key: UniqueKey(),
    overrides: overrides,
    child: ShadApp.custom(
      theme: AppShadTheme.light(),
      darkTheme: AppShadTheme.dark(),
      themeMode: dark ? ThemeMode.dark : ThemeMode.light,
      appBuilder: (BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: dark ? AppTheme.darkTheme : Theme.of(context),
        locale: const Locale('ko'),
        supportedLocales: const <Locale>[Locale('ko'), Locale('en')],
        localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
          GlobalShadLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        builder: (BuildContext context, Widget? app) =>
            ShadAppBuilder(child: app!),
        home: child,
      ),
    ),
  );
}

/// [host]를 띄우고 첫 화면이 그려질 때까지 진행한다.
/// 앱 뼈대(테마·지역화)가 준비된 다음 프레임에 화면이 나오므로 시간을 두고 한 번 더 그린다.
Future<void> pumpHost(WidgetTester tester, Widget host) async {
  await tester.pumpWidget(host);
  await tester.pump(const Duration(milliseconds: 100));
}

/// 같은 검사를 Light·Dark에서 한 번씩 돌린다. 설명 뒤에 [light]·[dark]가 붙는다.
void testWidgetsInBothModes(
  String description,
  Future<void> Function(WidgetTester tester, Brightness brightness) body, {
  Timeout? timeout,
}) {
  for (final Brightness brightness in <Brightness>[
    Brightness.light,
    Brightness.dark,
  ]) {
    testWidgets(
      '$description [${brightness.name}]',
      (WidgetTester tester) => body(tester, brightness),
      timeout: timeout,
    );
  }
}

/// [brightness]에 맞는 앱 색 토큰.
ShadColorScheme colorsFor(Brightness brightness) =>
    (brightness == Brightness.dark ? AppShadTheme.dark() : AppShadTheme.light())
        .colorScheme;

/// 논리 크기 [size]의 화면으로 바꾸고 테스트 끝에 되돌린다.
void useViewport(WidgetTester tester, Size size, {double bottomInset = 0}) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  if (bottomInset > 0) {
    tester.view.padding = FakeViewPadding(bottom: bottomInset);
  }
  addTearDown(tester.view.reset);
}
