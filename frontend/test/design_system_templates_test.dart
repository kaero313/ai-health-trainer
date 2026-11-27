// 화면 전환용 공통 템플릿(하단 저장 바, 섹션 제목, 리스트, 선택 칸, 수치 타일) 테스트.
// 모두 Light·Dark에서 한 번씩 돈다.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_shad_theme.dart';
import 'package:frontend/shared/design_system/design_system.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'support/design_system_host.dart';

Widget _page(Widget child, {Widget? bottom}) => Scaffold(
  body: SafeArea(
    child: Padding(padding: const EdgeInsets.all(20), child: child),
  ),
  bottomNavigationBar: bottom,
);

Color? _textColor(WidgetTester tester, String text) =>
    tester.widget<Text>(find.text(text)).style?.color;

void main() {
  group('AppBottomActionBar', () {
    testWidgetsInBothModes('full-width 48 primary above the safe area', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(360, 640), bottomInset: 34);
      int taps = 0;
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const SizedBox(),
            bottom: AppBottomActionBar(label: '저장하기', onPressed: () => taps++),
          ),
          brightness: b,
        ),
      );
      final Finder button = find.byType(ShadButton);
      final Rect rect = tester.getRect(button);
      expect(rect.height, 48);
      // 좌우 페이지 여백 20
      expect(rect.left, 20);
      expect(rect.right, 340);
      // 버튼 아래 12 + safe area 34
      expect(640 - rect.bottom, 12 + 34);
      expect(
        tester.widget<ShadButton>(button).variant,
        ShadButtonVariant.primary,
      );
      await tester.tap(find.text('저장하기'));
      expect(taps, 1);
    });

    testWidgetsInBothModes('error line uses the error token and an icon', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(360, 640));
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const SizedBox(),
            bottom: AppBottomActionBar(
              label: '저장하기',
              onPressed: () {},
              errorText: '필수 항목을 입력하세요',
            ),
          ),
          brightness: b,
        ),
      );
      expect(_textColor(tester, '필수 항목을 입력하세요'), colorsFor(b).error);
      expect(find.byIcon(LucideIcons.circleX), findsOneWidget);
      // 오류 문구는 버튼 위에 있다.
      expect(
        tester.getRect(find.text('필수 항목을 입력하세요')).bottom,
        lessThan(tester.getRect(find.byType(ShadButton)).top),
      );
    });

    testWidgetsInBothModes('loading keeps the width and ignores taps', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(360, 640));
      int taps = 0;
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const SizedBox(),
            bottom: AppBottomActionBar(
              label: '저장하기',
              loading: true,
              onPressed: () => taps++,
            ),
          ),
          brightness: b,
        ),
      );
      expect(find.text('저장하기'), findsNothing);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(tester.getSize(find.byType(ShadButton)).width, 320);
      expect(find.bySemanticsLabel('저장하기 중'), findsOneWidget);
      await tester.tap(find.byType(ShadButton));
      expect(taps, 0);
    });
  });

  group('SectionHeader', () {
    testWidgetsInBothModes(
      'heading with a link action that has a 48 tap area',
      (WidgetTester tester, Brightness b) async {
        useViewport(tester, const Size(390, 400));
        int taps = 0;
        await pumpHost(
          tester,
          designSystemHost(
            _page(
              SectionHeader(
                title: '식사 타임라인',
                actionLabel: '사진 분석',
                onAction: () => taps++,
              ),
            ),
            brightness: b,
          ),
        );
        expect(_textColor(tester, '식사 타임라인'), colorsFor(b).foreground);
        final Finder link = find.byType(ShadButton);
        expect(tester.widget<ShadButton>(link).variant, ShadButtonVariant.link);
        final Rect visible = tester.getRect(link);
        expect(visible.height, AppCardAction.visualHeight);
        await tester.tap(link);
        // 보이는 버튼 바로 위아래 3px도 눌린다.
        await tester.tapAt(Offset(visible.center.dx, visible.top - 3));
        await tester.tapAt(Offset(visible.center.dx, visible.bottom + 3));
        expect(taps, 3);
      },
    );

    testWidgetsInBothModes('title only has no button', (
      WidgetTester tester,
      Brightness b,
    ) async {
      await pumpHost(
        tester,
        designSystemHost(
          _page(const SectionHeader(title: '추천 음식')),
          brightness: b,
        ),
      );
      expect(find.text('추천 음식'), findsOneWidget);
      expect(find.byType(ShadButton), findsNothing);
    });
  });

  group('AppListCard and ListRow', () {
    testWidgetsInBothModes(
      'rows are divided and only tappable rows get a chevron',
      (WidgetTester tester, Brightness b) async {
        useViewport(tester, const Size(390, 600));
        final SemanticsHandle handle = tester.ensureSemantics();
        int taps = 0;
        await pumpHost(
          tester,
          designSystemHost(
            _page(
              AppListCard(
                title: '활력 지표',
                rows: <Widget>[
                  const ListRow(title: '심박', value: '기록 없음', valueMuted: true),
                  const ListRow(title: '체중', value: '72.4 kg'),
                  ListRow(
                    title: '식단 기준 관리',
                    icon: LucideIcons.salad,
                    onTap: () => taps++,
                  ),
                ],
              ),
            ),
            brightness: b,
          ),
        );
        final ShadColorScheme cs = colorsFor(b);
        expect(find.byType(Divider), findsNWidgets(2));
        expect(find.byIcon(LucideIcons.chevronRight), findsOneWidget);
        expect(_textColor(tester, '기록 없음'), cs.mutedForeground);
        expect(_textColor(tester, '72.4 kg'), cs.cardForeground);
        // 값이 있는 행은 "제목, 값"으로 읽힌다.
        expect(find.bySemanticsLabel('체중, 72.4 kg'), findsOneWidget);
        for (final Element row in find.byType(ListRow).evaluate()) {
          expect(
            tester
                .getSize(find.byElementPredicate((Element e) => e == row))
                .height,
            greaterThanOrEqualTo(ListRow.minHeight),
          );
        }
        await tester.tap(find.text('식단 기준 관리'));
        expect(taps, 1);
        handle.dispose();
      },
    );

    testWidgetsInBothModes('pressed row fills with accent immediately', (
      WidgetTester tester,
      Brightness b,
    ) async {
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            AppListCard(
              rows: <Widget>[ListRow(title: '월간 리포트', onTap: () {})],
            ),
          ),
          brightness: b,
        ),
      );
      final TestGesture g = await tester.startGesture(
        tester.getCenter(find.text('월간 리포트')),
      );
      await tester.pump();
      final ColoredBox fill = tester.widget<ColoredBox>(
        find
            .ancestor(
              of: find.text('월간 리포트'),
              matching: find.byType(ColoredBox),
            )
            .first,
      );
      expect(fill.color, colorsFor(b).accent);
      await g.up();
    });
  });

  group('AppSelectField', () {
    testWidgetsInBothModes('spans the parent width and reports the choice', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 700));
      String? chosen;
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                AppSelectField<String>(
                  label: '식사 유형',
                  initialValue: 'breakfast',
                  options: const <String, String>{
                    'breakfast': '아침',
                    'lunch': '점심',
                    'dinner': '저녁',
                  },
                  onChanged: (String? v) => chosen = v,
                ),
              ],
            ),
          ),
          brightness: b,
        ),
      );
      // 라벨은 항상 보이고, 선택 칸은 페이지 여백 안 전체 폭(350)이다.
      expect(find.text('식사 유형'), findsOneWidget);
      expect(tester.getSize(find.byType(ShadSelect<String>)).width, 350);

      await tester.tap(find.text('아침'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('저녁').last);
      await tester.pumpAndSettle();
      expect(chosen, 'dinner');
    });
  });

  group('MetricTile', () {
    testWidgetsInBothModes('shows the value with its unit', (
      WidgetTester tester,
      Brightness b,
    ) async {
      final SemanticsHandle handle = tester.ensureSemantics();
      await pumpHost(
        tester,
        designSystemHost(
          _page(const MetricTile(label: '현재 체중', value: '72.4', unit: 'kg')),
          brightness: b,
        ),
      );
      expect(_textColor(tester, '72.4'), colorsFor(b).cardForeground);
      expect(find.bySemanticsLabel('현재 체중 72.4 kg'), findsOneWidget);
      handle.dispose();
    });

    testWidgetsInBothModes('missing value shows -- and 기록 없음 in muted', (
      WidgetTester tester,
      Brightness b,
    ) async {
      await pumpHost(
        tester,
        designSystemHost(
          _page(const MetricTile(label: '체지방률', value: null, unit: '%')),
          brightness: b,
        ),
      );
      final ShadColorScheme cs = colorsFor(b);
      expect(_textColor(tester, '--'), cs.mutedForeground);
      expect(_textColor(tester, '기록 없음'), cs.mutedForeground);
      // 값이 없으면 단위를 보이지 않는다.
      expect(find.text('%'), findsNothing);
    });
  });

  test('templates read badge padding from the theme', () {
    // 공통 템플릿이 배지를 쓸 때도 테마 여백(§24)을 따른다.
    expect(
      AppShadTheme.light().secondaryBadgeTheme.padding,
      AppShadTheme.badgePadding,
    );
  });
}
