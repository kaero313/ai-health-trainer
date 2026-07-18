import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/auth/presentation/login_screen.dart';
import 'package:frontend/features/auth/presentation/onboarding_screen.dart';
import 'package:frontend/features/auth/presentation/register_screen.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('auth entry screens fit $viewport at large text scale', (
      WidgetTester tester,
    ) async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final GoRouter router = _buildAuthRouter();
      addTearDown(router.dispose);

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            theme: AppTheme.darkTheme,
            routerConfig: router,
            builder:
                (BuildContext context, Widget? child) => MediaQuery(
                  data: MediaQuery.of(
                    context,
                  ).copyWith(textScaler: const TextScaler.linear(1.3)),
                  child: child!,
                ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('다시 만나서 반갑습니다'), findsOneWidget);
      expect(tester.takeException(), isNull);

      router.go('/register');
      await tester.pumpAndSettle();
      expect(find.text('코칭을 시작할 준비가 됐습니다'), findsOneWidget);
      expect(tester.takeException(), isNull);

      router.go('/onboarding');
      await tester.pumpAndSettle();
      expect(find.text('한 끼를 정확하게 기록하세요'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}

GoRouter _buildAuthRouter() {
  return GoRouter(
    initialLocation: '/login',
    routes: <RouteBase>[
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      GoRoute(
        path: '/onboarding',
        builder: (_, __) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/dashboard',
        builder: (_, __) => const Scaffold(body: Text('홈 도착')),
      ),
    ],
  );
}
