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
  final TextEditingController _servingGramsController = TextEditingController();
  final TextEditingController _caloriesController = TextEditingController();
  final TextEditingController _proteinController = TextEditingController();
  final TextEditingController _carbsController = TextEditingController();
  final TextEditingController _fatController = TextEditingController();
  final TextEditingController _sugarController = TextEditingController();
  final TextEditingController _saturatedFatController = TextEditingController();
  final TextEditingController _unsaturatedFatController =
      TextEditingController();

  late DateTime _selectedDate;
  late String _selectedMealType;
  bool _isSaving = false;
  bool _isSearchingFoods = false;
  bool _autoCalculateFromCatalog = false;
  int _foodSearchGeneration = 0;
  Map<String, dynamic>? _selectedFood;
  List<Map<String, dynamic>> _foodSuggestions = <Map<String, dynamic>>[];

  String? _foodNameError;
  String? _servingGramsError;
  String? _caloriesError;
  String? _proteinError;
  String? _carbsError;
  String? _fatError;
  String? _sugarError;
  String? _saturatedFatError;
  String? _unsaturatedFatError;
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
    _servingGramsController.dispose();
    _caloriesController.dispose();
    _proteinController.dispose();
    _carbsController.dispose();
    _fatController.dispose();
    _sugarController.dispose();
    _saturatedFatController.dispose();
    _unsaturatedFatController.dispose();
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

  String? _validateOptionalNumber(String value, {String label = '값'}) {
    if (value.trim().isEmpty) {
      return null;
    }
    final double? parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return '$label은 숫자로 입력해주세요.';
    }
    if (parsed < 0) {
      return '$label은 0 이상으로 입력해주세요.';
    }
    return null;
  }

  Future<void> _searchFoods(String query) async {
    final String normalizedQuery = query.trim();
    final int generation = ++_foodSearchGeneration;

    if (normalizedQuery.isEmpty) {
      setState(() {
        _foodSuggestions = <Map<String, dynamic>>[];
        _isSearchingFoods = false;
      });
      return;
    }

    setState(() {
      _isSearchingFoods = true;
    });

    try {
      final List<Map<String, dynamic>> results = await ref
          .read(dietRepositoryProvider)
          .searchFoods(normalizedQuery);
      if (!mounted || generation != _foodSearchGeneration) {
        return;
      }
      setState(() {
        _foodSuggestions = results;
        _isSearchingFoods = false;
      });
    } catch (_) {
      if (!mounted || generation != _foodSearchGeneration) {
        return;
      }
      setState(() {
        _foodSuggestions = <Map<String, dynamic>>[];
        _isSearchingFoods = false;
      });
    }
  }

  void _selectFood(Map<String, dynamic> food) {
    _selectedFood = food;
    _autoCalculateFromCatalog = true;
    _foodNameController.text = food['name']?.toString() ?? '';
    _servingGramsController.text = '100';
    _applySelectedFoodNutrition(100);
    setState(() {
      _foodSuggestions = <Map<String, dynamic>>[];
      _foodNameError = null;
      _servingGramsError = null;
      _caloriesError = null;
      _proteinError = null;
      _carbsError = null;
      _fatError = null;
      _sugarError = null;
      _saturatedFatError = null;
      _unsaturatedFatError = null;
      _submitError = null;
    });
  }

  void _onFoodNameChanged(String value) {
    final String selectedName = _selectedFood?['name']?.toString() ?? '';
    if (selectedName.isNotEmpty && value.trim() != selectedName) {
      _selectedFood = null;
      _autoCalculateFromCatalog = false;
    }
    setState(() {
      _foodNameError = _validateFoodName(value);
      _submitError = null;
    });
    _searchFoods(value);
  }

  void _onServingGramsChanged(String value) {
    final String? error = _validateOptionalNumber(value, label: '섭취량');
    final double? grams = double.tryParse(value.trim());
    if (_selectedFood != null &&
        _autoCalculateFromCatalog &&
        error == null &&
        grams != null) {
      _applySelectedFoodNutrition(grams);
    }
    setState(() {
      _servingGramsError = error;
      _submitError = null;
    });
  }

  void _onManualNutritionChanged(
    TextEditingController controller,
    String? Function(String value) validator,
    void Function(String? error) setError,
  ) {
    setState(() {
      _autoCalculateFromCatalog = false;
      setError(validator(controller.text));
      _submitError = null;
    });
  }

  void _applySelectedFoodNutrition(double servingGrams) {
    final Map<String, dynamic>? food = _selectedFood;
    if (food == null) {
      return;
    }
    final double servingBasis = _toDouble(
      food['serving_basis_g'],
      fallback: 100,
    );
    final double ratio = servingBasis <= 0 ? 1 : servingGrams / servingBasis;

    _caloriesController.text = _formatInputNumber(
      _toDouble(food['calories']) * ratio,
    );
    _proteinController.text = _formatInputNumber(
      _toDouble(food['protein_g']) * ratio,
    );
    _carbsController.text = _formatInputNumber(
      _toDouble(food['carbs_g']) * ratio,
    );
    _fatController.text = _formatInputNumber(_toDouble(food['fat_g']) * ratio);
    _setOptionalNutrition(_sugarController, food['sugar_g'], ratio);
    _setOptionalNutrition(
      _saturatedFatController,
      food['saturated_fat_g'],
      ratio,
    );
    _setOptionalNutrition(
      _unsaturatedFatController,
      food['unsaturated_fat_g'],
      ratio,
    );
  }

  void _setOptionalNutrition(
    TextEditingController controller,
    dynamic value,
    double ratio,
  ) {
    final double? parsed = _toNullableDouble(value);
    controller.text = parsed == null ? '' : _formatInputNumber(parsed * ratio);
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
    final String? servingGramsError = _validateOptionalNumber(
      _servingGramsController.text,
      label: '섭취량',
    );
    final String? caloriesError = _validateCalories(_caloriesController.text);
    final String? proteinError = _validateOptionalNumber(
      _proteinController.text,
      label: '단백질',
    );
    final String? carbsError = _validateOptionalNumber(
      _carbsController.text,
      label: '탄수화물',
    );
    final String? fatError = _validateOptionalNumber(
      _fatController.text,
      label: '지방',
    );
    final String? sugarError = _validateOptionalNumber(
      _sugarController.text,
      label: '당분',
    );
    final String? saturatedFatError = _validateOptionalNumber(
      _saturatedFatController.text,
      label: '포화지방',
    );
    final String? unsaturatedFatError = _validateOptionalNumber(
      _unsaturatedFatController.text,
      label: '불포화지방',
    );

    setState(() {
      _foodNameError = foodNameError;
      _servingGramsError = servingGramsError;
      _caloriesError = caloriesError;
      _proteinError = proteinError;
      _carbsError = carbsError;
      _fatError = fatError;
      _sugarError = sugarError;
      _saturatedFatError = saturatedFatError;
      _unsaturatedFatError = unsaturatedFatError;
      _submitError = null;
    });

    if (foodNameError != null ||
        servingGramsError != null ||
        caloriesError != null ||
        proteinError != null ||
        carbsError != null ||
        fatError != null ||
        sugarError != null ||
        saturatedFatError != null ||
        unsaturatedFatError != null) {
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
          'food_catalog_item_id': _toNullableInt(_selectedFood?['id']),
          'food_name': _foodNameController.text.trim(),
          'serving_size': _servingSizeFromGrams(_servingGramsController.text),
          'serving_grams': _parseNullableNumber(_servingGramsController.text),
          'calories': double.parse(_caloriesController.text.trim()),
          'protein_g': _parseMacroOrZero(_proteinController.text),
          'carbs_g': _parseMacroOrZero(_carbsController.text),
          'fat_g': _parseMacroOrZero(_fatController.text),
          'sugar_g': _parseNullableNumber(_sugarController.text),
          'saturated_fat_g': _parseNullableNumber(_saturatedFatController.text),
          'unsaturated_fat_g': _parseNullableNumber(
            _unsaturatedFatController.text,
          ),
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
                onChanged: _onFoodNameChanged,
              ),
              if (_foodNameError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _foodNameError!,
                  style: AppTypography.caption.copyWith(color: AppColors.error),
                ),
              ],
              if (_isSearchingFoods || _foodSuggestions.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.xs),
                _FoodSuggestionList(
                  isLoading: _isSearchingFoods,
                  suggestions: _foodSuggestions,
                  onSelected: _selectFood,
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
              Text('섭취량 (g)', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _servingGramsController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 100'),
                onChanged: _onServingGramsChanged,
              ),
              if (_servingGramsError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _servingGramsError!,
                  style: AppTypography.caption.copyWith(color: AppColors.error),
                ),
              ],
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
                    _autoCalculateFromCatalog = false;
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
              Text('기본 영양소', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  Expanded(
                    child: _MacroInput(
                      label: '단백질 (g)',
                      controller: _proteinController,
                      errorText: _proteinError,
                      onChanged: (String value) {
                        _onManualNutritionChanged(
                          _proteinController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '단백질'),
                          (String? error) => _proteinError = error,
                        );
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
                        _onManualNutritionChanged(
                          _carbsController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '탄수화물'),
                          (String? error) => _carbsError = error,
                        );
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
                        _onManualNutritionChanged(
                          _fatController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '지방'),
                          (String? error) => _fatError = error,
                        );
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Text('선택 영양소', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  Expanded(
                    child: _MacroInput(
                      label: '당분 (g)',
                      controller: _sugarController,
                      errorText: _sugarError,
                      onChanged: (String value) {
                        _onManualNutritionChanged(
                          _sugarController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '당분'),
                          (String? error) => _sugarError = error,
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _MacroInput(
                      label: '포화 (g)',
                      controller: _saturatedFatController,
                      errorText: _saturatedFatError,
                      onChanged: (String value) {
                        _onManualNutritionChanged(
                          _saturatedFatController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '포화지방'),
                          (String? error) => _saturatedFatError = error,
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _MacroInput(
                      label: '불포화 (g)',
                      controller: _unsaturatedFatController,
                      errorText: _unsaturatedFatError,
                      onChanged: (String value) {
                        _onManualNutritionChanged(
                          _unsaturatedFatController,
                          (String input) =>
                              _validateOptionalNumber(input, label: '불포화지방'),
                          (String? error) => _unsaturatedFatError = error,
                        );
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

class _FoodSuggestionList extends StatelessWidget {
  final bool isLoading;
  final List<Map<String, dynamic>> suggestions;
  final ValueChanged<Map<String, dynamic>> onSelected;

  const _FoodSuggestionList({
    required this.isLoading,
    required this.suggestions,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.surfaceLight,
          border: Border.all(color: AppColors.divider),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isLoading)
              const LinearProgressIndicator(
                minHeight: 2,
                color: AppColors.primary,
                backgroundColor: AppColors.surfaceLight,
              ),
            for (int index = 0; index < suggestions.length; index++) ...[
              if (index > 0) const Divider(height: 1, color: AppColors.divider),
              InkWell(
                onTap: () => onSelected(suggestions[index]),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              suggestions[index]['name']?.toString() ?? '음식',
                              style: AppTypography.body2.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _catalogNutritionSummary(suggestions[index]),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: AppTypography.caption.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        _categoryLabel(
                          suggestions[index]['category']?.toString() ?? '',
                        ),
                        style: AppTypography.caption.copyWith(
                          color: AppColors.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
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

double? _parseNullableNumber(String rawValue) {
  final String trimmed = rawValue.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  return double.tryParse(trimmed);
}

double _toDouble(dynamic value, {double fallback = 0}) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? fallback;
  }
  return fallback;
}

double? _toNullableDouble(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    return double.tryParse(trimmed);
  }
  return null;
}

int? _toNullableInt(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}

String _formatInputNumber(double value) {
  final double rounded = (value * 10).roundToDouble() / 10;
  if (rounded == rounded.truncateToDouble()) {
    return rounded.toInt().toString();
  }
  return rounded.toStringAsFixed(1);
}

String _catalogNutritionSummary(Map<String, dynamic> food) {
  return '100g · ${_formatInputNumber(_toDouble(food['calories']))} kcal · '
      '단 ${_formatInputNumber(_toDouble(food['protein_g']))}g · '
      '탄 ${_formatInputNumber(_toDouble(food['carbs_g']))}g · '
      '지 ${_formatInputNumber(_toDouble(food['fat_g']))}g';
}

String _categoryLabel(String category) {
  switch (category) {
    case 'protein':
      return '단백질';
    case 'carb':
      return '탄수화물';
    case 'fat':
      return '지방';
    case 'fruit':
      return '과일';
    case 'vegetable':
      return '채소';
    case 'dairy':
      return '유제품';
    case 'soup':
      return '국물';
    case 'side':
      return '반찬';
    case 'supplement':
      return '보충제';
    case 'meal':
      return '식사';
    default:
      return '음식';
  }
}

String? _servingSizeFromGrams(String rawValue) {
  final double? grams = _parseNullableNumber(rawValue);
  if (grams == null) {
    return null;
  }
  return '${_formatInputNumber(grams)}g';
}

String _extractErrorMessage(Object error) {
  if (error is DietRepositoryException) {
    return error.message;
  }
  return error.toString();
}
