import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/auth/presentation/splash_screen.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('startup shows splash then onboarding on first launch', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final GoRouter router = _startupRouter();
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));

    expect(find.text('AI Health Trainer'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 1499));
    expect(find.text('AI Health Trainer'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 1));
    await tester.pump();
    expect(find.byKey(const Key('onboarding-target')), findsOneWidget);
  });

  testWidgets('startup routes returning users to login without settling', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'onboarding_done': true,
    });
    final GoRouter router = _startupRouter();
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump();

    expect(find.byKey(const Key('login-target')), findsOneWidget);
  });
}

GoRouter _startupRouter() {
  return GoRouter(
    initialLocation: '/splash',
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        builder:
            (BuildContext context, GoRouterState state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder:
            (BuildContext context, GoRouterState state) => const Scaffold(
              body: Text('온보딩', key: Key('onboarding-target')),
            ),
      ),
      GoRoute(
        path: '/login',
        builder:
            (BuildContext context, GoRouterState state) =>
                const Scaffold(body: Text('로그인', key: Key('login-target'))),
      ),
    ],
  );
}
