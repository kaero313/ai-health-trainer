import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/router/main_shell.dart';
import 'package:go_router/go_router.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('MainShell keeps five equal tabs at $viewport', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final GoRouter router = _buildRouter();
      addTearDown(router.dispose);

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));

      for (final String label in <String>['홈', '통계', '플랜', '식단', '스캔']) {
        expect(find.text(label), findsOneWidget);
      }
      expect(find.byType(FloatingActionButton), findsNothing);
      expect(tester.takeException(), isNull);

      final Map<String, String> destinations = <String, String>{
        '통계': '/profile',
        '플랜': '/exercise',
        '식단': '/diet',
        '스캔': '/diet/analyze',
        '홈': '/dashboard',
      };

      for (final MapEntry<String, String> entry in destinations.entries) {
        await tester.tap(find.text(entry.key));
        await tester.pumpAndSettle();
        expect(find.byKey(ValueKey<String>(entry.value)), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });
  }
}

GoRouter _buildRouter() {
  return GoRouter(
    initialLocation: '/dashboard',
    routes: <RouteBase>[
      ShellRoute(
        builder: (BuildContext context, GoRouterState state, Widget child) {
          return MainShell(currentLocation: state.uri.path, child: child);
        },
        routes: <RouteBase>[
          for (final String path in <String>[
            '/dashboard',
            '/profile',
            '/exercise',
            '/diet',
            '/diet/analyze',
          ])
            GoRoute(
              path: path,
              builder:
                  (BuildContext context, GoRouterState state) => ColoredBox(
                    color: Colors.black,
                    child: Center(
                      child: Text(path, key: ValueKey<String>(path)),
                    ),
                  ),
            ),
        ],
      ),
    ],
  );
}
