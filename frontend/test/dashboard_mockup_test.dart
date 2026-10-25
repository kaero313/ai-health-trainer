// 내부 전용 Dashboard 목업(lib/dev/mockups/) 렌더링·라우트 테스트.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/dev/mockups/dashboard_mockup_data.dart';
import 'package:frontend/dev/mockups/dashboard_mockup_screen.dart';
import 'package:frontend/dev/mockups/mockup_app.dart';
import 'package:frontend/dev/mockups/mockup_route.dart';
import 'package:frontend/dev/theme_preview/theme_preview_screen.dart';
import 'package:frontend/shared/design_system/design_system.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

const List<Size> _viewports = <Size>[
  Size(360, 800),
  Size(390, 844),
  Size(430, 932),
];

// 스켈레톤 펄스가 계속 돌아서 pumpAndSettle 대신 고정 시간만큼 진행한다.
Future<void> _settle(WidgetTester tester) async {
  for (int i = 0; i < 5; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void _useViewport(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

/// 목업을 띄우고 예외 없이 끝까지 스크롤되는지 본다. overflow도 예외로 잡힌다.
Future<void> _pumpAndScrollToEnd(
  WidgetTester tester,
  String location,
  String reason,
) async {
  // 이전 앱의 라우트·상태가 남지 않도록 새 키로 띄운다.
  await tester.pumpWidget(MockupApp(key: UniqueKey(), initialRoute: location));
  await _settle(tester);
  expect(tester.takeException(), isNull, reason: reason);
  expect(find.byType(DashboardMockupScreen), findsOneWidget, reason: reason);

  await tester.drag(
    find.byKey(DashboardMockupScreen.scrollKey),
    const Offset(0, -6000),
  );
  await _settle(tester);
  expect(tester.takeException(), isNull, reason: reason);

  // 마지막 블록이 하단 탭 위에 완전히 보인다.
  final Rect last = tester.getRect(
    find.byKey(DashboardMockupScreen.lastBlockKey),
  );
  final Rect nav = tester.getRect(find.byType(AppBottomNav));
  expect(last.top, greaterThanOrEqualTo(0), reason: reason);
  expect(last.bottom, lessThanOrEqualTo(nav.top), reason: reason);
}

void main() {
  for (final DashboardMockupState state in DashboardMockupState.values) {
    for (final ThemeMode mode in <ThemeMode>[ThemeMode.light, ThemeMode.dark]) {
      testWidgets('${state.name} ${mode.name} renders at 360/390/430', (
        WidgetTester tester,
      ) async {
        for (final Size size in _viewports) {
          _useViewport(tester, size);
          final String location = MockupRoute(
            page: MockupPage.dashboard,
            state: state,
            mode: mode,
          ).location;
          await _pumpAndScrollToEnd(tester, location, '$location @ $size');

          final BuildContext context = tester.element(
            find.byType(DashboardMockupScreen),
          );
          expect(
            ShadTheme.of(context).brightness,
            mode == ThemeMode.dark ? Brightness.dark : Brightness.light,
          );
        }
      });
    }
  }

  // 비교용 shadcn 기본 테마(Slate)에서도 앱 전용 색(custom)이 있어 템플릿이 그려진다.
  for (final ThemeMode mode in <ThemeMode>[ThemeMode.light, ThemeMode.dark]) {
    testWidgets('shadcn default theme renders data ${mode.name}', (
      WidgetTester tester,
    ) async {
      _useViewport(tester, const Size(390, 844));
      final String location = MockupRoute(
        page: MockupPage.dashboard,
        mode: mode,
        flavor: MockupThemeFlavor.shadcn,
      ).location;
      expect(location, contains('theme=shadcn'));
      await _pumpAndScrollToEnd(tester, location, location);

      final ShadThemeData theme = ShadTheme.of(
        tester.element(find.byType(DashboardMockupScreen)),
      );
      final ShadColorScheme slate = mode == ThemeMode.dark
          ? const ShadSlateColorScheme.dark()
          : const ShadSlateColorScheme.light();
      expect(theme.colorScheme.primary, slate.primary);
      expect(theme.colorScheme.background, slate.background);
    });
  }

  testWidgets('every state survives text scale 1.3 at 390', (
    WidgetTester tester,
  ) async {
    _useViewport(tester, const Size(390, 844));
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    for (final DashboardMockupState state in DashboardMockupState.values) {
      for (final ThemeMode mode in <ThemeMode>[
        ThemeMode.light,
        ThemeMode.dark,
      ]) {
        final String location = MockupRoute(
          page: MockupPage.dashboard,
          state: state,
          mode: mode,
        ).location;
        await _pumpAndScrollToEnd(tester, location, '$location @ x1.3');
      }
    }
  });

  testWidgets(
    'bottom safe area extends the bar and keeps the last card above it',
    (WidgetTester tester) async {
      _useViewport(tester, const Size(390, 844));
      tester.view.padding = const FakeViewPadding(bottom: 34);
      await _pumpAndScrollToEnd(
        tester,
        '/dashboard?state=data&mode=light',
        'inset 34',
      );
      final Rect nav = tester.getRect(find.byType(AppBottomNav));
      expect(nav.height, AppBottomNav.contentHeight + 34);
      expect(nav.bottom, 844);
      // 마지막 카드와 바 사이 여백 16(§5: 탭 높이 + 16)
      final Rect last = tester.getRect(
        find.byKey(DashboardMockupScreen.lastBlockKey),
      );
      // 드래그 뒤 스크롤 위치에 소수점 이하 오차가 남는다.
      expect(nav.top - last.bottom, closeTo(16, 0.5));
    },
  );

  for (final DashboardMockupState state in <DashboardMockupState>[
    DashboardMockupState.data,
    DashboardMockupState.sparse,
  ]) {
    testWidgets('${state.name} has exactly one primary button', (
      WidgetTester tester,
    ) async {
      _useViewport(tester, const Size(390, 844));
      await tester.pumpWidget(
        MockupApp(initialRoute: '/dashboard?state=${state.name}&mode=dark'),
      );
      await _settle(tester);
      // SingleChildScrollView는 화면 밖 카드도 모두 만든다.
      final Iterable<ShadButton> primaries = tester
          .widgetList<ShadButton>(find.byType(ShadButton))
          .where((ShadButton b) => b.variant == ShadButtonVariant.primary);
      expect(primaries.length, 1);
      expect(find.widgetWithText(ShadButton, 'AI 코치에게 질문'), findsOneWidget);
      // 카드 헤더 액션은 Ghost다. 강조색 링크를 더하지 않는다(§17 강조색 4곳).
      expect(
        tester
            .widgetList<ShadButton>(find.byType(ShadButton))
            .where((ShadButton b) => b.variant == ShadButtonVariant.link),
        isEmpty,
      );
      // 영양(식단 탭)과 오늘 운동 기록 두 카드에 있다.
      expect(find.byType(AppCardAction), findsNWidgets(2));
    });
  }

  testWidgets('header shows the goal only once the profile is loaded', (
    WidgetTester tester,
  ) async {
    _useViewport(tester, const Size(390, 844));
    for (final DashboardMockupState state in DashboardMockupState.values) {
      await tester.pumpWidget(
        MockupApp(
          key: UniqueKey(),
          initialRoute: '/dashboard?state=${state.name}&mode=light',
        ),
      );
      await _settle(tester);
      final bool loaded =
          state == DashboardMockupState.data ||
          state == DashboardMockupState.sparse;
      expect(
        find.text(loaded ? dashboardMockupSubtitle : dashboardMockupDate),
        findsOneWidget,
        reason: state.name,
      );
      expect(
        find.textContaining('체지방 감량'),
        loaded ? findsOneWidget : findsNothing,
        reason: state.name,
      );
    }
  });

  testWidgets('sparse shows guidance instead of a weight line', (
    WidgetTester tester,
  ) async {
    _useViewport(tester, const Size(390, 844));
    await tester.pumpWidget(
      const MockupApp(initialRoute: '/dashboard?state=sparse&mode=light'),
    );
    await _settle(tester);
    expect(find.text(TrendLineChart.sparseMessage), findsOneWidget);
    expect(find.text('오늘 운동 기록이 없습니다'), findsOneWidget);
    expect(find.text('운동 0일'), findsOneWidget);
  });

  group('MockupRoute.parse', () {
    test('reads state and mode from the query', () {
      expect(
        MockupRoute.parse('/dashboard?state=sparse&mode=dark'),
        const MockupRoute(
          page: MockupPage.dashboard,
          state: DashboardMockupState.sparse,
          mode: ThemeMode.dark,
        ),
      );
      for (final DashboardMockupState s in DashboardMockupState.values) {
        for (final ThemeMode m in ThemeMode.values) {
          final MockupRoute route = MockupRoute(
            page: MockupPage.dashboard,
            state: s,
            mode: m,
          );
          expect(MockupRoute.parse(route.location), route);
        }
      }
    });

    test('falls back to defaults and rejects unknown paths', () {
      expect(
        MockupRoute.parse('/dashboard'),
        const MockupRoute(page: MockupPage.dashboard),
      );
      expect(
        MockupRoute.parse('/dashboard?theme=shadcn&mode=light')!.flavor,
        MockupThemeFlavor.shadcn,
      );
      expect(
        MockupRoute.parse('/dashboard?theme=material')!.flavor,
        MockupThemeFlavor.app,
      );
      expect(
        MockupRoute.parse('/dashboard?state=bogus&mode=sepia'),
        const MockupRoute(page: MockupPage.dashboard),
      );
      expect(
        MockupRoute.parse('/'),
        const MockupRoute(page: MockupPage.gallery),
      );
      expect(
        MockupRoute.parse(''),
        const MockupRoute(page: MockupPage.gallery),
      );
      expect(
        MockupRoute.parse('/tokens?mode=light'),
        const MockupRoute(page: MockupPage.tokens, mode: ThemeMode.light),
      );
      expect(MockupRoute.parse('/nope'), isNull);
    });
  });

  testWidgets('system mode follows platform brightness', (
    WidgetTester tester,
  ) async {
    _useViewport(tester, const Size(390, 844));
    tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);
    await tester.pumpWidget(
      const MockupApp(initialRoute: '/dashboard?state=data&mode=system'),
    );
    await _settle(tester);
    final BuildContext context = tester.element(
      find.byType(DashboardMockupScreen),
    );
    expect(ShadTheme.of(context).brightness, Brightness.dark);
  });

  testWidgets('gallery opens tokens and a dashboard state', (
    WidgetTester tester,
  ) async {
    _useViewport(tester, const Size(390, 844));
    await tester.pumpWidget(const MockupApp(initialRoute: '/'));
    await _settle(tester);
    expect(find.text('Design Mockups'), findsOneWidget);

    await tester.tap(find.text('Dark'));
    await _settle(tester);

    await tester.tap(find.text('Dashboard · sparse'));
    await _settle(tester);
    final DashboardMockupScreen screen = tester.widget(
      find.byType(DashboardMockupScreen),
    );
    expect(screen.state, DashboardMockupState.sparse);
    expect(
      ShadTheme.of(
        tester.element(find.byType(DashboardMockupScreen)),
      ).brightness,
      Brightness.dark,
    );

    await tester.pumpWidget(
      MockupApp(key: UniqueKey(), initialRoute: '/tokens'),
    );
    await _settle(tester);
    expect(find.byType(ThemePreviewScreen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
