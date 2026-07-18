import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
import '../data/auth_repository.dart';
import '../domain/auth_controller.dart';
import 'auth_layout.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _passwordConfirmController =
      TextEditingController();

  bool _obscurePassword = true;
  bool _obscurePasswordConfirm = true;
  String? _emailError;
  String? _passwordError;
  String? _passwordConfirmError;
  String? _submitError;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _passwordConfirmController.dispose();
    super.dispose();
  }

  String? _validateEmail(String value) {
    final String email = value.trim();
    if (email.isEmpty) return '이메일을 입력해 주세요.';
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email)) {
      return '올바른 이메일 형식을 입력해 주세요.';
    }
    return null;
  }

  String? _validatePassword(String value) {
    if (value.isEmpty) return '비밀번호를 입력해 주세요.';
    if (!RegExp(
      r'^(?=.*[a-zA-Z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{8,}$',
    ).hasMatch(value)) {
      return '8자 이상이며 영문, 숫자, 특수문자를 포함해야 합니다.';
    }
    return null;
  }

  String? _validatePasswordConfirm(String value) {
    if (value.isEmpty) return '비밀번호를 다시 입력해 주세요.';
    return value == _passwordController.text ? null : '비밀번호가 일치하지 않습니다.';
  }

  Future<void> _submit() async {
    final String? emailError = _validateEmail(_emailController.text);
    final String? passwordError = _validatePassword(_passwordController.text);
    final String? confirmError = _validatePasswordConfirm(
      _passwordConfirmController.text,
    );
    setState(() {
      _emailError = emailError;
      _passwordError = passwordError;
      _passwordConfirmError = confirmError;
      _submitError = null;
    });
    if (emailError != null || passwordError != null || confirmError != null) {
      return;
    }

    try {
      await ref
          .read(authControllerProvider.notifier)
          .register(
            _emailController.text.trim(),
            _passwordController.text,
            _passwordConfirmController.text,
          );
      if (mounted) context.go('/dashboard');
    } catch (error) {
      if (mounted) {
        setState(() => _submitError = _extractRegisterError(error));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isLoading = ref.watch(authControllerProvider).isLoading;
    return AuthSurface(
      imageAsset: 'assets/stitch/workout_squat.jpg',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AuthBrand(
            title: '코칭을 시작할 준비가 됐습니다',
            subtitle: '계정을 만들고 개인 목표를 설정하세요.',
          ),
          const SizedBox(height: AppSpacing.lg),
          NeoGlassCard(
            highlighted: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _RegisterField(
                  controller: _emailController,
                  label: '이메일',
                  errorText: _emailError,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  icon: Icons.mail_outline,
                  onChanged: (String value) {
                    setState(() {
                      _emailError = _validateEmail(value);
                      _submitError = null;
                    });
                  },
                ),
                const SizedBox(height: AppSpacing.md),
                _RegisterField(
                  controller: _passwordController,
                  label: '비밀번호',
                  errorText: _passwordError,
                  obscureText: _obscurePassword,
                  textInputAction: TextInputAction.next,
                  icon: Icons.lock_outline,
                  suffix: IconButton(
                    tooltip: _obscurePassword ? '비밀번호 표시' : '비밀번호 숨기기',
                    onPressed: () {
                      setState(() => _obscurePassword = !_obscurePassword);
                    },
                    icon: Icon(
                      _obscurePassword
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                    ),
                  ),
                  onChanged: (String value) {
                    setState(() {
                      _passwordError = _validatePassword(value);
                      _passwordConfirmError = _validatePasswordConfirm(
                        _passwordConfirmController.text,
                      );
                      _submitError = null;
                    });
                  },
                ),
                const SizedBox(height: AppSpacing.md),
                _RegisterField(
                  controller: _passwordConfirmController,
                  label: '비밀번호 확인',
                  errorText: _passwordConfirmError,
                  obscureText: _obscurePasswordConfirm,
                  textInputAction: TextInputAction.done,
                  icon: Icons.verified_user_outlined,
                  suffix: IconButton(
                    tooltip: _obscurePasswordConfirm ? '비밀번호 표시' : '비밀번호 숨기기',
                    onPressed: () {
                      setState(
                        () =>
                            _obscurePasswordConfirm = !_obscurePasswordConfirm,
                      );
                    },
                    icon: Icon(
                      _obscurePasswordConfirm
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                    ),
                  ),
                  onChanged: (String value) {
                    setState(() {
                      _passwordConfirmError = _validatePasswordConfirm(value);
                      _submitError = null;
                    });
                  },
                  onSubmitted: (_) => isLoading ? null : _submit(),
                ),
                if (_submitError != null) ...[
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    _submitError!,
                    style: AppTypography.body2.copyWith(color: AppColors.error),
                  ),
                ],
                const SizedBox(height: AppSpacing.lg),
                NeoPrimaryButton(
                  label: isLoading ? '가입 중' : '회원가입',
                  icon: Icons.person_add_alt_1,
                  onPressed: isLoading ? null : _submit,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '이미 계정이 있나요?',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              TextButton(
                onPressed: () => context.go('/login'),
                child: Text(
                  '로그인',
                  style: AppTypography.body2.copyWith(color: AppColors.primary),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RegisterField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final String? errorText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final TextInputAction textInputAction;
  final IconData icon;
  final Widget? suffix;
  final ValueChanged<String> onChanged;
  final ValueChanged<String>? onSubmitted;

  const _RegisterField({
    required this.controller,
    required this.label,
    required this.errorText,
    required this.textInputAction,
    required this.icon,
    required this.onChanged,
    this.obscureText = false,
    this.keyboardType,
    this.suffix,
    this.onSubmitted,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      style: AppTypography.body1,
      onChanged: onChanged,
      onSubmitted: onSubmitted,
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
        prefixIcon: Icon(icon),
        suffixIcon: suffix,
      ),
    );
  }
}

String _extractRegisterError(Object error) {
  if (error is AuthRepositoryException) return error.message;
  return '회원가입에 실패했습니다. 잠시 후 다시 시도해 주세요.';
}
