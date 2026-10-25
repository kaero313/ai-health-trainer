// 내부 전용 Theme Preview 앱. 앱 내비게이션에 넣지 않고 main_theme_preview.dart로만 띄운다.
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import 'theme_preview_screen.dart';

class ThemePreviewApp extends StatefulWidget {
  const ThemePreviewApp({super.key, this.initialMode = ThemeMode.system});

  final ThemeMode initialMode;

  @override
  State<ThemePreviewApp> createState() => _ThemePreviewAppState();
}

class _ThemePreviewAppState extends State<ThemePreviewApp> {
  late ThemeMode _mode = widget.initialMode;
  final ShadThemeData _light = AppShadTheme.light();
  final ShadThemeData _dark = AppShadTheme.dark();

  @override
  Widget build(BuildContext context) {
    // interop 가이드 방식: ShadApp.custom이 테마를 고르고 MaterialApp이 그 Theme을 받는다.
    return ShadApp.custom(
      theme: _light,
      darkTheme: _dark,
      themeMode: _mode,
      appBuilder: (BuildContext context) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Theme Preview',
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
          home: ThemePreviewScreen(
            mode: _mode,
            onModeChanged: (ThemeMode mode) => setState(() => _mode = mode),
          ),
        );
      },
    );
  }
}
