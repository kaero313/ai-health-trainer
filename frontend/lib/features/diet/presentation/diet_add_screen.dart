import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/diet_repository.dart';
import '../domain/diet_controller.dart';

class DietAddScreen extends ConsumerStatefulWidget {
  final String? mealType;

  const DietAddScreen({super.key, this.mealType});

  @override
  ConsumerState<DietAddScreen> createState() => _DietAddScreenState();
}

class _DietAddScreenState extends ConsumerState<DietAddScreen> {
  static const List<String> _mealTypes = <String>[
    'breakfast',
    'lunch',
    'dinner',
    'snack',
  ];

  final TextEditingController _foodNameController = TextEditingController();
  final TextEditingController _servingSizeController = TextEditingController();
  final TextEditingController _caloriesController = TextEditingController();
  final TextEditingController _proteinController = TextEditingController();
  final TextEditingController _carbsController = TextEditingController();
  final TextEditingController _fatController = TextEditingController();

  late DateTime _selectedDate;
  late String _selectedMealType;
  bool _isSaving = false;

  String? _foodNameError;
  String? _caloriesError;
  String? _proteinError;
  String? _carbsError;
  String? _fatError;
  String? _submitError;

  @override
  void initState() {
    super.initState();
    _selectedMealType = _normalizeMealType(widget.mealType);
    _selectedDate = ref.read(selectedDietDateProvider);
  }

  @override
  void dispose() {
    _foodNameController.dispose();
    _servingSizeController.dispose();
    _caloriesController.dispose();
    _proteinController.dispose();
    _carbsController.dispose();
    _fatController.dispose();
    super.dispose();
  }

