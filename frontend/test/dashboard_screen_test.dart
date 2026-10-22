// 실제 홈(DashboardScreen)과 API 응답 변환(dashboard_view_data.dart) 테스트.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/design_system/app_shad_theme.dart';
import 'package:frontend/core/router/main_shell.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/dashboard/data/dashboard_repository.dart';
import 'package:frontend/features/dashboard/domain/dashboard_controller.dart';
import 'package:frontend/features/dashboard/presentation/dashboard_screen.dart';
import 'package:frontend/features/dashboard/presentation/dashboard_view.dart';
import 'package:frontend/features/dashboard/presentation/dashboard_view_data.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/shared/design_system/design_system.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'support/fake_repositories.dart';

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-'
    '${d.day.toString().padLeft(2, '0')}';

DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

const Map<String, dynamic> _profile = <String, dynamic>{
  'weight_kg': 72.4,
  'goal': 'diet',
};

Map<String, dynamic> _today({
  num consumedKcal = 1185,
  bool withTarget = true,
  int exercises = 2,
}) => <String, dynamic>{
  'nutrition': <String, dynamic>{
    'target': withTarget
        ? <String, dynamic>{
            'calories': 2085,
            'protein_g': 130,
            'carbs_g': 261,
            'fat_g': 58,
          }
        : null,
    'consumed': <String, dynamic>{
      'calories': consumedKcal,
      'protein_g': 69,
      'carbs_g': 165,
      'fat_g': 26,
    },
  },
  'exercise': <String, dynamic>{
    'completed': exercises > 0,
    'muscle_groups_trained': <String>['chest', 'legs'],
    'total_sets': 7,
    'exercises_count': exercises,
  },
  'streak': <String, dynamic>{'exercise_days': 1, 'diet_logging_days': 14},
};

/// [now]가 속한 주의 월~일. 월·수 운동, 월~오늘 식단.
Map<String, dynamic> _weekly(DateTime now) {
  final DateTime monday = _dateOnly(
    now,
  ).subtract(Duration(days: now.weekday - 1));
  return <String, dynamic>{
    'daily_breakdown': <Map<String, dynamic>>[
      for (int i = 0; i < 7; i++)
        <String, dynamic>{
          'date': _ymd(monday.add(Duration(days: i))),
          'calories': i < now.weekday ? 1800 : 0,
          'exercised': i == 0 || i == 2,
        },
    ],
  };
}

/// 40일 전(범위 밖), 20일 전, 10일 전, 오늘 기록. 30일 변화는 72.4 - 73.5 = -1.1.
List<Map<String, dynamic>> _weights(DateTime now) {
  final DateTime today = _dateOnly(now);
  Map<String, dynamic> at(int daysAgo, double kg) => <String, dynamic>{
    'log_date': _ymd(today.subtract(Duration(days: daysAgo))),
    'weight_kg': kg,
  };
  return <Map<String, dynamic>>[
    at(0, 72.4),
    at(40, 75.0),
    at(20, 73.5),
    at(10, 72.9),
  ];
}

