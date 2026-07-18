import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
import '../data/diet_image_picker.dart';
import '../data/diet_repository.dart';
import '../domain/diet_controller.dart';

const Map<String, String> kDietMealTypeLabels = <String, String>{
  'breakfast': '아침',
  'lunch': '점심',
  'dinner': '저녁',
  'snack': '간식',
};

class DietAnalyzeScreen extends ConsumerStatefulWidget {
  const DietAnalyzeScreen({super.key});

  @override
  ConsumerState<DietAnalyzeScreen> createState() => _DietAnalyzeScreenState();
}

class _DietAnalyzeScreenState extends ConsumerState<DietAnalyzeScreen> {
  Uint8List? _selectedImageBytes;
  String? _selectedImageName;
  List<Map<String, dynamic>> _foods = <Map<String, dynamic>>[];
  Set<int> _selectedIndexes = <int>{};
  String _mealType = 'breakfast';
  bool _isAnalyzing = false;
  bool _isSaving = false;
  String? _errorMessage;

  Future<void> _pickAndAnalyze(ImageSource source) async {
    try {
      final XFile? image = await ref
          .read(dietImagePickerProvider)
          .pickImage(source);
      if (image == null) {
        return;
      }
      final Uint8List bytes = await image.readAsBytes();
      if (bytes.isEmpty) {
        throw const DietRepositoryException('선택한 이미지가 비어 있습니다.');
      }
      final String contentType = _resolveImageContentType(
        filename: image.name,
        pickerMimeType: image.mimeType,
      );
      final String filename = _normalizedFilename(
        image.name,
        source,
        contentType,
      );

      if (!mounted) {
        return;
      }
      setState(() {
        _selectedImageBytes = bytes;
        _selectedImageName = filename;
        _isAnalyzing = true;
        _errorMessage = null;
        _foods = <Map<String, dynamic>>[];
        _selectedIndexes = <int>{};
      });

      final Map<String, dynamic> result = await ref
          .read(dietRepositoryProvider)
          .analyzeImage(
            bytes: bytes,
            filename: filename,
            contentType: contentType,
          );
      final List<Map<String, dynamic>> foods =
          (result['foods'] as List<dynamic>? ?? <dynamic>[])
              .whereType<Map<String, dynamic>>()
              .toList();

      if (!mounted) {
        return;
      }
      setState(() {
        _foods = foods;
        _selectedIndexes = Set<int>.from(
          List<int>.generate(foods.length, (int index) => index),
        );
        _isAnalyzing = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = _extractErrorMessage(error);
        _isAnalyzing = false;
      });
    }
  }

