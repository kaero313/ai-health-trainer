import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/exercise_repository.dart';
import '../domain/exercise_controller.dart';

const Map<String, String> kExerciseMuscleGroupLabels = <String, String>{
  'chest': '가슴',
  'back': '등',
  'shoulder': '어깨',
  'legs': '하체',
  'arms': '팔',
  'core': '코어',
  'cardio': '유산소',
  'full_body': '전신',
};

const List<String> kExerciseMuscleGroupOrder = <String>[
  'chest',
  'back',
  'shoulder',
  'legs',
  'arms',
  'core',
  'cardio',
  'full_body',
];

class ExerciseAddScreen extends ConsumerStatefulWidget {
  final String? exerciseName;
  final String? muscleGroup;
  final int? sets;
  final int? reps;
  final double? weightKg;

  // ignore: prefer_const_constructors_in_immutables
  ExerciseAddScreen({
    super.key,
    this.exerciseName,
    this.muscleGroup,
    this.sets,
    this.reps,
    this.weightKg,
  });

  @override
  ConsumerState<ExerciseAddScreen> createState() => _ExerciseAddScreenState();
}

class _ExerciseAddScreenState extends ConsumerState<ExerciseAddScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _setsController = TextEditingController(
    text: '3',
  );
  final TextEditingController _repsController = TextEditingController(
    text: '10',
  );
  final TextEditingController _weightController = TextEditingController();
  final TextEditingController _memoController = TextEditingController();

  late DateTime _selectedDate;
  String _selectedMuscleGroup = kExerciseMuscleGroupOrder.first;

  bool _isSaving = false;
  String? _nameError;
  String? _setsError;
  String? _repsError;
  String? _weightError;
  String? _submitError;

  @override
  void initState() {
    super.initState();
    _selectedDate = ref.read(exerciseDateProvider);
    _applyPrefill();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _setsController.dispose();
    _repsController.dispose();
    _weightController.dispose();
    _memoController.dispose();
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

  String? _validateExerciseName(String value) {
    if (value.trim().isEmpty) {
      return '운동명을 입력해주세요.';
    }
    return null;
  }

  String? _validatePositiveInt(String value, String label) {
    if (value.trim().isEmpty) {
      return '$label 입력해주세요.';
    }
    final int? parsed = int.tryParse(value.trim());
    if (parsed == null) {
      return '$label 숫자로 입력해주세요.';
    }
    if (parsed <= 0) {
      return '$label 1 이상이어야 합니다.';
    }
    return null;
  }

  String? _validateWeight(String value) {
    if (value.trim().isEmpty) {
      return null;
    }
    final double? parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return '무게는 숫자로 입력해주세요.';
    }
    if (parsed < 0) {
      return '무게는 0 이상이어야 합니다.';
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
    final String? nameError = _validateExerciseName(_nameController.text);
    final String? setsError = _validatePositiveInt(_setsController.text, '세트수');
    final String? repsError = _validatePositiveInt(_repsController.text, '횟수');
    final String? weightError = _validateWeight(_weightController.text);

    setState(() {
      _nameError = nameError;
      _setsError = setsError;
      _repsError = repsError;
      _weightError = weightError;
      _submitError = null;
    });

    if (nameError != null ||
        setsError != null ||
        repsError != null ||
        weightError != null) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final int setsCount = int.parse(_setsController.text.trim());
    final int repsCount = int.parse(_repsController.text.trim());
    final String weightText = _weightController.text.trim();
    final double? weight =
        weightText.isEmpty ? null : double.parse(_weightController.text.trim());

    final List<Map<String, dynamic>> sets = List<Map<String, dynamic>>.generate(
      setsCount,
      (int index) => <String, dynamic>{
        'set_number': index + 1,
        'reps': repsCount,
        'weight_kg': weight,
        'is_completed': true,
      },
    );

    final Map<String, dynamic> payload = <String, dynamic>{
      'exercise_date': DateFormat('yyyy-MM-dd').format(_selectedDate),
      'exercise_name': _nameController.text.trim(),
      'muscle_group': _selectedMuscleGroup,
      'memo': _nullableText(_memoController.text),
      'sets': sets,
    };

    try {
      await ref.read(exerciseRepositoryProvider).createExerciseLog(payload);
      ref.read(exerciseDateProvider.notifier).state = _selectedDate;
      ref.invalidate(exerciseLogsProvider);
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
      appBar: AppBar(title: const Text('운동 추가')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('운동명', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _nameController,
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 벤치프레스'),
                onChanged: (String value) {
                  setState(() {
                    _nameError = _validateExerciseName(value);
                    _submitError = null;
                  });
                },
              ),
              if (_nameError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _nameError!,
                  style: AppTypography.caption.copyWith(color: AppColors.error),
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              Text('근육군', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              DropdownButtonFormField<String>(
                value: _selectedMuscleGroup,
                decoration: _inputDecoration(hintText: '근육군 선택'),
                dropdownColor: AppColors.surface,
                style: AppTypography.body1,
                items:
                    kExerciseMuscleGroupOrder.map((String muscleGroup) {
                      return DropdownMenuItem<String>(
                        value: muscleGroup,
                        child: Text(
                          kExerciseMuscleGroupLabels[muscleGroup] ??
                              muscleGroup,
                        ),
                      );
                    }).toList(),
                onChanged: (String? value) {
                  if (value == null) {
                    return;
                  }
                  setState(() {
                    _selectedMuscleGroup = value;
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
              Row(
                children: [
                  Expanded(
                    child: _NumberInputField(
                      label: '세트수',
                      hint: '3',
                      controller: _setsController,
                      errorText: _setsError,
                      keyboardType: TextInputType.number,
                      onChanged: (String value) {
                        setState(() {
                          _setsError = _validatePositiveInt(value, '세트수');
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _NumberInputField(
                      label: '횟수',
                      hint: '10',
                      controller: _repsController,
                      errorText: _repsError,
                      keyboardType: TextInputType.number,
                      onChanged: (String value) {
                        setState(() {
                          _repsError = _validatePositiveInt(value, '횟수');
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: _NumberInputField(
                      label: '무게 (kg)',
                      hint: '60.0',
                      controller: _weightController,
                      errorText: _weightError,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      onChanged: (String value) {
                        setState(() {
                          _weightError = _validateWeight(value);
                          _submitError = null;
                        });
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Text('메모 (선택)', style: AppTypography.body2),
              const SizedBox(height: AppSpacing.xs),
              TextField(
                controller: _memoController,
                maxLines: 3,
                style: AppTypography.body1,
                decoration: _inputDecoration(hintText: '예: 마지막 세트가 힘들었음'),
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

  void _applyPrefill() {
    final String? exerciseName = widget.exerciseName;
    if (exerciseName != null && exerciseName.trim().isNotEmpty) {
      _nameController.text = exerciseName.trim();
    }

    final String? muscleGroup = widget.muscleGroup;
    if (muscleGroup != null &&
        kExerciseMuscleGroupOrder.contains(muscleGroup.trim())) {
      _selectedMuscleGroup = muscleGroup.trim();
    }

    final int? sets = widget.sets;
    if (sets != null && sets > 0) {
      _setsController.text = sets.toString();
    }

    final int? reps = widget.reps;
    if (reps != null && reps > 0) {
      _repsController.text = reps.toString();
    }

    final double? weightKg = widget.weightKg;
    if (weightKg != null && weightKg >= 0) {
      _weightController.text = _formatWeight(weightKg);
    }
  }
}

class _NumberInputField extends StatelessWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final String? errorText;
  final TextInputType keyboardType;
  final ValueChanged<String> onChanged;

  const _NumberInputField({
    required this.label,
    required this.hint,
    required this.controller,
    required this.errorText,
    required this.keyboardType,
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
          keyboardType: keyboardType,
          style: AppTypography.body1,
          onChanged: onChanged,
          decoration: InputDecoration(
            hintText: hint,
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

String? _nullableText(String value) {
  final String trimmed = value.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

String _extractErrorMessage(Object error) {
  if (error is ExerciseRepositoryException) {
    return error.message;
  }
  return error.toString();
}

String _formatWeight(double value) {
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toStringAsFixed(1);
}
