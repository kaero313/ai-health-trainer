import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/chat/data/chat_repository.dart';
import 'package:frontend/features/chat/presentation/chat_screen.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/features/profile/presentation/profile_edit_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('chat and profile form fit $viewport at large text scale', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pumpScreen(tester, const ChatScreen(), <Override>[
        chatRepositoryProvider.overrideWithValue(FakeChatRepository()),
      ]);
      expect(find.text('AI 코치'), findsWidgets);
      expect(tester.takeException(), isNull);

      final FakeProfileRepository profileRepository =
          FakeProfileRepository()..profile = _profile;
      await _pumpScreen(tester, const ProfileEditScreen(), <Override>[
        profileRepositoryProvider.overrideWithValue(profileRepository),
      ]);
      await tester.pump();
      expect(find.text('프로필 설정'), findsOneWidget);
      expect(find.text('저장하기'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('chat input stays usable in a reduced keyboard viewport', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(360, 600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await _pumpScreen(tester, const ChatScreen(), <Override>[
      chatRepositoryProvider.overrideWithValue(FakeChatRepository()),
    ]);
    await tester.tap(find.byType(TextField));
    await tester.pump();

    expect(find.byIcon(Icons.send), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

const Map<String, dynamic> _profile = <String, dynamic>{
  'name': '모바일 테스터',
  'height_cm': 175,
  'weight_kg': 78.4,
  'age': 32,
  'gender': 'male',
  'goal': 'bulk',
  'activity_level': 'active',
  'allergies': <String>['유당 민감'],
  'food_preferences': <String>['고단백', '지중해식'],
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
