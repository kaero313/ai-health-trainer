import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/diet/presentation/diet_add_screen.dart';
import 'package:frontend/features/exercise/data/exercise_repository.dart';
import 'package:frontend/features/exercise/presentation/exercise_add_screen.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/features/profile/presentation/profile_edit_screen.dart';

import 'support/fake_repositories.dart';

// 입력 화면 세 곳은 저장 버튼을 하단 고정 바에 두므로,
// 작은 화면과 키보드가 올라온 상태에서도 스크롤 없이 눌려야 한다.
void main() {
  final Map<String, Widget Function()> screens = <String, Widget Function()>{
    '식단 추가': () => const DietAddScreen(),
    '운동 추가': () => ExerciseAddScreen(),
    '프로필 수정': () => const ProfileEditScreen(),
  };

  for (final MapEntry<String, Widget Function()> screen in screens.entries) {
    for (final double keyboardInset in <double>[0, 300]) {
      testWidgets(
        '${screen.key} 저장 버튼이 360x600, 키보드 $keyboardInset에서 스크롤 없이 보인다',
        (WidgetTester tester) async {
          tester.view.physicalSize = const Size(360, 600);
          tester.view.devicePixelRatio = 1.0;
          tester.view.viewInsets = FakeViewPadding(bottom: keyboardInset);
          addTearDown(tester.view.reset);

          await _pumpScreen(tester, screen.value());

          final Finder saveButton = find.text('저장하기').hitTestable();
          expect(saveButton, findsOneWidget);
          // 테스트 키보드는 실제로 화면을 덮지 않으므로 위치로 가려짐을 판정한다.
          expect(
            tester.getRect(saveButton).bottom,
            lessThanOrEqualTo(600 - keyboardInset),
          );
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
}

Future<void> _pumpScreen(WidgetTester tester, Widget screen) async {
  final FakeProfileRepository profileRepository =
      FakeProfileRepository()
        ..profile = <String, dynamic>{
          'height_cm': 175,
          'weight_kg': 78.4,
          'age': 32,
          'gender': 'male',
          'goal': 'bulk',
          'activity_level': 'active',
          'allergies': <String>['유당 민감'],
          'food_preferences': <String>['고단백'],
        };
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: <Override>[
        dietRepositoryProvider.overrideWithValue(FakeDietRepository()),
        exerciseRepositoryProvider.overrideWithValue(FakeExerciseRepository()),
        profileRepositoryProvider.overrideWithValue(profileRepository),
      ],
      child: MaterialApp(theme: AppTheme.darkTheme, home: screen),
    ),
  );
  await tester.pump();
  await tester.pump();
}
