import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/diet/data/diet_image_picker.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/diet/presentation/diet_analyze_screen.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import 'support/fake_repositories.dart';

void main() {
  testWidgets('Scan picks bytes, analyzes, and saves selected foods', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository repository =
        FakeDietRepository()
          ..analysis = <String, dynamic>{
            'foods': <Map<String, dynamic>>[
              <String, dynamic>{
                'food_name': '연어 샐러드',
                'serving_size': '1접시',
                'calories': 420,
                'protein_g': 35,
                'carbs_g': 22,
                'fat_g': 18,
                'confidence': 0.94,
              },
            ],
          };
    final Uint8List pngBytes = Uint8List.fromList(
      base64Decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
      ),
    );
    final FakeDietImagePicker picker =
        FakeDietImagePicker()
          ..image = XFile.fromData(
            pngBytes,
            name: 'meal.png',
            mimeType: 'image/png',
          );
    final GoRouter router = GoRouter(
      initialLocation: '/diet/analyze',
      routes: <RouteBase>[
        GoRoute(
          path: '/diet/analyze',
          builder:
              (BuildContext context, GoRouterState state) =>
                  const DietAnalyzeScreen(),
        ),
        GoRoute(
          path: '/diet',
          builder:
              (BuildContext context, GoRouterState state) =>
                  const Scaffold(body: Text('식단 저장 완료')),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          dietRepositoryProvider.overrideWithValue(repository),
          dietImagePickerProvider.overrideWithValue(picker),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );

    await tester.tap(find.text('갤러리'));
    await tester.pump();
    await tester.pump();

    expect(picker.lastSource, ImageSource.gallery);
    expect(repository.uploadedBytes, orderedEquals(pngBytes));
    expect(repository.uploadedFilename, 'gallery_image.png');
    expect(repository.uploadedContentType, 'image/png');
    expect(find.byType(Image), findsOneWidget);
    expect(find.text('연어 샐러드'), findsOneWidget);

    await tester.ensureVisible(find.text('선택한 음식 저장'));
    await tester.tap(find.text('선택한 음식 저장'));
    await tester.pump();
    await tester.pump();

    expect(repository.createdPayloads, hasLength(1));
    expect(repository.createdPayloads.single['ai_analyzed'], isTrue);
    expect(
      repository.createdPayloads.single['items'],
      isA<List<Map<String, dynamic>>>(),
    );
    expect(find.text('식단 저장 완료'), findsOneWidget);
  });

  testWidgets('Scan cancel and picker errors do not call analysis', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository repository = FakeDietRepository();
    final FakeDietImagePicker picker = FakeDietImagePicker();

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          dietRepositoryProvider.overrideWithValue(repository),
          dietImagePickerProvider.overrideWithValue(picker),
        ],
        child: const MaterialApp(home: DietAnalyzeScreen()),
      ),
    );

    await tester.tap(find.text('카메라'));
    await tester.pump();
    expect(repository.uploadedBytes, isNull);

    picker.error = StateError('camera unavailable');
    await tester.tap(find.text('카메라'));
    await tester.pump();
    expect(find.text('분석 오류'), findsOneWidget);
    expect(find.textContaining('사진 접근 권한'), findsOneWidget);
  });

  testWidgets('Scan rejects unsupported image formats before upload', (
    WidgetTester tester,
  ) async {
    final FakeDietRepository repository = FakeDietRepository();
    final FakeDietImagePicker picker =
        FakeDietImagePicker()
          ..image = XFile.fromData(
            Uint8List.fromList(<int>[1, 2, 3]),
            name: 'meal.gif',
            mimeType: 'image/gif',
          );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          dietRepositoryProvider.overrideWithValue(repository),
          dietImagePickerProvider.overrideWithValue(picker),
        ],
        child: const MaterialApp(home: DietAnalyzeScreen()),
      ),
    );

    await tester.tap(find.text('갤러리'));
    await tester.pump();

    expect(repository.uploadedBytes, isNull);
    expect(find.text('JPEG 또는 PNG 이미지만 선택할 수 있습니다.'), findsOneWidget);
  });
}
