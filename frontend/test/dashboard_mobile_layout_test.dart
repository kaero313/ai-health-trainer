import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/dashboard/domain/dashboard_controller.dart';
import 'package:frontend/features/dashboard/presentation/dashboard_screen.dart';
import 'package:frontend/features/dashboard/presentation/monthly_report_screen.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/features/profile/presentation/profile_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('dashboard, stats, and monthly routes fit $viewport', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final FakeProfileRepository profileRepository =
          FakeProfileRepository()..profile = _profile;
      final List<Override> overrides = <Override>[
        profileRepositoryProvider.overrideWithValue(profileRepository),
        todayDashboardProvider.overrideWith((ref) async => _today),
        weeklyDashboardProvider.overrideWith((ref) async => _weekly),
        monthlyDashboardProvider.overrideWith((ref, month) async => const {}),
        weightHistoryProvider.overrideWith((ref, month) async => const []),
      ];

      await _pumpScreen(tester, const DashboardScreen(), overrides);
      await tester.pump();
      expect(find.text('오늘의 진행'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const ProfileScreen(), overrides);
      await tester.pump();
      expect(find.text('신체 통계'), findsOneWidget);
      expect(find.text('기기 미연결'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const MonthlyReportScreen(), overrides);
      await tester.pump();
      expect(find.text('월간 리포트'), findsOneWidget);
      expect(find.text('식단 기록 없음'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}

const Map<String, dynamic> _profile = <String, dynamic>{
  'name': '모바일 테스터',
  'weight_kg': 78.4,
  'height_cm': 175,
  'goal': 'bulk',
  'activity_level': 'active',
  'target_calories': 2500,
  'target_protein_g': 160,
};

const Map<String, dynamic> _today = <String, dynamic>{
  'nutrition': <String, dynamic>{
    'calories': 680,
    'target_calories': 2500,
    'protein_g': 45,
    'target_protein_g': 160,
    'carbs_g': 62,
    'target_carbs_g': 300,
    'fat_g': 18,
    'target_fat_g': 70,
  },
  'exercise': <String, dynamic>{'exercise_count': 1, 'total_sets': 3},
  'streak': <String, dynamic>{'current': 2},
};

const Map<String, dynamic> _weekly = <String, dynamic>{
  'daily_breakdown': <Map<String, dynamic>>[],
  'exercise_summary': <String, dynamic>{},
};

Future<void> _pumpScreen(
  WidgetTester tester,
  Widget screen,
  List<Override> overrides,
) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.darkTheme,
        builder:
            (BuildContext context, Widget? child) => MediaQuery(
              data: MediaQuery.of(
                context,
              ).copyWith(textScaler: const TextScaler.linear(1.3)),
              child: child!,
            ),
        home: screen,
      ),
    ),
  );
  await tester.pump();
}
