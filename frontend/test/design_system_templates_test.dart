// 화면 전환용 공통 템플릿(하단 저장 바, 섹션 제목, 리스트, 선택 칸, 수치 타일) 테스트.
// 모두 Light·Dark에서 한 번씩 돈다.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_shad_theme.dart';
import 'package:frontend/core/design_system/app_text_styles.dart';
import 'package:frontend/core/design_system/keep_all.dart';
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

  group('AppTextField', () {
    testWidgetsInBothModes('label stays visible and the field is 48 tall', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 600));
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                AppTextField(label: '키', placeholder: '175', unit: 'cm'),
              ],
            ),
          ),
          brightness: b,
        ),
      );
      final ShadColorScheme cs = colorsFor(b);
      expect(find.text('키'), findsOneWidget);
      expect(_textColor(tester, 'cm'), cs.mutedForeground);
      expect(tester.getSize(find.byType(ShadInput)).height, 48);
    });

    testWidgetsInBothModes('an action button keeps the height at 48', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 600));
      int taps = 0;
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                AppTextField(
                  label: '비밀번호',
                  obscureText: true,
                  action: AppTextFieldAction(
                    icon: LucideIcons.eye,
                    semanticLabel: '비밀번호 표시',
                    onPressed: () => taps++,
                  ),
                ),
              ],
            ),
          ),
          brightness: b,
        ),
      );
      expect(tester.getSize(find.byType(ShadInput)).height, 48);
      final Finder action = find.bySemanticsLabel('비밀번호 표시');
      expect(action, findsOneWidget);
      // 아이콘(20)에서 떨어진 46 칸 가장자리도 눌린다.
      final Offset icon = tester.getCenter(find.byIcon(LucideIcons.eye));
      await tester.tapAt(icon + const Offset(-20, 0));
      expect(taps, 1);
      await tester.tap(find.byIcon(LucideIcons.eye));
      expect(taps, 2);
    });

    testWidgetsInBothModes('error shows border, message and icon', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 600));
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                AppTextField(
                  label: '이메일',
                  description: '로그인에 쓰는 주소',
                  errorText: '올바른 이메일 형식을 입력해 주세요.',
                ),
              ],
            ),
          ),
          brightness: b,
        ),
      );
      final ShadColorScheme cs = colorsFor(b);
      expect(_textColor(tester, '올바른 이메일 형식을 입력해 주세요.'), cs.error);
      expect(find.byIcon(LucideIcons.circleX), findsOneWidget);
      // 오류가 있으면 도움말 대신 오류가 보인다.
      expect(find.text('로그인에 쓰는 주소'), findsNothing);
    });
  });

  group('DateStepper', () {
    testWidgetsInBothModes('arrows are 48 buttons and null disables one side', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 400));
      final SemanticsHandle handle = tester.ensureSemantics();
      int prev = 0;
      int picks = 0;
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            DateStepper(
              label: '2026년 11월',
              caption: '이번 달',
              onPrevious: () => prev++,
              onNext: null,
              onTapLabel: () => picks++,
              previousLabel: '이전 달',
              nextLabel: '다음 달',
            ),
          ),
          brightness: b,
        ),
      );
      final ShadColorScheme cs = colorsFor(b);
      expect(_textColor(tester, '2026년 11월'), cs.foreground);
      final Finder buttons = find.byType(ShadIconButton);
      expect(buttons, findsNWidgets(2));
      for (final Element e in buttons.evaluate()) {
        expect(
          tester.getSize(find.byElementPredicate((Element x) => x == e)),
          const Size(48, 48),
        );
      }
      expect(
        tester.getSemantics(find.bySemanticsLabel('다음 달')),
        matchesSemantics(label: '다음 달', isButton: true, hasEnabledState: true),
      );
      expect(
        tester.getSemantics(find.bySemanticsLabel('이번 달 2026년 11월')),
        matchesSemantics(
          label: '이번 달 2026년 11월',
          hint: '날짜 선택',
          isButton: true,
          hasTapAction: true,
        ),
      );
      await tester.tap(find.bySemanticsLabel('이전 달'));
      await tester.tap(find.text('2026년 11월'));
      expect(prev, 1);
      expect(picks, 1);
      handle.dispose();
    });
  });

  group('FilterChipBar', () {
    testWidgetsInBothModes(
      'selected chip uses primaryMuted and reports value',
      (WidgetTester tester, Brightness b) async {
        useViewport(tester, const Size(390, 400));
        String? chosen = 'chest';
        await pumpHost(
          tester,
          designSystemHost(
            _page(
              StatefulBuilder(
                builder: (BuildContext context, StateSetter setState) =>
                    FilterChipBar<String>(
                      items: const <FilterChipItem<String>>[
                        FilterChipItem<String>(value: null, label: '전체'),
                        FilterChipItem<String>(value: 'chest', label: '가슴'),
                        FilterChipItem<String>(value: 'back', label: '등'),
                      ],
                      selected: chosen,
                      onSelected: (String? v) => setState(() => chosen = v),
                    ),
              ),
            ),
            brightness: b,
          ),
        );
        final ShadColorScheme cs = colorsFor(b);
        expect(_textColor(tester, '가슴'), cs.primary);
        expect(_textColor(tester, '등'), cs.foreground);
        expect(
          tester.getSize(find.byType(FilterChipBar<String>)).height,
          FilterChipBar.hitHeight,
        );
        final SemanticsHandle handle = tester.ensureSemantics();
        expect(
          tester.getSemantics(find.bySemanticsLabel('등')),
          matchesSemantics(
            label: '등',
            isButton: true,
            hasSelectedState: true,
            hasTapAction: true,
          ),
        );
        handle.dispose();
        await tester.tap(find.text('전체'));
        await tester.pump();
        expect(chosen, isNull);
        expect(_textColor(tester, '전체'), cs.primary);
      },
    );
  });

  group('SourceList', () {
    testWidgetsInBothModes('shows sources, folds extras and says when empty', (
      WidgetTester tester,
      Brightness b,
    ) async {
      useViewport(tester, const Size(390, 500));
      final SemanticsHandle handle = tester.ensureSemantics();
      await pumpHost(
        tester,
        designSystemHost(
          _page(
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                SourceList(
                  sources: <String>['영양 가이드', '근력 운동 지침', '수면 연구', '단백질 권장량'],
                  maxVisible: 3,
                ),
                SizedBox(height: 24),
                SourceList(sources: <String>[]),
              ],
            ),
          ),
          brightness: b,
        ),
      );
      expect(find.text('영양 가이드'), findsOneWidget);
      expect(find.text('단백질 권장량'), findsNothing);
      expect(find.bySemanticsLabel('출처 1개 더 있음'), findsOneWidget);
      expect(find.text('확인된 출처가 없습니다'), findsOneWidget);
      // 출처는 정보라 강조색을 쓰지 않는다.
      for (final Text t in tester.widgetList<Text>(find.text('검증된 출처'))) {
        expect(t.style?.color, isNot(colorsFor(b).primary));
      }
      handle.dispose();
    });
  });

  testWidgets('EmptyState reads keepAll text as the plain sentence', (
    WidgetTester tester,
  ) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    const String description = '체중을 입력하면 통계를 볼 수 있습니다.';
    await pumpHost(
      tester,
      designSystemHost(
        _page(
          EmptyState(
            icon: LucideIcons.userRound,
            title: '프로필 설정이 필요합니다',
            description: keepAll(description),
          ),
        ),
      ),
    );
    expect(find.bySemanticsLabel(description), findsOneWidget);
    expect(find.text(keepAll(description)), findsOneWidget);
    handle.dispose();
  });

  testWidgetsInBothModes('null callbacks render disabled buttons', (
    WidgetTester tester,
    Brightness b,
  ) async {
    useViewport(tester, const Size(390, 700));
    await pumpHost(
      tester,
      designSystemHost(
        _page(
          const Column(
            children: <Widget>[
              DateStepper(label: '2026년 11월', onPrevious: null, onNext: null),
              ErrorState(title: '불러오지 못했습니다'),
            ],
          ),
          bottom: const AppBottomActionBar(label: '저장하기', onPressed: null),
        ),
        brightness: b,
      ),
    );
    for (final ShadIconButton button in tester.widgetList<ShadIconButton>(
      find.byType(ShadIconButton),
    )) {
      expect(button.enabled, isFalse);
    }
    for (final ShadButton button in tester.widgetList<ShadButton>(
      find.byType(ShadButton),
    )) {
      expect(button.enabled, isFalse);
    }
  });

  group('keepAll', () {
    test('joins letters inside words and keeps the spaces', () {
      const String joiner = '⁠';
      expect(keepAll('됐습니다'), '됐$joiner습$joiner니$joiner다');
      expect(keepAll('준비가 됐습니다').split(' ').length, 2);
      expect(keepAll('준비가  됐습니다').replaceAll(joiner, ''), '준비가  됐습니다');
      expect(keepAll(''), '');
    });

    test('a long heading breaks only at spaces', () {
      const String title = '코칭을 시작할 준비가 됐습니다';
      List<int> lineEnds(String text) {
        final TextPainter tp = TextPainter(
          text: TextSpan(text: text, style: AppTextStyles.display),
          textDirection: TextDirection.ltr,
          // 테스트 글꼴은 글자마다 1em(28)이다. 370이면 마지막 단어의 첫 음절까지 첫 줄에 들어간다.
        )..layout(maxWidth: 370);
        final List<int> ends = <int>[];
        int offset = 0;
        while (true) {
          final TextRange line = tp.getLineBoundary(
            TextPosition(offset: offset),
          );
          if (line.end >= text.length || line.end <= offset) break;
          ends.add(line.end);
          offset = line.end;
        }
        tp.dispose();
        return ends;
      }

      bool atSpace(String text, int end) =>
          text[end - 1] == ' ' || text[end] == ' ';

      // 그냥 두면 음절 사이에서 줄이 바뀐다(이 검사가 의미 있다는 확인).
      final List<int> plain = lineEnds(title);
      expect(plain, isNotEmpty);
      expect(plain.any((int e) => !atSpace(title, e)), isTrue);
      // keepAll이면 줄은 공백에서만 바뀐다.
      final String kept = keepAll(title);
      final List<int> ends = lineEnds(kept);
      expect(ends, isNotEmpty);
      for (final int e in ends) {
        expect(atSpace(kept, e), isTrue);
      }
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
