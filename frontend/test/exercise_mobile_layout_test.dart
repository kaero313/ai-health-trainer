import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/exercise/data/exercise_repository.dart';
import 'package:frontend/features/exercise/presentation/exercise_add_screen.dart';
import 'package:frontend/features/exercise/presentation/exercise_recommend_screen.dart';
import 'package:frontend/features/exercise/presentation/exercise_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('exercise routes fit $viewport at large text scale', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final FakeExerciseRepository repository =
          FakeExerciseRepository()
            ..logs = _exerciseData
            ..recommendation = _recommendation;
      final List<Override> overrides = <Override>[
        exerciseRepositoryProvider.overrideWithValue(repository),
      ];

      await _pumpScreen(tester, const ExerciseScreen(), overrides);
      await tester.pump();
      expect(find.text('운동 플랜'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, ExerciseAddScreen(), overrides);
      expect(find.text('세트별 운동 기록을 입력하세요'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const ExerciseRecommendScreen(), overrides);
      await tester.pump();
      expect(find.text('AI 운동 추천'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}

const Map<String, dynamic> _exerciseData = <String, dynamic>{
  'exercises': <Map<String, dynamic>>[
    <String, dynamic>{
      'id': 1,
      'exercise_name': '바벨 백 스쿼트',
      'muscle_group': 'legs',
      'sets': <Map<String, dynamic>>[
        <String, dynamic>{'set_number': 1, 'reps': 8, 'weight_kg': 80},
        <String, dynamic>{'set_number': 2, 'reps': 8, 'weight_kg': 80},
      ],
    },
  ],
};

const Map<String, dynamic> _recommendation = <String, dynamic>{
  'recommendation': '하체의 주요 움직임을 균형 있게 구성했습니다.',
  'suggested_exercises': <Map<String, dynamic>>[
    <String, dynamic>{
      'exercise_name': '루마니안 데드리프트',
      'muscle_group': 'legs',
      'sets': 3,
      'reps': 10,
      'weight_kg': null,
      'reason': '후면 사슬을 보완합니다.',
    },
  ],
  'sources': <String>['근비대 운동 구성 가이드'],
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