  InputDecoration _inputDecoration({
    required String hintText,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      hintText: hintText,
      hintStyle: AppTypography.body2.copyWith(color: AppColors.textSecondary),
      filled: true,
      fillColor: AppColors.surfaceLight,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.md,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.divider),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.error),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.error, width: 1.2),
      ),
      suffixIcon: suffixIcon,
    );
  }

  String? _validateFoodName(String value) {
    if (value.trim().isEmpty) {
      return '음식명을 입력해주세요.';
    }
    return null;
  }

  String? _validateCalories(String value) {
    if (value.trim().isEmpty) {
      return '칼로리를 입력해주세요.';
    }
    final double? parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return '숫자로 입력해주세요.';
    }
    if (parsed < 0) {
      return '0 이상으로 입력해주세요.';
    }
    return null;
  }

  String? _validateOptionalMacro(String value) {
    if (value.trim().isEmpty) {
      return null;
    }
    final double? parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return '숫자로 입력해주세요.';
    }
    if (parsed < 0) {
      return '0 이상으로 입력해주세요.';
    }
    return null;
  }

  Future<void> _pickDate() async {
    final DateTime now = DateTime.now();
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 2),
      locale: const Locale('ko'),
    );
    if (pickedDate == null) {
      return;
    }
    setState(() {
      _selectedDate = pickedDate;
    });
  }

  Future<void> _submit() async {
    final String? foodNameError = _validateFoodName(_foodNameController.text);
    final String? caloriesError = _validateCalories(_caloriesController.text);
    final String? proteinError = _validateOptionalMacro(
      _proteinController.text,
    );
    final String? carbsError = _validateOptionalMacro(_carbsController.text);
    final String? fatError = _validateOptionalMacro(_fatController.text);

    setState(() {
      _foodNameError = foodNameError;
      _caloriesError = caloriesError;
      _proteinError = proteinError;
      _carbsError = carbsError;
      _fatError = fatError;
      _submitError = null;
    });

    if (foodNameError != null ||
        caloriesError != null ||
        proteinError != null ||
        carbsError != null ||
        fatError != null) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final Map<String, dynamic> payload = <String, dynamic>{
      'log_date': DateFormat('yyyy-MM-dd').format(_selectedDate),
      'meal_type': _selectedMealType,
      'image_url': null,
      'items': <Map<String, dynamic>>[
        <String, dynamic>{
          'food_name': _foodNameController.text.trim(),
          'serving_size': _nullableText(_servingSizeController.text),
          'calories': double.parse(_caloriesController.text.trim()),
          'protein_g': _parseMacroOrZero(_proteinController.text),
          'carbs_g': _parseMacroOrZero(_carbsController.text),
          'fat_g': _parseMacroOrZero(_fatController.text),
        },
      ],
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
        _submitError = _extractErrorMessage(e);
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
      appBar: AppBar(title: const Text('식단 수동 추가')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('음식명', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _foodNameController,
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 닭가슴살 샐러드'),
                onChanged: (String value) {
                  setState(() {
                    _foodNameError = _validateFoodName(value);
                    _submitError = null;
                  });
                },
              ),
              if (_foodNameError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _foodNameError!,
                  style: AppTypography.caption.copyWith(color: AppColors.error),
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              Text('식사시간', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              DropdownButtonFormField<String>(
                value: _selectedMealType,
                decoration: _inputDecoration(hintText: '식사시간 선택'),
                dropdownColor: AppColors.surface,
                style: AppTypography.body1,
                items:
                    _mealTypes.map((String mealType) {
                      return DropdownMenuItem<String>(
                        value: mealType,
                        child: Text(_mealTypeLabel(mealType)),
                      );
                    }).toList(),
                onChanged: (String? value) {
                  if (value == null) {
                    return;
                  }
                  setState(() {
                    _selectedMealType = value;
                  });
                },
              ),
              const SizedBox(height: AppSpacing.md),
              Text('날짜', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              InkWell(
                borderRadius: BorderRadius.circular(AppRadius.md),
                onTap: _pickDate,
                child: InputDecorator(
                  decoration: _inputDecoration(
                    hintText: '날짜 선택',
                    suffixIcon: const Icon(
                      Icons.calendar_today,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  child: Text(
                    DateFormat('yyyy-MM-dd').format(_selectedDate),
                    style: AppTypography.body1,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text('1회분량 (선택)', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _servingSizeController,
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 1인분, 200g'),
              ),
              const SizedBox(height: AppSpacing.md),
              Text('칼로리 (kcal)', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _caloriesController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 350'),
                onChanged: (String value) {
                  setState(() {
                    _caloriesError = _validateCalories(value);
                    _submitError = null;
                  });
                },
              ),
              if (_caloriesError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _caloriesError!,
                  style: AppTypography.caption.copyWith(color: AppColors.error),
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Expanded(
                    child: _MacroInput(
                      label: '단백질 (g)',
                      controller: _proteinController,
                      errorText: _proteinError,
                      onChanged: (String value) {
                        setState(() {
                          _proteinError = _validateOptionalMacro(value);
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _MacroInput(
                      label: '탄수화물 (g)',
                      controller: _carbsController,
                      errorText: _carbsError,
                      onChanged: (String value) {
                        setState(() {
                          _carbsError = _validateOptionalMacro(value);
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _MacroInput(
                      label: '지방 (g)',
                      controller: _fatController,
                      errorText: _fatError,
                      onChanged: (String value) {
                        setState(() {
                          _fatError = _validateOptionalMacro(value);
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.lg),
              if (_submitError != null) ...[
                Text(
                  _submitError!,
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
                        onTap: _isSaving ? null : _submit,
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
                                    '저장하기',
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
            ],
          ),
        ),
      ),
    );
  }
}

class _MacroInput extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final String? errorText;
  final ValueChanged<String> onChanged;

  const _MacroInput({
    required this.label,
    required this.controller,
    required this.errorText,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTypography.caption),
        const SizedBox(height: AppSpacing.xs),
        TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          style: AppTypography.body1,
          onChanged: onChanged,
          decoration: InputDecoration(
            hintText: '0',
            hintStyle: AppTypography.body2.copyWith(
              color: AppColors.textSecondary,
            ),
            filled: true,
            fillColor: AppColors.surfaceLight,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.md,
            ),
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
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: const BorderSide(color: AppColors.error),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: const BorderSide(color: AppColors.error, width: 1.2),
            ),
          ),
        ),
        if (errorText != null) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            errorText!,
            style: AppTypography.caption.copyWith(color: AppColors.error),
          ),
        ],
      ],
    );
  }
}

String _normalizeMealType(String? mealType) {
  switch (mealType) {
    case 'breakfast':
    case 'lunch':
    case 'dinner':
    case 'snack':
      return mealType!;
    default:
      return 'breakfast';
  }
}

String _mealTypeLabel(String mealType) {
  switch (mealType) {
    case 'breakfast':
      return '아침';
    case 'lunch':
      return '점심';
    case 'dinner':
      return '저녁';
    case 'snack':
      return '간식';
    default:
      return mealType;
  }
}

double _parseMacroOrZero(String rawValue) {
  final String trimmed = rawValue.trim();
  if (trimmed.isEmpty) {
    return 0;
  }
  return double.tryParse(trimmed) ?? 0;
}

String? _nullableText(String rawValue) {
  final String trimmed = rawValue.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return error.toString();
}
