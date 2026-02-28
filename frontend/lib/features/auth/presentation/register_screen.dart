import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/auth_repository.dart';
import '../domain/auth_controller.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _passwordConfirmController = TextEditingController();

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
    if (email.isEmpty) {
      return '이메일을 입력해주세요.';
    }
    final RegExp emailRegex = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');
    if (!emailRegex.hasMatch(email)) {
      return '유효한 이메일 형식을 입력해주세요.';
    }
    return null;
  }

  String? _validatePassword(String value) {
    if (value.isEmpty) {
      return '비밀번호를 입력해주세요.';
    }
    const String pattern = r'^(?=.*[a-zA-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$';
    final RegExp passwordRegex = RegExp(pattern);
    if (!passwordRegex.hasMatch(value)) {
      return '비밀번호는 8자 이상, 영문/숫자/특수문자를 포함해야 합니다.';
    }
    return null;
  }

  String? _validatePasswordConfirm(String value) {
    if (value.isEmpty) {
      return '비밀번호 확인을 입력해주세요.';
    }
    if (value != _passwordController.text) {
      return '비밀번호가 일치하지 않습니다.';
    }
    return null;
  }

  Future<void> _submit() async {
    final String? emailError = _validateEmail(_emailController.text);
    final String? passwordError = _validatePassword(_passwordController.text);
    final String? passwordConfirmError = _validatePasswordConfirm(
      _passwordConfirmController.text,
    );

    setState(() {
      _emailError = emailError;
      _passwordError = passwordError;
      _passwordConfirmError = passwordConfirmError;
      _submitError = null;
    });

    if (emailError != null || passwordError != null || passwordConfirmError != null) {
      return;
    }

    try {
      await ref.read(authControllerProvider.notifier).register(
            _emailController.text.trim(),
            _passwordController.text,
            _passwordConfirmController.text,
          );
      if (!mounted) {
        return;
      }
      context.go('/dashboard');
    } catch (e) {
      setState(() {
        _submitError = _extractErrorMessage(e);
      });
    }
  }

  String _extractErrorMessage(Object error) {
    if (error is AuthRepositoryException) {
      return error.message;
    }
    final String raw = error.toString();
    if (raw.startsWith('Exception: ')) {
      return raw.replaceFirst('Exception: ', '');
    }
    return raw;
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
      suffixIcon: suffixIcon,
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool isLoading = ref.watch(authControllerProvider).isLoading;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(
                    Icons.fitness_center,
                    size: 64,
                    color: AppColors.primary,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    'AI Health Trainer',
                    textAlign: TextAlign.center,
                    style: AppTypography.h2.copyWith(color: AppColors.primary),
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  TextField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    style: AppTypography.body1,
                    onChanged: (String value) {
                      setState(() {
                        _emailError = _validateEmail(value);
                        _submitError = null;
                      });
                    },
                    decoration: _inputDecoration(hintText: 'user@email.com'),
                  ),
                  if (_emailError != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      _emailError!,
                      style: AppTypography.caption.copyWith(color: AppColors.error),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  TextField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    style: AppTypography.body1,
                    onChanged: (String value) {
                      setState(() {
                        _passwordError = _validatePassword(value);
                        _passwordConfirmError = _validatePasswordConfirm(
                          _passwordConfirmController.text,
                        );
                        _submitError = null;
                      });
                    },
                    decoration: _inputDecoration(
                      hintText: '비밀번호',
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                        icon: Icon(
                          _obscurePassword ? Icons.visibility_off : Icons.visibility,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                  if (_passwordError != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      _passwordError!,
                      style: AppTypography.caption.copyWith(color: AppColors.error),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  TextField(
                    controller: _passwordConfirmController,
                    obscureText: _obscurePasswordConfirm,
                    style: AppTypography.body1,
                    onChanged: (String value) {
                      setState(() {
                        _passwordConfirmError = _validatePasswordConfirm(value);
                        _submitError = null;
                      });
                    },
                    decoration: _inputDecoration(
                      hintText: '비밀번호 확인',
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscurePasswordConfirm = !_obscurePasswordConfirm;
                          });
                        },
                        icon: Icon(
                          _obscurePasswordConfirm ? Icons.visibility_off : Icons.visibility,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                  if (_passwordConfirmError != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      _passwordConfirmError!,
                      style: AppTypography.caption.copyWith(color: AppColors.error),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  if (_submitError != null) ...[
                    Text(
                      _submitError!,
                      style: AppTypography.body2.copyWith(color: AppColors.error),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  Opacity(
                    opacity: isLoading ? 0.7 : 1,
                    child: SizedBox(
                      height: 52,
                      child: DecoratedBox(
                        decoration: primaryButtonDecoration,
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(AppRadius.md),
                            onTap: isLoading ? null : _submit,
                            child: Center(
                              child: isLoading
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: AppColors.background,
                                      ),
                                    )
                                  : Text(
                                      '가입하기',
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
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '이미 계정이 있으신가요? ',
                        style: AppTypography.body2.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.go('/login'),
                        child: Text(
                          '로그인',
                          style: AppTypography.body2.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
