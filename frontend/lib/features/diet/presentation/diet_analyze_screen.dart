import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shimmer/shimmer.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
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
  final ImagePicker _picker = ImagePicker();

  XFile? _selectedImage;
  List<Map<String, dynamic>> _foods = <Map<String, dynamic>>[];
  Set<int> _selectedIndexes = <int>{};
  String _mealType = 'breakfast';
  bool _isAnalyzing = false;
  bool _isSaving = false;
  bool _hasAnalyzed = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startAnalyzeFlow();
    });
  }

  Future<void> _startAnalyzeFlow() async {
    final ImageSource? source = await _showSourceSheet();
    if (source == null) {
      if (mounted) {
        context.pop();
      }
      return;
    }
    await _pickAndAnalyze(source);
  }

  Future<ImageSource?> _showSourceSheet() async {
    return showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
      ),
      builder: (BuildContext context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('이미지 선택', style: AppTypography.h3),
                const SizedBox(height: AppSpacing.sm),
                ListTile(
                  leading: const Icon(
                    Icons.camera_alt,
                    color: AppColors.primary,
                  ),
                  title: Text('카메라', style: AppTypography.body1),
                  onTap: () => Navigator.of(context).pop(ImageSource.camera),
                ),
                ListTile(
                  leading: const Icon(
                    Icons.photo_library,
                    color: AppColors.primary,
                  ),
                  title: Text('갤러리', style: AppTypography.body1),
                  onTap: () => Navigator.of(context).pop(ImageSource.gallery),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _pickAndAnalyze(ImageSource source) async {
    final XFile? image = await _picker.pickImage(source: source);
    if (image == null) {
      if (mounted) {
        context.pop();
      }
      return;
    }

    setState(() {
      _selectedImage = image;
      _isAnalyzing = true;
      _errorMessage = null;
      _hasAnalyzed = false;
    });

    try {
      final Map<String, dynamic> result = await ref
          .read(dietRepositoryProvider)
          .analyzeImage(image.path);

      final List<Map<String, dynamic>> foods =
          (result['foods'] as List<dynamic>? ?? <dynamic>[])
              .whereType<Map<String, dynamic>>()
              .toList();

      setState(() {
        _foods = foods;
        _selectedIndexes = Set<int>.from(
          List<int>.generate(foods.length, (int index) => index),
        );
        _hasAnalyzed = true;
        _isAnalyzing = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = _extractErrorMessage(e);
        _isAnalyzing = false;
      });
    }
  }

  Future<void> _retake() async {
    final ImageSource? source = await _showSourceSheet();
    if (source == null) {
      if (mounted) {
        context.pop();
      }
      return;
    }
    await _pickAndAnalyze(source);
  }

  Future<void> _saveSelectedFoods() async {
    if (_selectedIndexes.isEmpty) {
      setState(() {
        _errorMessage = '저장할 음식을 하나 이상 선택해주세요.';
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
      'items': selectedFoods,
    };

    try {
      await ref.read(dietRepositoryProvider).createDietLog(payload);
      ref.invalidate(dietLogsProvider);
      if (!mounted) {
        return;
      }
      context.pop(true);
    } catch (e) {
      setState(() {
        _errorMessage = _extractErrorMessage(e);
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
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('음식 사진 분석')),
      body: SafeArea(child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isAnalyzing) {
      return const _AnalyzeLoadingView();
    }

    if (_selectedImage == null) {
      return Center(child: Text('이미지를 불러오는 중...', style: AppTypography.body2));
    }

    if (_errorMessage != null && !_hasAnalyzed) {
      return _AnalyzeErrorView(message: _errorMessage!, onRetry: _retake);
    }

    if (_hasAnalyzed && _foods.isEmpty) {
      return _EmptyAnalyzeResult(
        imagePath: _selectedImage!.path,
        message: '인식된 음식이 없습니다. 다시 촬영해주세요.',
        onRetake: _retake,
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: Image.file(
              File(_selectedImage!.path),
              height: 250,
              fit: BoxFit.cover,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          for (int index = 0; index < _foods.length; index) ...[
            _AnalyzedFoodCard(
              food: _foods[index],
              checked: _selectedIndexes.contains(index),
              onChanged: (bool checked) {
                setState(() {
                  if (checked) {
                    _selectedIndexes.add(index);
                  } else {
                    _selectedIndexes.remove(index);
                  }
                });
              },
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          _SelectedTotalCard(foods: _foods, selectedIndexes: _selectedIndexes),
          const SizedBox(height: AppSpacing.md),
          Text('식사시간', style: AppTypography.body2),
          const SizedBox(height: AppSpacing.xs),
          DropdownButtonFormField<String>(
            value: _mealType,
            decoration: InputDecoration(
              filled: true,
              fillColor: AppColors.surfaceLight,
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(color: AppColors.divider),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: const BorderSide(
                  color: AppColors.primary,
                  width: 1.2,
                ),
              ),
            ),
            dropdownColor: AppColors.surface,
            style: AppTypography.body1,
            items:
                kDietMealTypeLabels.entries.map((MapEntry<String, String> e) {
                  return DropdownMenuItem<String>(
                    value: e.key,
                    child: Text(e.value),
                  );
                }).toList(),
            onChanged: (String? value) {
              if (value == null) {
                return;
              }
              setState(() {
                _mealType = value;
              });
            },
          ),
          const SizedBox(height: AppSpacing.lg),
          if (_errorMessage != null) ...[
            Text(
              _errorMessage!,
              style: AppTypography.body2.copyWith(color: AppColors.error),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          Opacity(
            opacity: _isSaving ? 0.7 : 1,
            child: SizedBox(
              height: 52,
              child: DecoratedBox(
                decoration: primaryButtonDecoration,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    onTap: _isSaving ? null : _saveSelectedFoods,
                    child: Center(
                      child:
                          _isSaving
                              ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: AppColors.background,
                                ),
                              )
                              : Text(
                                '식단에 추가하기',
                                style: AppTypography.body1.copyWith(
                                  color: AppColors.background,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          OutlinedButton(
            onPressed: _retake,
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppColors.divider),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
            ),
            child: Text(
              '다시 촬영',
              style: AppTypography.body2.copyWith(color: AppColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalyzeLoadingView extends StatelessWidget {
  const _AnalyzeLoadingView();

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.surface,
      highlightColor: AppColors.surfaceLight,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: [
            Container(
              height: 250,
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            for (int i = 0; i < 3; i++) ...[
              Container(
                height: 120,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
          ],
        ),
      ),
    );
  }
}

class _AnalyzeErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _AnalyzeErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body2.copyWith(color: AppColors.error),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton(
              onPressed: onRetry,
              child: Text(
                '다시 시도',
                style: AppTypography.body2.copyWith(color: AppColors.primary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyAnalyzeResult extends StatelessWidget {
  final String imagePath;
  final String message;
  final VoidCallback onRetake;

  const _EmptyAnalyzeResult({
    required this.imagePath,
    required this.message,
    required this.onRetake,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: Image.file(File(imagePath), height: 250, fit: BoxFit.cover),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            message,
            style: AppTypography.body1,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.md),
          OutlinedButton(
            onPressed: onRetake,
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppColors.divider),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
            ),
            child: Text(
              '다시 촬영',
              style: AppTypography.body2.copyWith(color: AppColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalyzedFoodCard extends StatelessWidget {
  final Map<String, dynamic> food;
  final bool checked;
  final ValueChanged<bool> onChanged;

  const _AnalyzedFoodCard({
    required this.food,
    required this.checked,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final double confidence = _toDouble(food['confidence']);
    final int stars = (confidence * 5).clamp(0, 5).round();

    return DecoratedBox(
      decoration: cardDecoration,
      child: CheckboxListTile(
        value: checked,
        onChanged: (bool? value) => onChanged(value ?? false),
        activeColor: AppColors.primary,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(
          food['food_name']?.toString() ?? '음식',
          style: AppTypography.body1.copyWith(fontWeight: FontWeight.w700),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: AppSpacing.xs),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${_format(_toDouble(food['calories']))} kcal',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  Text(
                    '단 ${_format(_toDouble(food['protein_g']))}g',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.protein,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text(
                    '탄 ${_format(_toDouble(food['carbs_g']))}g',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.carbs,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text(
                    '지 ${_format(_toDouble(food['fat_g']))}g',
                    style: AppTypography.caption.copyWith(color: AppColors.fat),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: List<Widget>.generate(5, (int index) {
                  return Icon(
                    index < stars ? Icons.star : Icons.star_border,
                    size: 14,
                    color: AppColors.warning,
                  );
                }),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectedTotalCard extends StatelessWidget {
  final List<Map<String, dynamic>> foods;
  final Set<int> selectedIndexes;

  const _SelectedTotalCard({
    required this.foods,
    required this.selectedIndexes,
  });

  @override
  Widget build(BuildContext context) {
    double calories = 0;
    double protein = 0;
    double carbs = 0;
    double fat = 0;

    for (final int index in selectedIndexes) {
      if (index < 0 || index >= foods.length) {
        continue;
      }
      final Map<String, dynamic> food = foods[index];
      calories += _toDouble(food['calories']);
      protein += _toDouble(food['protein_g']);
      carbs += _toDouble(food['carbs_g']);
      fat += _toDouble(food['fat_g']);
    }

    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('선택 합계', style: AppTypography.h3),
            const SizedBox(height: AppSpacing.xs),
            Text('${_format(calories)} kcal', style: AppTypography.body1),
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                Text(
                  '단 ${_format(protein)}g',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.protein,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '탄 ${_format(carbs)}g',
                  style: AppTypography.caption.copyWith(color: AppColors.carbs),
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '지 ${_format(fat)}g',
                  style: AppTypography.caption.copyWith(color: AppColors.fat),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return error.toString();
}

double _toDouble(dynamic value) {
  if (value == null) {
    return 0;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString()) ?? 0;
}

double? _toDoubleOrNull(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

String? _nullableString(dynamic value) {
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  if (text.isEmpty) {
    return null;
  }
  return text;
}

String _format(double value) {
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toStringAsFixed(1);
}
