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
  final TextEditingController _memoController = TextEditingController();
  final List<_SetInputState> _setInputs = <_SetInputState>[];

  late DateTime _selectedDate;
  String _selectedMuscleGroup = kExerciseMuscleGroupOrder.first;

  bool _isSaving = false;
  String? _nameError;
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
    _memoController.dispose();
    _disposeSetInputs();
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
      return '$label를 입력해주세요.';
    }
    final int? parsed = int.tryParse(value.trim());
    if (parsed == null) {
      return '$label는 숫자로 입력해주세요.';
    }
    if (parsed <= 0) {
      return '$label는 1 이상이어야 합니다.';
    }
    return null;
  }

  String? _validateWeight(String value, {String label = '무게'}) {
    if (value.trim().isEmpty) {
      return null;
    }
    final double? parsed = double.tryParse(value.trim());
    if (parsed == null) {
      return '$label는 숫자로 입력해주세요.';
    }
    if (parsed < 0) {
      return '$label는 0 이상이어야 합니다.';
    }
    return null;
  }

  void _addSetInput() {
    final String repsText =
        _setInputs.isEmpty || _setInputs.last.repsController.text.trim().isEmpty
            ? '10'
            : _setInputs.last.repsController.text.trim();
    final String weightText =
        _setInputs.isEmpty ? '' : _setInputs.last.weightController.text.trim();
    setState(() {
      _setInputs.add(
        _SetInputState(repsText: repsText, weightText: weightText),
      );
      _submitError = null;
    });
  }

  void _removeSetInput(int index) {
    if (_setInputs.length <= 1) {
      return;
    }
    setState(() {
      final _SetInputState removed = _setInputs.removeAt(index);
      removed.dispose();
      _submitError = null;
    });
  }

  List<Map<String, dynamic>>? _buildSetsPayload() {
    bool hasError = false;
    final List<Map<String, dynamic>> sets = <Map<String, dynamic>>[];

    for (int index = 0; index < _setInputs.length; index += 1) {
      final _SetInputState input = _setInputs[index];
      final String repsLabel = '${index + 1}세트 횟수';
      final String weightLabel = '${index + 1}세트 무게';
      final String? repsError = _validatePositiveInt(
        input.repsController.text,
        repsLabel,
      );
      final String? weightError = _validateWeight(
        input.weightController.text,
        label: weightLabel,
      );
      input.repsError = repsError;
      input.weightError = weightError;

      if (repsError != null || weightError != null) {
        hasError = true;
        continue;
      }

      final String weightText = input.weightController.text.trim();
      sets.add(<String, dynamic>{
        'set_number': index + 1,
        'reps': int.parse(input.repsController.text.trim()),
        'weight_kg': weightText.isEmpty ? null : double.parse(weightText),
        'is_completed': true,
      });
    }

    return hasError ? null : sets;
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
    final List<Map<String, dynamic>>? sets = _buildSetsPayload();

    setState(() {
      _nameError = nameError;
      _submitError = null;
    });

    if (nameError != null || sets == null) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

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
                  Expanded(child: Text('세트별 기록', style: AppTypography.body2)),
                  TextButton.icon(
                    onPressed: _addSetInput,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('세트 추가'),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              for (int index = 0; index < _setInputs.length; index += 1) ...[
                _SetInputRow(
                  setNumber: index + 1,
                  input: _setInputs[index],
                  canRemove: _setInputs.length > 1,
                  onRemove: () => _removeSetInput(index),
                  onRepsChanged: (String value) {
                    setState(() {
                      _setInputs[index].repsError = _validatePositiveInt(
                        value,
                        '${index + 1}세트 횟수',
                      );
                      _submitError = null;
                    });
                  },
                  onWeightChanged: (String value) {
                    setState(() {
                      _setInputs[index].weightError = _validateWeight(
                        value,
                        label: '${index + 1}세트 무게',
                      );
                      _submitError = null;
                    });
                  },
                ),
                if (index != _setInputs.length - 1)
                  const SizedBox(height: AppSpacing.sm),
              ],
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

    final int setCount =
        widget.sets != null && widget.sets! > 0 ? widget.sets! : 1;
    final int repsCount =
        widget.reps != null && widget.reps! > 0 ? widget.reps! : 10;
    final double? weightKg =
        widget.weightKg != null && widget.weightKg! >= 0
            ? widget.weightKg
            : null;
    _replaceSetInputs(
      setCount: setCount,
      repsText: repsCount.toString(),
      weightText: weightKg == null ? '' : _formatWeight(weightKg),
    );
  }

  void _replaceSetInputs({
    required int setCount,
    required String repsText,
    required String weightText,
  }) {
    _disposeSetInputs();
    _setInputs.addAll(
      List<_SetInputState>.generate(
        setCount,
        (_) => _SetInputState(repsText: repsText, weightText: weightText),
      ),
    );
  }

  void _disposeSetInputs() {
    for (final _SetInputState input in _setInputs) {
      input.dispose();
    }
    _setInputs.clear();
  }
}

class _SetInputState {
  final TextEditingController repsController;
  final TextEditingController weightController;
  String? repsError;
  String? weightError;

  _SetInputState({required String repsText, String weightText = ''})
    : repsController = TextEditingController(text: repsText),
      weightController = TextEditingController(text: weightText);

  void dispose() {
    repsController.dispose();
    weightController.dispose();
  }
}

class _SetInputRow extends StatelessWidget {
  final int setNumber;
  final _SetInputState input;
  final bool canRemove;
  final VoidCallback onRemove;
  final ValueChanged<String> onRepsChanged;
  final ValueChanged<String> onWeightChanged;

  const _SetInputRow({
    required this.setNumber,
    required this.input,
    required this.canRemove,
    required this.onRemove,
    required this.onRepsChanged,
    required this.onWeightChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.divider),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 48,
              height: 48,
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('$setNumber세트', style: AppTypography.caption),
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: _SetNumberField(
                label: '횟수',
                hint: '10',
                controller: input.repsController,
                errorText: input.repsError,
                keyboardType: TextInputType.number,
                onChanged: onRepsChanged,
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: _SetNumberField(
                label: '무게(kg)',
                hint: '60',
                controller: input.weightController,
                errorText: input.weightError,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                onChanged: onWeightChanged,
              ),
            ),
            IconButton(
              tooltip: '세트 삭제',
              onPressed: canRemove ? onRemove : null,
              icon: const Icon(Icons.delete_outline),
              color: AppColors.textSecondary,
              disabledColor: AppColors.textDisabled,
            ),
          ],
        ),
      ),
    );
  }
}

class _SetNumberField extends StatelessWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final String? errorText;
  final TextInputType keyboardType;
  final ValueChanged<String> onChanged;

  const _SetNumberField({
    required this.label,
    required this.hint,
    required this.controller,
    required this.errorText,
    required this.keyboardType,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      style: AppTypography.body1,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        errorText: errorText,
        errorMaxLines: 2,
        labelStyle: AppTypography.caption.copyWith(
          color: AppColors.textSecondary,
        ),
        hintStyle: AppTypography.body2.copyWith(color: AppColors.textSecondary),
        filled: true,
        fillColor: AppColors.surfaceLight,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.sm,
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
      ),
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
