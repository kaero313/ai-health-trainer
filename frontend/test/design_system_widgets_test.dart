// 새 디자인 시스템 템플릿 위젯(lib/shared/design_system/) 단위 테스트.
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_shad_theme.dart';
import 'package:frontend/shared/design_system/design_system.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// ShadTheme + Material 뼈대. [bottomPadding]은 하단 safe area(홈 인디케이터 등)를 흉내 낸다.
Widget _host(
  Widget child, {
  Brightness brightness = Brightness.light,
  double bottomPadding = 0,
}) {
  final ShadThemeData theme = brightness == Brightness.dark
      ? AppShadTheme.dark()
      : AppShadTheme.light();
  return MaterialApp(
    home: Builder(
      builder: (BuildContext context) => MediaQuery(
        data: MediaQuery.of(
          context,
        ).copyWith(padding: EdgeInsets.only(bottom: bottomPadding)),
        child: ShadTheme(
          data: theme,
          child: Scaffold(body: child),
        ),
      ),
    ),
  );
}

const List<AppBottomNavItem> _tabs = <AppBottomNavItem>[
  AppBottomNavItem(icon: LucideIcons.house, label: '홈'),
  AppBottomNavItem(icon: LucideIcons.chartLine, label: '통계'),
  AppBottomNavItem(icon: LucideIcons.dumbbell, label: '플랜'),
  AppBottomNavItem(icon: LucideIcons.utensils, label: '식단'),
  AppBottomNavItem(icon: LucideIcons.scanLine, label: '스캔'),
];

Color? _iconColor(WidgetTester tester, int index) {
  return tester
      .widget<Icon>(
        find.descendant(
          of: find.byKey(AppBottomNav.itemKey(index)),
          matching: find.byType(Icon),
        ),
      )
      .color;
}

