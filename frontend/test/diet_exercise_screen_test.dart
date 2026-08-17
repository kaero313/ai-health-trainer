import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/diet/presentation/diet_add_screen.dart';
import 'package:frontend/features/diet/presentation/diet_screen.dart';
import 'package:frontend/features/exercise/data/exercise_repository.dart';
import 'package:frontend/features/exercise/presentation/exercise_add_screen.dart';
import 'package:frontend/features/exercise/presentation/exercise_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  testWidgets('Diet renders empty and data states and deletes a log', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository repository =
        FakeDietRepository()..logs = _emptyDietData;
    await _pumpWithOverrides(tester, const DietScreen(), <Override>[
      dietRepositoryProvider.overrideWithValue(repository),
    ]);
    await tester.pump();
    expect(find.text('아침 기록 추가'), findsOneWidget);
    expect(find.text('저녁 기록 추가'), findsOneWidget);

    repository.logs = <String, dynamic>{
      'daily_total': <String, dynamic>{
        'calories': 180.4,
        'protein_g': 20.4,
        'carbs_g': 12,
        'fat_g': 5,
      },
      'target_remaining': <String, dynamic>{
        'calories': 1819.6,
        'protein_g': 129.6,
        'carbs_g': 238,
        'fat_g': 55,
      },
      'meals': <String, dynamic>{
        'breakfast': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 7,
            'items': <Map<String, dynamic>>[
              <String, dynamic>{
                'food_name': '그릭 요거트',
                'calories': 180,
                'protein_g': 20,
                'carbs_g': 12,
              },
            ],
          },
        ],
      },
    };
    await _pumpWithOverrides(tester, const DietScreen(), <Override>[
      dietRepositoryProvider.overrideWithValue(repository),
    ]);
    await tester.pump();
    expect(find.text('그릭 요거트'), findsOneWidget);
    expect(find.text('180 / 2000 kcal'), findsOneWidget);
    expect(find.text('20 / 150 g'), findsOneWidget);

    await tester.ensureVisible(find.byIcon(Icons.more_vert));
    await tester.tap(find.byIcon(Icons.more_vert));
    await tester.pump();
    expect(repository.deletedLogIds, <int>[7]);
  });

  testWidgets('Exercise renders empty and data states and deletes a log', (
    WidgetTester tester,
  ) async {
    final FakeExerciseRepository repository =
        FakeExerciseRepository()
          ..logs = <String, dynamic>{'exercises': <dynamic>[]};
    await _pumpWithOverrides(tester, const ExerciseScreen(), <Override>[
      exerciseRepositoryProvider.overrideWithValue(repository),
    ]);
    await tester.pump();
    expect(find.text('아직 기록된 운동이 없습니다'), findsOneWidget);

    repository.logs = <String, dynamic>{
      'exercises': <Map<String, dynamic>>[
        <String, dynamic>{
          'id': 9,
          'exercise_name': '백 스쿼트',
          'muscle_group': 'legs',
          'sets': <Map<String, dynamic>>[
            <String, dynamic>{'reps': 8, 'weight_kg': 80},
          ],
        },
      ],
    };
    await _pumpWithOverrides(tester, const ExerciseScreen(), <Override>[
      exerciseRepositoryProvider.overrideWithValue(repository),
    ]);
    await tester.pump();
    expect(find.text('백 스쿼트'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.delete_outline).first);
    await tester.pump();
    expect(repository.deletedLogIds, <int>[9]);
  });

  testWidgets('Diet and exercise add forms expose validation errors', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository dietRepository = FakeDietRepository();
    await _pumpWithOverrides(tester, const DietAddScreen(), <Override>[
      dietRepositoryProvider.overrideWithValue(dietRepository),
    ]);
    final Finder dietSave = find.text('저장하기');
    await tester.ensureVisible(dietSave);
    await tester.tap(dietSave);
    await tester.pump();
    expect(find.text('음식명을 입력해주세요.'), findsOneWidget);
    expect(find.text('칼로리를 입력해주세요.'), findsOneWidget);
    expect(dietRepository.createdPayloads, isEmpty);

    final FakeExerciseRepository exerciseRepository = FakeExerciseRepository();
    await _pumpWithOverrides(tester, ExerciseAddScreen(), <Override>[
      exerciseRepositoryProvider.overrideWithValue(exerciseRepository),
    ]);
    final Finder exerciseSave = find.text('저장하기');
    await tester.ensureVisible(exerciseSave);
    await tester.tap(exerciseSave);
    await tester.pump();
    expect(find.text('운동명을 입력해주세요.'), findsOneWidget);
    expect(exerciseRepository.createdPayloads, isEmpty);
  });
}

const Map<String, dynamic> _emptyDietData = <String, dynamic>{
  'daily_total': <String, dynamic>{
    'calories': 0,
    'protein_g': 0,
    'carbs_g': 0,
    'fat_g': 0,
  },
  'target_remaining': null,
  'meals': <String, dynamic>{},
};

Future<void> _pumpWithOverrides(
  WidgetTester tester,
  Widget screen,
  List<Override> overrides,
) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: overrides,
      child: MaterialApp(home: screen),
    ),
  );
  await tester.pump();
}
