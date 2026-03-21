import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/profile_repository.dart';
import '../domain/profile_check_provider.dart';
import '../domain/profile_controller.dart';

class ProfileEditScreen extends ConsumerStatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  ConsumerState<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends ConsumerState<ProfileEditScreen> {
  final TextEditingController _heightController = TextEditingController();
  final TextEditingController _weightController = TextEditingController();
  final TextEditingController _ageController = TextEditingController();
  final TextEditingController _allergyInputController = TextEditingController();
  final TextEditingController _preferenceInputController = TextEditingController();

  String _gender = 'male';
  String _goal = 'maintain';
  String _activityLevel = 'moderate';

  List<String> _allergies = <String>[];
  List<String> _foodPreferences = <String>[];

  bool _initializedFromData = false;
  bool _isInitialSetupMode = false;
  bool _isSubmitting = false;

  String? _heightError;
  String? _weightError;
  String? _ageError;
  String? _submitError;

  @override
  void dispose() {
    _heightController.dispose();
    _weightController.dispose();
    _ageController.dispose();
    _allergyInputController.dispose();
    _preferenceInputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<Map<String, dynamic>> profileAsync = ref.watch(
      profileControllerProvider,
    );

    final Object? error = profileAsync.asError?.error;
    final bool isNotFound = error is ProfileRepositoryException && error.statusCode == 404;
    final bool isInitialLoading = profileAsync.isLoading && !_initializedFromData;
    final bool hasUnhandledError = error != null && !isNotFound && !_initializedFromData;

    if (!_initializedFromData && profileAsync.hasValue) {
      _applyInitialValues(profileAsync.requireValue);
    }
    if (!_initializedFromData && isNotFound) {
      _initializedFromData = true;
      _isInitialSetupMode = true;
    }

    final bool isInitialSetupMode = _isInitialSetupMode;
    final String screenTitle = isInitialSetupMode ? '프로필 설정' : '프로필 수정';
    final Widget? screenLeading = isInitialSetupMode ? const SizedBox.shrink() : null;

    if (isInitialLoading) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          title: Text(screenTitle),
          leading: screenLeading,
        ),
        body: const Center(
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
      );
    }

    if (hasUnhandledError) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          title: Text(screenTitle),
          leading: screenLeading,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _extractErrorMessage(error),
                  style: AppTypography.body2.copyWith(color: AppColors.error),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.md),
                TextButton(
                  onPressed: () => ref.invalidate(profileControllerProvider),
                  child: Text(
                    '다시 시도',
                    style: AppTypography.body2.copyWith(color: AppColors.primary),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(screenTitle),
        leading: screenLeading,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (isInitialSetupMode) ...[
              _buildInitialSetupNotice(),
              const SizedBox(height: AppSpacing.lg),
            ],
            _buildNumericField(
              controller: _heightController,
              hintText: '키 (cm)',
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              errorText: _heightError,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildNumericField(
              controller: _weightController,
              hintText: '몸무게 (kg)',
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              errorText: _weightError,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildNumericField(
              controller: _ageController,
              hintText: '나이',
              keyboardType: TextInputType.number,
              errorText: _ageError,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildDropdownField(
              label: '성별',
              value: _gender,
              items: const <MapEntry<String, String>>[
                MapEntry<String, String>('male', '남성'),
                MapEntry<String, String>('female', '여성'),
                MapEntry<String, String>('other', '기타'),
              ],
              onChanged: (String value) {
                setState(() {
                  _gender = value;
                });
              },
            ),
            const SizedBox(height: AppSpacing.md),
            _buildDropdownField(
              label: '목표',
              value: _goal,
              items: const <MapEntry<String, String>>[
                MapEntry<String, String>('bulk', '벌크업'),
                MapEntry<String, String>('diet', '다이어트'),
                MapEntry<String, String>('maintain', '유지'),
              ],
              onChanged: (String value) {
                setState(() {
                  _goal = value;
                });
              },
            ),
            const SizedBox(height: AppSpacing.md),
            _buildDropdownField(
              label: '활동 수준',
              value: _activityLevel,
              items: const <MapEntry<String, String>>[
                MapEntry<String, String>('sedentary', '비활동적'),
                MapEntry<String, String>('light', '가벼운'),
                MapEntry<String, String>('moderate', '보통 (주 3~5)'),
                MapEntry<String, String>('active', '활발 (주 6~7)'),
                MapEntry<String, String>('very_active', '매우 활발'),
              ],
              onChanged: (String value) {
                setState(() {
                  _activityLevel = value;
                });
              },
            ),
            const SizedBox(height: AppSpacing.lg),
            _buildTagEditor(
              title: '알레르기',
              inputController: _allergyInputController,
              tags: _allergies,
              onAdd: _addAllergy,
              onRemove: _removeAllergy,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildTagEditor(
              title: '선호 식품',
              inputController: _preferenceInputController,
              tags: _foodPreferences,
              onAdd: _addPreference,
              onRemove: _removePreference,
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
              opacity: _isSubmitting ? 0.7 : 1,
              child: SizedBox(
                height: 52,
                child: DecoratedBox(
                  decoration: primaryButtonDecoration,
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      onTap: _isSubmitting ? null : _submit,
                      child: Center(
                        child: _isSubmitting
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
    );
  }

  Widget _buildInitialSetupNotice() {
    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          children: [
            const Icon(
              Icons.person_outline,
              color: AppColors.textSecondary,
              size: 24,
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                '프로필을 먼저 설정해주세요.',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNumericField({
    required TextEditingController controller,
    required String hintText,
    required TextInputType keyboardType,
    required String? errorText,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          style: AppTypography.body1,
          onChanged: (_) {
            setState(() {
              _submitError = null;
            });
          },
          decoration: _inputDecoration(hintText: hintText),
        ),
        if (errorText != null) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            errorText,
            style: AppTypography.caption.copyWith(color: AppColors.error),
          ),
        ],
      ],
    );
  }

  Widget _buildDropdownField({
    required String label,
    required String value,
    required List<MapEntry<String, String>> items,
    required ValueChanged<String> onChanged,
  }) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.divider),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: value,
            isExpanded: true,
            dropdownColor: AppColors.surface,
            style: AppTypography.body1,
            iconEnabledColor: AppColors.textSecondary,
            items: items
                .map(
                  (MapEntry<String, String> item) => DropdownMenuItem<String>(
                    value: item.key,
                    child: Text('$label: ${item.value}'),
                  ),
                )
                .toList(),
            onChanged: (String? newValue) {
              if (newValue != null) {
                onChanged(newValue);
              }
            },
          ),
        ),
      ),
    );
  }

  Widget _buildTagEditor({
    required String title,
    required TextEditingController inputController,
    required List<String> tags,
    required VoidCallback onAdd,
    required ValueChanged<String> onRemove,
  }) {
    return DecoratedBox(
      decoration: cardDecoration,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: AppTypography.h3),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: inputController,
                    style: AppTypography.body1,
                    decoration: _inputDecoration(hintText: '$title 추가'),
                    onSubmitted: (_) => onAdd(),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                IconButton(
                  onPressed: onAdd,
                  icon: const Icon(Icons.add, color: AppColors.primary),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            if (tags.isEmpty)
              Text(
                '없음',
                style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
              )
            else
              Wrap(
                spacing: AppSpacing.xs,
                runSpacing: AppSpacing.xs,
                children: tags
                    .map(
                      (String tag) => Chip(
                        backgroundColor: AppColors.surfaceLight,
                        side: BorderSide.none,
                        label: Text(
                          tag,
                          style: AppTypography.caption.copyWith(
                            color: AppColors.textPrimary,
                          ),
                        ),
                        deleteIcon: const Icon(
                          Icons.close,
                          size: 16,
                          color: AppColors.textSecondary,
                        ),
                        onDeleted: () => onRemove(tag),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  InputDecoration _inputDecoration({required String hintText}) {
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
    );
  }

  void _applyInitialValues(Map<String, dynamic> data) {
    _heightController.text = (data['height_cm'] ?? '').toString();
    _weightController.text = (data['weight_kg'] ?? '').toString();
    _ageController.text = (data['age'] ?? '').toString();

    _gender = _validatedOrDefault(
      data['gender']?.toString(),
      const <String>{'male', 'female', 'other'},
      'male',
    );
    _goal = _validatedOrDefault(
      data['goal']?.toString(),
      const <String>{'bulk', 'diet', 'maintain'},
      'maintain',
    );
    _activityLevel = _validatedOrDefault(
      data['activity_level']?.toString(),
      const <String>{'sedentary', 'light', 'moderate', 'active', 'very_active'},
      'moderate',
    );

    _allergies = (data['allergies'] as List<dynamic>? ?? <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();
    _foodPreferences = (data['food_preferences'] as List<dynamic>? ?? <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();

    _isInitialSetupMode = false;
    _initializedFromData = true;
  }

  String _validatedOrDefault(
    String? value,
    Set<String> allowed,
    String fallback,
  ) {
    if (value != null && allowed.contains(value)) {
      return value;
    }
    return fallback;
  }

  void _addAllergy() {
    final String value = _allergyInputController.text.trim();
    if (value.isEmpty || _allergies.contains(value)) {
      return;
    }
    setState(() {
      _allergies = <String>[..._allergies, value];
      _allergyInputController.clear();
      _submitError = null;
    });
  }

  void _removeAllergy(String value) {
    setState(() {
      _allergies = _allergies.where((String item) => item != value).toList();
      _submitError = null;
    });
  }

  void _addPreference() {
    final String value = _preferenceInputController.text.trim();
    if (value.isEmpty || _foodPreferences.contains(value)) {
      return;
    }
    setState(() {
      _foodPreferences = <String>[..._foodPreferences, value];
      _preferenceInputController.clear();
      _submitError = null;
    });
  }

  void _removePreference(String value) {
    setState(() {
      _foodPreferences = _foodPreferences.where((String item) => item != value).toList();
      _submitError = null;
    });
  }

  Future<void> _submit() async {
    final String? heightError = _validateHeight(_heightController.text);
    final String? weightError = _validateWeight(_weightController.text);
    final String? ageError = _validateAge(_ageController.text);

    setState(() {
      _heightError = heightError;
      _weightError = weightError;
      _ageError = ageError;
      _submitError = null;
    });

    if (heightError != null || weightError != null || ageError != null) {
      return;
    }

    final Map<String, dynamic> payload = <String, dynamic>{
      'height_cm': double.parse(_heightController.text.trim()),
      'weight_kg': double.parse(_weightController.text.trim()),
      'age': int.parse(_ageController.text.trim()),
      'gender': _gender,
      'goal': _goal,
      'activity_level': _activityLevel,
      'allergies': _allergies,
      'food_preferences': _foodPreferences,
    };

    setState(() {
      _isSubmitting = true;
    });

    try {
      final bool wasInitialSetupMode = _isInitialSetupMode;
      await ref.read(profileControllerProvider.notifier).updateProfile(payload);
      ref.invalidate(profileCheckProvider);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('프로필이 저장되었습니다.')),
      );
      if (wasInitialSetupMode) {
        context.go('/dashboard');
      } else {
        context.pop();
      }
    } catch (e) {
      setState(() {
        _submitError = _extractErrorMessage(e);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  String? _validateHeight(String raw) {
    final double? value = double.tryParse(raw.trim());
    if (value == null) {
      return '키를 숫자로 입력해주세요.';
    }
    if (value < 100 || value > 250) {
      return '키는 100~250cm 범위여야 합니다.';
    }
    return null;
  }

  String? _validateWeight(String raw) {
    final double? value = double.tryParse(raw.trim());
    if (value == null) {
      return '몸무게를 숫자로 입력해주세요.';
    }
    if (value < 30 || value > 300) {
      return '몸무게는 30~300kg 범위여야 합니다.';
    }
    return null;
  }

  String? _validateAge(String raw) {
    final int? value = int.tryParse(raw.trim());
    if (value == null) {
      return '나이를 숫자로 입력해주세요.';
    }
    if (value < 10 || value > 100) {
      return '나이는 10~100 범위여야 합니다.';
    }
    return null;
  }

  String _extractErrorMessage(Object error) {
    if (error is ProfileRepositoryException) {
      return error.message;
    }
    final String raw = error.toString();
    if (raw.startsWith('Exception: ')) {
      return raw.replaceFirst('Exception: ', '');
    }
    return raw;
  }
}