void main() {
  group('AppBottomNav', () {
    for (final double inset in <double>[0, 34]) {
      testWidgets('bar grows by bottom safe area $inset, items stay in 64', (
        WidgetTester tester,
      ) async {
        int? tapped;
        await tester.binding.setSurfaceSize(const Size(390, 844));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          _host(
            Align(
              alignment: Alignment.bottomCenter,
              child: AppBottomNav(
                items: _tabs,
                selectedIndex: 0,
                onSelected: (int i) => tapped = i,
              ),
            ),
            bottomPadding: inset,
          ),
        );
        await tester.pump(const Duration(milliseconds: 200));

        final Rect bar = tester.getRect(find.byType(AppBottomNav));
        expect(bar.height, AppBottomNav.contentHeight + inset);
        expect(bar.width, 390);

        final List<double> widths = <double>[];
        for (int i = 0; i < _tabs.length; i++) {
          final Rect item = tester.getRect(find.byKey(AppBottomNav.itemKey(i)));
          // 항목(누르는 영역)은 바 위쪽 64 안에 있고, safe area로 내려가지 않는다.
          expect(item.top, bar.top);
          expect(item.bottom, bar.top + AppBottomNav.contentHeight);
          expect(item.height, greaterThanOrEqualTo(48));
          widths.add(item.width);
        }
        expect(widths.toSet().length, 1, reason: '항목 5개는 같은 폭');

        final ShadColorScheme cs = AppShadTheme.light().colorScheme;
        expect(_iconColor(tester, 0), cs.primary);
        for (int i = 1; i < _tabs.length; i++) {
          expect(_iconColor(tester, i), cs.mutedForeground);
        }

        await tester.tap(find.text('식단'));
        expect(tapped, 3);
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('selected item exposes selected semantics', (
      WidgetTester tester,
    ) async {
      final SemanticsHandle handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _host(AppBottomNav(items: _tabs, selectedIndex: 1, onSelected: (_) {})),
      );
      expect(
        tester.getSemantics(find.byKey(AppBottomNav.itemKey(1))),
        matchesSemantics(
          label: '통계 탭, 5개 중 2번째',
          isButton: true,
          isSelected: true,
          hasSelectedState: true,
          hasTapAction: true,
        ),
      );
      handle.dispose();
    });
  });

  group('ProgressRing', () {
    test('clamps the drawn value to 0~1 and reports overflow', () {
      const ProgressRing over = ProgressRing(value: 1.4, label: '열량 목표');
      expect(over.clampedValue, 1.0);
      expect(over.overflow, closeTo(0.4, 1e-9));
      expect(over.isOver, isTrue);
      expect(over.effectiveValueText, '140%');

      const ProgressRing under = ProgressRing(value: -0.2, label: '열량 목표');
      expect(under.clampedValue, 0.0);
      expect(under.overflow, 0);
      expect(under.effectiveValueText, '0%');

      const ProgressRing normal = ProgressRing(value: 0.57, label: '열량 목표');
      expect(normal.clampedValue, 0.57);
      expect(normal.isOver, isFalse);
      expect(normal.effectiveValueText, '57%');
    });

    testWidgets('renders the unclamped percent in the center', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _host(const ProgressRing(value: 1.15, label: '열량 목표')),
      );
      expect(find.text('115%'), findsOneWidget);
      expect(find.text('열량 목표'), findsOneWidget);
      expect(tester.getSize(find.byType(ProgressRing)), const Size(112, 112));
      expect(tester.takeException(), isNull);
    });
  });

  group('TrendLineChart', () {
    for (final List<double> values in <List<double>>[
      <double>[],
      <double>[72.4],
    ]) {
      testWidgets('shows the guidance text with ${values.length} points', (
        WidgetTester tester,
      ) async {
        await tester.pumpWidget(
          _host(
            TrendLineChart(
              series: <TrendSeries>[
                TrendSeries(
                  label: '체중',
                  color: const Color(0xFF0891B2),
                  values: values,
                ),
              ],
              xLabels: const <String>['10/4'],
            ),
          ),
        );
        expect(find.text(TrendLineChart.sparseMessage), findsOneWidget);
        expect(find.byType(LineChart), findsNothing);
      });
    }

    testWidgets('draws a line chart with 2+ points and a legend for 2 series', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const TrendLineChart(
            series: <TrendSeries>[
              TrendSeries(
                label: '단백질',
                color: Color(0xFF7C3AED),
                values: <double>[72, 80, 65],
              ),
              TrendSeries(
                label: '지방',
                color: Color(0xFFDB2777),
                values: <double>[40, 52, 38],
              ),
            ],
            xLabels: <String>['9/20', '9/21', '9/22'],
          ),
        ),
      );
      await tester.pump();
      expect(find.text(TrendLineChart.sparseMessage), findsNothing);
      expect(find.byType(LineChart), findsOneWidget);
      expect(find.byType(AppLegendDot), findsNWidgets(2));
      expect(tester.takeException(), isNull);
    });

    test('scale puts min, mid and max on nice values', () {
      final TrendScale weight = TrendScale.fit(72.4, 73.6);
      expect(weight.min, 72);
      expect(weight.max, 74);
      expect(weight.step, 1);
      expect(weight.format(73), '73');

      final TrendScale kcal = TrendScale.fit(1185, 2240);
      expect(kcal.min, lessThanOrEqualTo(1185));
      expect(kcal.max, greaterThanOrEqualTo(2240));
      expect(kcal.format(2000), '2,000');
    });
  });

  testWidgets('WeekConsistency labels each day for screen readers', (
    WidgetTester tester,
  ) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        const WeekConsistency(
          days: <WeekDayStatus>[
            WeekDayStatus(
              label: '수',
              fullName: '수요일',
              exercise: DayMark.done,
              diet: DayMark.done,
            ),
            WeekDayStatus(
              label: '토',
              fullName: '토요일',
              exercise: DayMark.missed,
              diet: DayMark.done,
              isToday: true,
            ),
            WeekDayStatus(
              label: '일',
              fullName: '일요일',
              exercise: DayMark.future,
              diet: DayMark.future,
            ),
          ],
        ),
      ),
    );
    expect(find.bySemanticsLabel('수요일, 운동 기록 있음, 식단 기록 있음'), findsOneWidget);
    expect(find.bySemanticsLabel('토요일 오늘, 운동 기록 없음, 식단 기록 있음'), findsOneWidget);
    expect(
      find.bySemanticsLabel('일요일, 운동 아직 지나지 않음, 식단 아직 지나지 않음'),
      findsOneWidget,
    );
    // 범례가 색 점과 함께 일수를 글자로 보인다.
    expect(find.text('운동 1일'), findsOneWidget);
    expect(find.text('식단 2일'), findsOneWidget);
    handle.dispose();
  });

  testWidgets('WeekConsistency draws no dot for future days', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const WeekConsistency(
          days: <WeekDayStatus>[
            WeekDayStatus(
              label: '토',
              fullName: '토요일',
              exercise: DayMark.done,
              diet: DayMark.missed,
              isToday: true,
            ),
            WeekDayStatus(
              label: '일',
              fullName: '일요일',
              exercise: DayMark.future,
              diet: DayMark.future,
            ),
          ],
        ),
      ),
    );
    bool isCircle(Widget w) =>
        w is Container &&
        w.decoration is BoxDecoration &&
        (w.decoration! as BoxDecoration).shape == BoxShape.circle;
    // 범례 점 2 + 토요일 점 2. 일요일은 점이 없다.
    expect(find.byWidgetPredicate(isCircle), findsNWidgets(4));
    final Text sunday = tester.widget<Text>(find.text('일'));
    expect(
      sunday.style!.color,
      AppShadTheme.light().colorScheme.mutedForeground,
    );
    // 점이 없어도 칸은 남아 요일 라벨 높이가 같다.
    expect(
      tester.getTopLeft(find.text('일')).dy,
      tester.getTopLeft(find.text('토')).dy,
    );
  });

  testWidgets('badge padding 8/4 comes from the theme', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              AppBadge.neutral(label: '운동 1일 연속', icon: LucideIcons.flame),
              AppBadge.status(tone: AppBadgeTone.success, label: '달성'),
              AppBadge.outline(label: '외곽선'),
            ],
          ),
        ),
      ),
    );
    // 호출부에서 여백을 덮어쓰지 않는다.
    for (final ShadBadge b in tester.widgetList<ShadBadge>(
      find.byType(ShadBadge),
    )) {
      expect(b.padding, isNull);
    }
    final ShadThemeData theme = AppShadTheme.light();
    for (final ShadBadgeTheme t in <ShadBadgeTheme>[
      theme.primaryBadgeTheme,
      theme.secondaryBadgeTheme,
      theme.destructiveBadgeTheme,
      theme.outlineBadgeTheme,
    ]) {
      expect(t.padding, AppShadTheme.badgePadding);
    }
    // 아이콘 16 + 위아래 4 = 24
    expect(tester.getSize(find.byType(AppBadge).at(0)).height, 24);
    expect(tester.getSize(find.byType(AppBadge).at(1)).height, 24);
  });

  group('AppCardAction', () {
    testWidgets('is a foreground ghost button 40 tall with a 48 tap area', (
      WidgetTester tester,
    ) async {
      int taps = 0;
      await tester.pumpWidget(
        _host(
          Center(
            child: AppCardAction(label: '보기', onPressed: () => taps++),
          ),
        ),
      );
      final Finder button = find.byType(ShadButton);
      expect(
        tester.widget<ShadButton>(button).variant,
        ShadButtonVariant.ghost,
      );
      expect(tester.getSize(button).height, AppCardAction.visualHeight);
      expect(
        tester.getSize(find.byType(AppCardAction)).height,
        AppCardAction.hitHeight,
      );
      final RenderParagraph label = tester.renderObject(find.text('보기'));
      expect(
        label.text.style!.color,
        AppShadTheme.light().colorScheme.foreground,
      );

      final Rect visible = tester.getRect(button);
      await tester.tap(button);
      expect(taps, 1);
      // 보이는 버튼 위아래 3px도 눌린다.
      await tester.tapAt(Offset(visible.center.dx, visible.top - 3));
      await tester.tapAt(Offset(visible.center.dx, visible.bottom + 3));
      expect(taps, 3);
    });

    testWidgets('AppCard keeps a 40 header look around the 48 tap area', (
      WidgetTester tester,
    ) async {
      const Key body = ValueKey<String>('body');
      await tester.pumpWidget(
        _host(
          AppCard(
            title: '오늘 운동 기록',
            trailing: AppCardAction(label: '보기', onPressed: () {}),
            children: const <Widget>[SizedBox(key: body, height: 10)],
          ),
        ),
      );
      const double border = 1;
      final Rect card = tester.getRect(find.byType(ShadCard));
      final Rect visible = tester.getRect(find.byType(ShadButton));
      final Rect hit = tester.getRect(find.byType(AppCardAction));
      final Rect content = tester.getRect(find.byKey(body));
      // 보이는 버튼은 여백 16 안쪽에서 시작하고 본문과 16 떨어진다.
      expect(visible.top - card.top, AppCard.padding + border);
      expect(content.top - visible.bottom, 16);
      // 누르는 영역만 여백 쪽으로 4 넘친다.
      expect(hit.top, visible.top - AppCardAction.hitOverflow);
      expect(hit.bottom, visible.bottom + AppCardAction.hitOverflow);
    });
  });

  for (final (bool emphasis, double inset) in <(bool, double)>[
    (false, 16),
    (true, 20),
  ]) {
    testWidgets('AppCard emphasis=$emphasis uses $inset padding', (
      WidgetTester tester,
    ) async {
      const Key body = ValueKey<String>('body');
      await tester.pumpWidget(
        _host(
          AppCard(
            emphasis: emphasis,
            children: const <Widget>[SizedBox(key: body, height: 10)],
          ),
        ),
      );
      final Rect card = tester.getRect(find.byType(ShadCard));
      final Rect content = tester.getRect(find.byKey(body));
      // 1px 외곽선은 여백 바깥에 더해진다(Container·CSS border-box와 같다).
      const double border = 1;
      expect(content.left - card.left, inset + border);
      expect(content.top - card.top, inset + border);
      expect(card.right - content.right, inset + border);
    });
  }

  testWidgets('AppHeader.detail back button is a 48 tappable labelled button', (
    WidgetTester tester,
  ) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    int backs = 0;
    await tester.pumpWidget(
      _host(AppHeader.detail(title: '월간 리포트', onBack: () => backs++)),
    );
    final Finder back = find.byType(ShadIconButton);
    expect(tester.getSize(back), const Size(48, 48));
    expect(
      tester.getSemantics(back),
      matchesSemantics(label: '뒤로', isButton: true, hasTapAction: true),
    );
    await tester.tap(back);
    expect(backs, 1);
    handle.dispose();
  });

  test('formatNumber adds thousands separators', () {
    expect(formatNumber(1185), '1,185');
    expect(formatNumber(2085), '2,085');
    expect(formatNumber(1234567), '1,234,567');
    expect(formatNumber(72.4, decimals: 1), '72.4');
    expect(formatNumber(-1.1, decimals: 1), '-1.1');
    expect(formatNumber(130), '130');
  });
}
