import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/dashboard/data/dashboard_repository.dart';
import 'package:frontend/features/dashboard/domain/dashboard_controller.dart';
import 'package:frontend/features/dashboard/presentation/dashboard_screen.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/features/profile/presentation/profile_edit_screen.dart';
import 'package:frontend/features/profile/presentation/profile_screen.dart';
import 'package:go_router/go_router.dart';

import 'support/fake_repositories.dart';

void main() {
  testWidgets('Dashboard renders loading, error, and data states', (
    WidgetTester tester,
  ) async {
    final FakeProfileRepository profileRepository =
        FakeProfileRepository()..profile = _profileData;
    final Completer<Map<String, dynamic>> pendingToday =
        Completer<Map<String, dynamic>>();

    await _pumpScreen(
      tester,
      const DashboardScreen(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(profileRepository),
        todayDashboardProvider.overrideWith((ref) => pendingToday.future),
        weeklyDashboardProvider.overrideWith(
          (ref) async => <String, dynamic>{},
        ),
      ],
    );
    expect(find.text('데이터를 동기화하는 중'), findsOneWidget);

    await _pumpScreen(
      tester,
      const DashboardScreen(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(profileRepository),
        todayDashboardProvider.overrideWith(
          (ref) async =>
              throw const DashboardRepositoryException(
                '대시보드 연결 오류',
                statusCode: 500,
              ),
        ),
        weeklyDashboardProvider.overrideWith(
          (ref) async => <String, dynamic>{},
        ),
      ],
    );
    await tester.pump();
    expect(find.text('대시보드를 불러오지 못했습니다'), findsOneWidget);
    expect(find.text('대시보드 연결 오류'), findsOneWidget);

    await _pumpScreen(
      tester,
      const DashboardScreen(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(profileRepository),
        todayDashboardProvider.overrideWith((ref) async => <String, dynamic>{}),
        weeklyDashboardProvider.overrideWith(
          (ref) async => <String, dynamic>{},
        ),
      ],
    );
    await tester.pump();
    expect(find.text('오늘의 진행'), findsOneWidget);
    expect(find.text('영양'), findsOneWidget);
  });

  testWidgets('Profile renders error and biometric data states', (
    WidgetTester tester,
  ) async {
    final FakeProfileRepository errorRepository =
        FakeProfileRepository()
          ..error = const ProfileRepositoryException(
            '프로필 연결 오류',
            statusCode: 500,
          );
    await _pumpScreen(
      tester,
      const ProfileScreen(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(errorRepository),
      ],
    );
    await tester.pump();
    expect(find.text('프로필을 불러오지 못했습니다'), findsOneWidget);
    expect(find.text('프로필 연결 오류'), findsOneWidget);

    final FakeProfileRepository dataRepository =
        FakeProfileRepository()..profile = _profileData;
    await _pumpScreen(
      tester,
      const ProfileScreen(),
      overrides: <Override>[
        profileRepositoryProvider.overrideWithValue(dataRepository),
      ],
    );
    await tester.pump();
    expect(find.text('신체 통계'), findsOneWidget);
    expect(find.text('현재 체중'), findsOneWidget);
    expect(find.textContaining('78.4', findRichText: true), findsOneWidget);
  });

  testWidgets('Profile edit deep link returns to profile after save', (
    WidgetTester tester,
  ) async {
    final FakeProfileRepository repository =
        FakeProfileRepository()
          ..profile = <String, dynamic>{
            ..._profileData,
            'age': 32,
            'gender': 'male',
            'activity_level': 'active',
            'allergies': <String>['유당 민감'],
            'food_preferences': <String>['고단백'],
          };
    final GoRouter router = GoRouter(
      initialLocation: '/profile/edit',
      routes: <RouteBase>[
        GoRoute(
          path: '/profile/edit',
          builder: (_, __) => const ProfileEditScreen(),
        ),
        GoRoute(
          path: '/profile',
          builder: (_, __) => const Scaffold(body: Text('프로필 도착')),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          profileRepositoryProvider.overrideWithValue(repository),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump();
    await tester.pump();

    final Finder saveButton = find.text('저장하기');
    await tester.ensureVisible(saveButton);
    await tester.tap(saveButton);
    await tester.pump();
    await tester.pump();

    expect(router.state.uri.path, '/profile');
    expect(find.text('프로필 도착'), findsOneWidget);
  });
}

const Map<String, dynamic> _profileData = <String, dynamic>{
  'name': 'UI 테스터',
  'weight_kg': 78.4,
  'height_cm': 175,
  'goal': 'bulk',
  'body_fat_percent': 14.2,
};

Future<void> _pumpScreen(
  WidgetTester tester,
  Widget screen, {
  required List<Override> overrides,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: <Override>[
        weightHistoryProvider.overrideWith(
          (ref, month) async => <Map<String, dynamic>>[],
        ),
        ...overrides,
      ],
      child: MaterialApp(home: screen),
    ),
  );
  await tester.pump();
}
