import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_tokens.dart';
import 'package:frontend/dev/theme_preview/theme_preview_app.dart';
import 'package:frontend/dev/theme_preview/theme_preview_screen.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

const List<String> _sectionTitles = <String>[
  'Surfaces',
  'Actions',
  'Text',
  'Border · Input · Ring',
  'Status',
  'Typography',
  'Buttons',
  'Inputs',
  'Cards',
  'Badges',
  'Progress',
  'Chart',
  'Radius',
  'Spacing',
];

// 로딩 버튼 인디케이터가 계속 돌아서 pumpAndSettle 대신 고정 시간만큼 진행한다.
Future<void> _settle(WidgetTester tester) async {
  for (int i = 0; i < 5; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  for (final (ThemeMode mode, String applied) in <(ThemeMode, String)>[
    (ThemeMode.light, 'Light'),
    (ThemeMode.dark, 'Dark'),
  ]) {
    testWidgets('theme preview renders every section in $applied at 390x844', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(ThemePreviewApp(initialMode: mode));
      await _settle(tester);
      expect(tester.takeException(), isNull);

      expect(find.text('Theme Preview'), findsOneWidget);
      expect(find.text('적용된 밝기: $applied'), findsOneWidget);

      final Rect viewport = tester.getRect(
        find.byKey(ThemePreviewScreen.scrollKey),
      );
      for (final String title in _sectionTitles) {
        final Finder finder = find.text(title);
        expect(finder, findsOneWidget, reason: title);
        await tester.ensureVisible(finder);
        await tester.pump();
        final Rect rect = tester.getRect(finder);
        expect(viewport.contains(rect.center), isTrue, reason: title);
        expect(tester.takeException(), isNull, reason: title);
      }

      // Inputs 섹션의 검증 실패 문구가 화면에 보인다.
      expect(find.text('100~250 사이로 입력하세요.'), findsOneWidget);

      // 끝까지 스크롤한다.
      await tester.drag(
        find.byKey(ThemePreviewScreen.scrollKey),
        const Offset(0, -30000),
      );
      await _settle(tester);
      expect(find.text('s48'), findsOneWidget);
      expect(
        viewport.contains(tester.getRect(find.text('s48')).center),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('mode selector switches applied brightness', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const ThemePreviewApp(initialMode: ThemeMode.light),
    );
    await _settle(tester);
    expect(find.text('적용된 밝기: Light'), findsOneWidget);

    await tester.tap(find.text('Dark'));
    await _settle(tester);
    expect(find.text('적용된 밝기: Dark'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('select fills the field width and icon buttons are 48', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const ThemePreviewApp(initialMode: ThemeMode.light),
    );
    await _settle(tester);

    final Finder iconButton = find.byType(ShadIconButton).first;
    await tester.ensureVisible(iconButton);
    await tester.pump();
    expect(tester.getSize(iconButton), const Size(48, 48));

    final Finder select = find.byType(ShadSelect<String>);
    await tester.ensureVisible(select);
    await tester.pump();
    // 같은 카드의 입력 칸과 좌우 끝이 같아야 한다(§10). 고치기 전에는 내용 폭(약 113)이었다.
    final Rect selectRect = tester.getRect(select);
    final Rect inputRect = tester.getRect(find.byType(ShadInput).last);
    expect(selectRect.left, inputRect.left);
    expect(selectRect.right, inputRect.right);
    expect(tester.takeException(), isNull);
  });

  // 은은한 면이 배경·카드와 같으면 트랙·Secondary 버튼·눌림 효과가 보이지 않는다(§3-2).
  for (final (String name, AppColorTokens t) in <(String, AppColorTokens)>[
    ('light', AppColorTokens.light),
    ('dark', AppColorTokens.dark),
  ]) {
    test('$name subtle surfaces stand apart from background and card', () {
      for (final (String surface, Color color) in <(String, Color)>[
        ('muted', t.muted),
        ('secondary', t.secondary),
        ('accent', t.accent),
      ]) {
        for (final (String base, Color baseColor) in <(String, Color)>[
          ('background', t.background),
          ('card', t.card),
        ]) {
          final double ratio = AppContrast.ratio(color, baseColor);
          expect(
            ratio,
            greaterThanOrEqualTo(1.1),
            reason: '$name $surface/$base $ratio',
          );
        }
      }
    });
  }

  group('token contrast (WCAG 2.x)', () {
    for (final (String name, AppColorTokens t) in <(String, AppColorTokens)>[
      ('light', AppColorTokens.light),
      ('dark', AppColorTokens.dark),
    ]) {
      test('$name text pairs meet 4.5:1', () {
        final Map<String, (Color, Color)> pairs = <String, (Color, Color)>{
          'foreground/background': (t.foreground, t.background),
          'mutedForeground/background': (t.mutedForeground, t.background),
          'mutedForeground/card': (t.mutedForeground, t.card),
          'primary/card': (t.primary, t.card),
          'primaryForeground/primary': (t.primaryForeground, t.primary),
          'destructiveForeground/destructive': (
            t.destructiveForeground,
            t.destructive,
          ),
          'error/card': (t.error, t.card),
          'mutedForeground/muted': (t.mutedForeground, t.muted),
          'secondaryForeground/secondary': (
            t.secondaryForeground,
            t.secondary,
          ),
          'accentForeground/accent': (t.accentForeground, t.accent),
          'success/card': (t.success, t.card),
          'warning/card': (t.warning, t.card),
          'info/card': (t.info, t.card),
        };
        pairs.forEach((String pair, (Color, Color) c) {
          final double ratio = AppContrast.ratio(c.$1, c.$2);
          expect(
            ratio,
            greaterThanOrEqualTo(4.5),
            reason: '$name $pair $ratio',
          );
        });
      });

      test('$name input and chart colors meet 3:1 on card', () {
        final double input = AppContrast.ratio(t.input, t.card);
        expect(input, greaterThanOrEqualTo(3.0), reason: '$name input $input');
        for (final (String series, Color color) in t.chartEntries) {
          final double ratio = AppContrast.ratio(color, t.card);
          expect(
            ratio,
            greaterThanOrEqualTo(3.0),
            reason: '$name $series $ratio',
          );
        }
      });
    }
  });
}