Future<void> _pumpHome(
  WidgetTester tester, {
  Map<String, dynamic>? profile,
  Object? profileError,
  Future<Map<String, dynamic>> Function()? today,
  Future<List<Map<String, dynamic>>> Function()? weights,
}) async {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final DateTime now = DateTime.now();
  final FakeProfileRepository profiles = FakeProfileRepository()
    ..profile = profile ?? _profile
    ..error = profileError;
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(profiles),
        todayDashboardProvider.overrideWith(
          (ref) => today == null ? Future.value(_today()) : today(),
        ),
        weeklyDashboardProvider.overrideWith((ref) async => _weekly(now)),
        recentWeightHistoryProvider.overrideWith(
          (ref) => weights == null ? Future.value(_weights(now)) : weights(),
        ),
      ],
      // 앱 루트(main.dart)처럼 ShadTheme 아래에 옛 Material 테마와 셸을 둔다.
      child: ShadTheme(
        data: AppShadTheme.dark(),
        child: MaterialApp(
          theme: AppTheme.darkTheme,
          home: const MainShell(
            currentLocation: '/dashboard',
            child: DashboardScreen(),
          ),
        ),
      ),
    ),
  );
  for (int i = 0; i < 5; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  group('dashboard view data', () {
    // 2026-10-03은 토요일이다.
    final DateTime saturday = DateTime(2026, 10, 3, 9);

    test('subtitle shows the goal only with a known profile goal', () {
      expect(dashboardDateLabel(saturday), '10월 3일 토요일');
      expect(
        dashboardSubtitle(saturday, profile: _profile),
        '10월 3일 토요일 · 체지방 감량 중',
      );
      expect(dashboardSubtitle(saturday), '10월 3일 토요일');
      expect(
        dashboardSubtitle(
          saturday,
          profile: const <String, dynamic>{'goal': 'unknown'},
        ),
        '10월 3일 토요일',
      );
      expect(dashboardGoalLabel('bulk'), '근육 증가 중');
      expect(dashboardGoalLabel('maintain'), '체중 유지 중');
    });

    test('week marks today and leaves later days as future', () {
      final List<WeekDayStatus> week = weekStatuses(
        (_weekly(saturday)['daily_breakdown'] as List<Map<String, dynamic>>),
        saturday,
      );
      expect(week.map((WeekDayStatus d) => d.label).join(), '월화수목금토일');
      expect(week[0].exercise, DayMark.done);
      expect(week[1].exercise, DayMark.missed);
      expect(week[5].isToday, isTrue);
      expect(week[5].diet, DayMark.done);
      expect(week[6].exercise, DayMark.future);
      expect(week[6].diet, DayMark.future);
      expect(week[6].fullName, '일요일');
    });

    test('weight keeps the last 30 days in date order', () {
      final DashboardViewData data = DashboardViewData.fromApi(
        profile: _profile,
        today: _today(),
        weekly: _weekly(saturday),
        weightHistory: _weights(saturday),
        weightTrendState: WeightTrendState.ready,
        now: saturday,
      );
      expect(data.weightHistory, <double>[73.5, 72.9, 72.4]);
      expect(data.weightDates, <String>['9/13', '9/23', '10/3']);
      expect(data.weightChangeKg, -1.1);
      expect(data.weightKg, 72.4);
    });

    test('maps exercise, targets and the over-target amount', () {
      final DashboardViewData data = DashboardViewData.fromApi(
        profile: _profile,
        today: _today(consumedKcal: 2400),
        weekly: const <String, dynamic>{},
        weightHistory: null,
        weightTrendState: WeightTrendState.loading,
        now: saturday,
      );
      expect(data.todayExerciseTitle, '가슴 · 하체');
      expect(data.todayExerciseDetail, '2개 운동 · 7세트');
      expect(data.overKcal, 315);
      expect(data.weightChangeKg, isNull);
      expect(data.week, isEmpty);

      final DashboardViewData noTarget = DashboardViewData.fromApi(
        profile: const <String, dynamic>{},
        today: _today(withTarget: false, exercises: 0),
        weekly: const <String, dynamic>{},
        weightHistory: const <Map<String, dynamic>>[],
        weightTrendState: WeightTrendState.ready,
        now: saturday,
      );
      expect(noTarget.hasTarget, isFalse);
      expect(noTarget.intakeRatio, 0);
      expect(noTarget.overKcal, 0);
      expect(noTarget.proteinTargetG, isNull);
      expect(noTarget.todayExerciseTitle, isNull);
      expect(noTarget.weightKg, isNull);
    });
  });

  group('DashboardScreen', () {
    testWidgets('renders the new design inside the shell', (
      WidgetTester tester,
    ) async {
      await _pumpHome(tester);
      expect(tester.takeException(), isNull);
      expect(
        find.text('${dashboardDateLabel(DateTime.now())} · 체지방 감량 중'),
        findsOneWidget,
      );
      expect(find.text('오늘의 진행'), findsOneWidget);
      expect(find.text('가슴 · 하체'), findsOneWidget);
      // 지난 30일 변화(-1.1kg) 중립 배지
      expect(find.text('1.1kg'), findsOneWidget);
      // 화면의 Primary 버튼은 AI 코치 하나다.
      expect(
        tester
            .widgetList<ShadButton>(find.byType(ShadButton))
            .where((ShadButton b) => b.variant == ShadButtonVariant.primary),
        hasLength(1),
      );

      // 끝까지 스크롤하면 마지막 카드가 셸의 하단 탭 위에 보인다.
      await tester.drag(
        find.byKey(DashboardView.scrollKey),
        const Offset(0, -6000),
      );
      await tester.pump(const Duration(milliseconds: 500));
      final Rect last = tester.getRect(find.byKey(DashboardView.lastBlockKey));
      final Rect nav = tester.getRect(
        find.ancestor(of: find.text('스캔'), matching: find.byType(Row)).first,
      );
      expect(last.bottom, lessThanOrEqualTo(nav.top));
      expect(tester.takeException(), isNull);
    });

    testWidgets('shows a warning badge when intake passes the target', (
      WidgetTester tester,
    ) async {
      await _pumpHome(tester, today: () async => _today(consumedKcal: 2400));
      expect(find.text('315kcal 초과'), findsOneWidget);
      // 링 중앙은 자르지 않은 실제 비율이다.
      expect(find.text('115%'), findsOneWidget);
    });

    testWidgets('profile 404 asks for setup and shows only the date', (
      WidgetTester tester,
    ) async {
      await _pumpHome(
        tester,
        profileError: const ProfileRepositoryException(
          '프로필 없음',
          statusCode: 404,
        ),
      );
      expect(find.text('프로필 설정이 필요합니다'), findsOneWidget);
      expect(find.text(dashboardDateLabel(DateTime.now())), findsOneWidget);
      expect(find.textContaining('감량'), findsNothing);
    });

    testWidgets('server error shows the message and a retry button', (
      WidgetTester tester,
    ) async {
      await _pumpHome(
        tester,
        today: () async => throw const DashboardRepositoryException(
          '대시보드 연결 오류',
          statusCode: 500,
        ),
      );
      expect(find.text('대시보드를 불러오지 못했습니다'), findsOneWidget);
      expect(find.text('대시보드 연결 오류'), findsOneWidget);
      expect(find.text('다시 시도'), findsOneWidget);
      expect(find.text(dashboardDateLabel(DateTime.now())), findsOneWidget);
    });

    testWidgets('weight trend loads separately from the rest', (
      WidgetTester tester,
    ) async {
      final Completer<List<Map<String, dynamic>>> pending =
          Completer<List<Map<String, dynamic>>>();
      await _pumpHome(tester, weights: () => pending.future);
      expect(find.text('오늘의 진행'), findsOneWidget);
      // 체중 차트 자리만 스켈레톤이다.
      expect(find.byType(SkeletonBlock), findsOneWidget);
      expect(find.byType(TrendLineChart), findsNothing);
    });
  });
}
