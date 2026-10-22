import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'core/design_system/app_shad_theme.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

void main() {
  runApp(const ProviderScope(child: MyApp()));
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final GoRouter router = ref.watch(routerProvider);
    // 새 디자인 시스템(docs/DESIGN_SYSTEM.md §18)의 ShadTheme을 앱 전체에 둔다.
    // 아직 옮기지 않은 화면은 MaterialApp의 AppTheme을 그대로 쓴다.
    // 옛 화면이 Dark 전용이라 Dark로 고정한다. System·Light는 Appearance 설정과 함께 연다.
    return ShadApp.custom(
      theme: AppShadTheme.light(),
      darkTheme: AppShadTheme.dark(),
      themeMode: ThemeMode.dark,
      appBuilder: (BuildContext context) => MaterialApp.router(
        theme: AppTheme.darkTheme,
        routerConfig: router,
        locale: const Locale('ko'),
        localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
          GlobalShadLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        supportedLocales: const <Locale>[Locale('ko'), Locale('en')],
        builder: (BuildContext context, Widget? child) =>
            ShadAppBuilder(child: child!),
      ),
    );
  }
}
