import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/features/diet/data/diet_image_picker.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/diet/presentation/diet_add_screen.dart';
import 'package:frontend/features/diet/presentation/diet_analyze_screen.dart';
import 'package:frontend/features/diet/presentation/diet_recommend_screen.dart';
import 'package:frontend/features/diet/presentation/diet_screen.dart';

import 'support/fake_repositories.dart';

void main() {
  for (final Size viewport in <Size>[
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    testWidgets('diet routes fit $viewport at large text scale', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(viewport);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final FakeDietRepository repository =
          FakeDietRepository()
            ..logs = _dietData
            ..recommendation = _recommendation;
      final List<Override> overrides = <Override>[
        dietRepositoryProvider.overrideWithValue(repository),
        dietImagePickerProvider.overrideWithValue(FakeDietImagePicker()),
      ];

      await _pumpScreen(tester, const DietScreen(), overrides);
      expect(find.text('식단 플래너'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const DietAddScreen(), overrides);
      expect(find.text('직접 식단 기록'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const DietAnalyzeScreen(), overrides);
      expect(find.text('AI 식단 스캔'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _pumpScreen(tester, const DietRecommendScreen(), overrides);
      await tester.pump();
      expect(find.text('AI 식단 추천'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}

const Map<String, dynamic> _dietData = <String, dynamic>{
  'daily_total': <String, dynamic>{
    'calories': 680,
    'protein_g': 45,
    'carbs_g': 62,
    'fat_g': 18,
  },
  'target_remaining': <String, dynamic>{
    'calories': 1320,
    'protein_g': 105,
    'carbs_g': 188,
    'fat_g': 42,
  },
  'meals': <String, dynamic>{
    'lunch': <Map<String, dynamic>>[
      <String, dynamic>{
        'id': 1,
        'items': <Map<String, dynamic>>[
          <String, dynamic>{
            'food_name': '구운 연어와 퀴노아',
            'calories': 680,
            'protein_g': 45,
            'carbs_g': 62,
            'fat_g': 18,
          },
        ],
      },
    ],
  },
};

const Map<String, dynamic> _recommendation = <String, dynamic>{
  'recommendation': '남은 영양 목표에 맞춰 단백질과 복합 탄수화물을 보충하세요.',
  'remaining_nutrients': <String, dynamic>{
    'calories': 1320,
    'protein_g': 105,
    'carbs_g': 188,
    'fat_g': 42,
  },
  'suggested_foods': <Map<String, dynamic>>[
    <String, dynamic>{
      'food_name': '닭가슴살 현미 덮밥',
      'calories': 520,
      'protein_g': 48,
      'carbs_g': 58,
      'fat_g': 10,
    },
  ],
  'sources': <String>['근육 증가기 영양 가이드'],
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