  Future<void> _saveSelectedFoods() async {
    if (_selectedIndexes.isEmpty) {
      setState(() {
        _errorMessage = '저장할 음식을 하나 이상 선택해 주세요.';
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    final DateTime targetDate = ref.read(selectedDietDateProvider);
    final List<Map<String, dynamic>> selectedFoods = <Map<String, dynamic>>[];
    for (final int index in _selectedIndexes) {
      if (index < 0 || index >= _foods.length) {
        continue;
      }
      final Map<String, dynamic> food = _foods[index];
      selectedFoods.add(<String, dynamic>{
        'food_name': food['food_name']?.toString() ?? '음식',
        'serving_size': _nullableString(food['serving_size']),
        'calories': _toDouble(food['calories']),
        'protein_g': _toDouble(food['protein_g']),
        'carbs_g': _toDouble(food['carbs_g']),
        'fat_g': _toDouble(food['fat_g']),
        'confidence': _toDoubleOrNull(food['confidence']),
      });
    }

    final Map<String, dynamic> payload = <String, dynamic>{
      'log_date': DateFormat('yyyy-MM-dd').format(targetDate),
      'meal_type': _mealType,
      'image_url': null,
      'ai_analyzed': true,
      'items': selectedFoods,
    };

    try {
      await ref.read(dietRepositoryProvider).createDietLog(payload);
      ref.invalidate(dietLogsProvider);
      if (!mounted) {
        return;
      }
      context.go('/diet');
    } catch (error) {
      setState(() {
        _errorMessage = _extractErrorMessage(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return NeoPage(
      children: [
        Text('AI 식단 스캔', style: AppTypography.h1),
        const SizedBox(height: AppSpacing.xs),
        Text(
          '사진으로 칼로리와 영양 정보를 분석합니다.',
          style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.lg),
        _ScanHero(
          selectedImageBytes: _selectedImageBytes,
          selectedImageName: _selectedImageName,
          isAnalyzing: _isAnalyzing,
          onCamera: () => _pickAndAnalyze(ImageSource.camera),
          onGallery: () => _pickAndAnalyze(ImageSource.gallery),
        ),
        if (_errorMessage != null) ...[
          const SizedBox(height: AppSpacing.md),
          NeoStateCard(
            icon: Icons.error_outline,
            title: '분석 오류',
            message: _errorMessage!,
          ),
        ],
        if (_selectedImageBytes != null && !_isAnalyzing) ...[
          const SizedBox(height: AppSpacing.md),
          _AnalyzeResult(
            foods: _foods,
            selectedIndexes: _selectedIndexes,
            mealType: _mealType,
            onMealTypeChanged: (String mealType) {
              setState(() {
                _mealType = mealType;
              });
            },
            onFoodSelectionChanged: (int index, bool checked) {
              setState(() {
                if (checked) {
                  _selectedIndexes.add(index);
                } else {
                  _selectedIndexes.remove(index);
                }
              });
            },
            onSave: _isSaving ? null : _saveSelectedFoods,
            isSaving: _isSaving,
          ),
        ],
      ],
    );
  }
}

class _ScanHero extends StatelessWidget {
  final Uint8List? selectedImageBytes;
  final String? selectedImageName;
  final bool isAnalyzing;
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  const _ScanHero({
    required this.selectedImageBytes,
    required this.selectedImageName,
    required this.isAnalyzing,
    required this.onCamera,
    required this.onGallery,
  });

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      highlighted: true,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (selectedImageBytes == null)
            Container(
              height: 280,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(AppRadius.xl),
                border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.24),
                ),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    AppColors.primary.withValues(alpha: 0.16),
                    Colors.white.withValues(alpha: 0.02),
                  ],
                ),
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(AppRadius.xl),
                    child: Image.asset(
                      'assets/stitch/nutrition_salmon.jpg',
                      fit: BoxFit.cover,
                    ),
                  ),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(AppRadius.xl),
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          AppColors.background.withValues(alpha: 0.26),
                          AppColors.background.withValues(alpha: 0.92),
                        ],
                      ),
                    ),
                  ),
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.center_focus_strong,
                            color: AppColors.primary,
                            size: 48,
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            '음식 사진을 선택하세요',
                            style: AppTypography.h3,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            'JPG/PNG 형식을 지원합니다.',
                            style: AppTypography.body2.copyWith(
                              color: AppColors.textSecondary,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            )
          else
            Semantics(
              image: true,
              label: selectedImageName ?? '선택한 음식 이미지',
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.xl),
                child: Image.memory(
                  selectedImageBytes!,
                  height: 260,
                  fit: BoxFit.cover,
                  gaplessPlayback: true,
                  errorBuilder: (
                    BuildContext context,
                    Object _,
                    StackTrace? __,
                  ) {
                    return const SizedBox(
                      height: 260,
                      child: Center(
                        child: Icon(
                          Icons.broken_image_outlined,
                          color: AppColors.error,
                          size: 44,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          if (selectedImageBytes != null && selectedImageName != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              selectedImageName!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: AppTypography.caption,
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          if (isAnalyzing)
            Column(
              children: [
                const LinearProgressIndicator(
                  minHeight: 4,
                  color: AppColors.primary,
                  backgroundColor: AppColors.surfaceHigh,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  '음식과 영양 정보를 분석하고 있습니다.',
                  textAlign: TextAlign.center,
                  style: AppTypography.body2.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            )
          else
            Row(
              children: [
                Expanded(
                  child: NeoPrimaryButton(
                    label: '카메라',
                    icon: Icons.camera_alt_outlined,
                    onPressed: onCamera,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: NeoOutlineButton(
                    label: '갤러리',
                    icon: Icons.photo_library_outlined,
                    onPressed: onGallery,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _AnalyzeResult extends StatelessWidget {
  final List<Map<String, dynamic>> foods;
  final Set<int> selectedIndexes;
  final String mealType;
  final ValueChanged<String> onMealTypeChanged;
  final void Function(int index, bool checked) onFoodSelectionChanged;
  final VoidCallback? onSave;
  final bool isSaving;

  const _AnalyzeResult({
    required this.foods,
    required this.selectedIndexes,
    required this.mealType,
    required this.onMealTypeChanged,
    required this.onFoodSelectionChanged,
    required this.onSave,
    required this.isSaving,
  });

  @override
  Widget build(BuildContext context) {
    if (foods.isEmpty) {
      return const NeoStateCard(
        icon: Icons.search_off,
        title: '인식된 음식이 없습니다',
        message: '다른 각도에서 다시 촬영하거나 직접 식단을 추가해 주세요.',
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(child: Text('분석 결과', style: AppTypography.h2)),
            NeoInfoChip(
              label: '${selectedIndexes.length}/${foods.length}개 선택',
              color: AppColors.primary,
              filled: true,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        for (int index = 0; index < foods.length; index++) ...[
          _FoodResultCard(
            food: foods[index],
            checked: selectedIndexes.contains(index),
            onChanged: (bool checked) => onFoodSelectionChanged(index, checked),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        const SizedBox(height: AppSpacing.sm),
        DropdownButtonFormField<String>(
          value: mealType,
          dropdownColor: AppColors.surfaceLow,
          style: AppTypography.body1,
          decoration: const InputDecoration(labelText: '식사 시간'),
          items:
              kDietMealTypeLabels.entries.map((MapEntry<String, String> e) {
                return DropdownMenuItem<String>(
                  value: e.key,
                  child: Text(e.value),
                );
              }).toList(),
          onChanged: (String? value) {
            if (value != null) {
              onMealTypeChanged(value);
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        NeoPrimaryButton(
          label: isSaving ? '저장 중...' : '선택한 음식 저장',
          icon: Icons.check_circle_outline,
          onPressed: onSave,
        ),
      ],
    );
  }
}

class _FoodResultCard extends StatelessWidget {
  final Map<String, dynamic> food;
  final bool checked;
  final ValueChanged<bool> onChanged;

  const _FoodResultCard({
    required this.food,
    required this.checked,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final String name = food['food_name']?.toString() ?? '음식';
    final int calories = _toDouble(food['calories']).round();
    final int protein = _toDouble(food['protein_g']).round();
    final int carbs = _toDouble(food['carbs_g']).round();
    final int fat = _toDouble(food['fat_g']).round();
    final String? servingSize = _nullableString(food['serving_size']);
    final double? confidence = _toDoubleOrNull(food['confidence']);

    return NeoGlassCard(
      child: Row(
        children: [
          Checkbox(
            value: checked,
            activeColor: AppColors.primary,
            checkColor: AppColors.background,
            onChanged: (bool? value) => onChanged(value ?? false),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: AppTypography.h3),
                if (servingSize != null || confidence != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    <String>[
                      if (servingSize != null) servingSize,
                      if (confidence != null)
                        '신뢰도 ${(confidence.clamp(0, 1) * 100).round()}%',
                    ].join(' · '),
                    style: AppTypography.caption,
                  ),
                ],
                const SizedBox(height: AppSpacing.xs),
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [
                    NeoInfoChip(
                      label: '$calories kcal',
                      color: AppColors.primary,
                    ),
                    NeoInfoChip(
                      label: 'P $protein g',
                      color: AppColors.textSecondary,
                    ),
                    NeoInfoChip(
                      label: 'C $carbs g',
                      color: AppColors.secondary,
                    ),
                    NeoInfoChip(label: 'F $fat g', color: AppColors.tertiary),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String? _nullableString(Object? value) {
  final String? text = value?.toString();
  if (text == null || text.trim().isEmpty) {
    return null;
  }
  return text.trim();
}

double _toDouble(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? 0;
  }
  return 0;
}

double? _toDoubleOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return '이미지를 불러오지 못했습니다. 카메라 또는 사진 접근 권한을 확인해 주세요.';
}

String _normalizedFilename(
  String name,
  ImageSource source,
  String contentType,
) {
  final String trimmed = name.trim();
  final String extension = trimmed.toLowerCase().split('.').last;
  if (trimmed.isNotEmpty &&
      (extension == 'jpg' || extension == 'jpeg' || extension == 'png')) {
    return trimmed;
  }
  final String prefix = source == ImageSource.camera ? 'camera' : 'gallery';
  final String fallbackExtension = contentType == 'image/png' ? 'png' : 'jpg';
  return '${prefix}_image.$fallbackExtension';
}

String _resolveImageContentType({
  required String filename,
  required String? pickerMimeType,
}) {
  final String normalizedMimeType = pickerMimeType?.trim().toLowerCase() ?? '';
  if (normalizedMimeType == 'image/jpeg' || normalizedMimeType == 'image/png') {
    return normalizedMimeType;
  }

  final String extension = filename.toLowerCase().split('.').last;
  if (extension == 'png') {
    return 'image/png';
  }
  if (extension == 'jpg' || extension == 'jpeg') {
    return 'image/jpeg';
  }
  throw const DietRepositoryException('JPEG 또는 PNG 이미지만 선택할 수 있습니다.');
}
