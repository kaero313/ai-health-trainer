import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/chat/data/chat_repository.dart';
import 'package:frontend/features/chat/presentation/chat_screen.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/diet/presentation/diet_recommend_screen.dart';
import 'package:frontend/features/exercise/data/exercise_repository.dart';
import 'package:frontend/features/exercise/presentation/exercise_recommend_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  testWidgets('Chat sends selected context and renders answer sources', (
    WidgetTester tester,
  ) async {
    final FakeChatRepository repository =
        FakeChatRepository()
          ..response = <String, dynamic>{
            'answer': '오늘은 단백질을 나눠 섭취하세요.',
            'sources': <String>['단백질 섭취 가이드'],
          };

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          chatRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(home: ChatScreen()),
      ),
    );

    await tester.tap(find.text('식단'));
    await tester.enterText(find.byType(TextField), '운동 후 무엇을 먹을까요?');
    await tester.pump();
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump();
    await tester.pump();

    expect(repository.lastContextType, 'diet');
    expect(repository.lastMessage, '운동 후 무엇을 먹을까요?');
    expect(find.text('오늘은 단백질을 나눠 섭취하세요.'), findsOneWidget);
    expect(find.text('단백질 섭취 가이드'), findsOneWidget);
  });

  testWidgets('Chat renders a clean repository error', (
    WidgetTester tester,
  ) async {
    final FakeChatRepository repository =
        FakeChatRepository()
          ..error = const ChatRepositoryException(
            '답변에 필요한 근거를 찾지 못했습니다.',
            code: 'RAG_CONTEXT_UNAVAILABLE',
            statusCode: 503,
          );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          chatRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(home: ChatScreen()),
      ),
    );
    await tester.enterText(find.byType(TextField), '질문');
    await tester.pump();
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump();
    await tester.pump();

    expect(find.textContaining('답변에 필요한 근거'), findsOneWidget);
    expect(find.textContaining('{'), findsNothing);
  });

  testWidgets('Diet recommendation renders result and source chip', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository repository =
        FakeDietRepository()
          ..recommendation = <String, dynamic>{
            'recommendation': '저녁에는 복합 탄수화물을 보충하세요.',
            'remaining_nutrients': <String, dynamic>{},
            'suggested_foods': <Map<String, dynamic>>[],
            'sources': <String>['영양 기본 가이드'],
          };

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          dietRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(home: DietRecommendScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('저녁에는 복합 탄수화물을 보충하세요.'), findsOneWidget);
    expect(find.textContaining('영양 기본 가이드'), findsOneWidget);
  });

  testWidgets('Exercise recommendation renders clean structured error', (
    WidgetTester tester,
  ) async {
    final FakeExerciseRepository repository =
        FakeExerciseRepository()
          ..recommendationError = const ExerciseRepositoryException(
            'AI 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해 주세요.',
            code: 'AI_SCHEMA_INVALID',
            statusCode: 502,
          );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          exerciseRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(home: ExerciseRecommendScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('추천을 불러오지 못했습니다'), findsOneWidget);
    expect(find.textContaining('AI 응답 형식'), findsOneWidget);
  });
}
