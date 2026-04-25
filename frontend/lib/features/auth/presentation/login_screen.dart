import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_decorations.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../data/auth_repository.dart';
import '../domain/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final TextEditingController _emailController = TextEditingController(text: 'admin@admin.com');
  final TextEditingController _passwordController = TextEditingController(text: 'Admin@12345678');

  bool _obscurePassword = true;
  String? _emailError;
  String? _passwordError;
  String? _submitError;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
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
    return null;
  }

  Future<void> _submit() async {
    final String? emailError = _validateEmail(_emailController.text);
    final String? passwordError = _validatePassword(_passwordController.text);

    setState(() {
      _emailError = emailError;
      _passwordError = passwordError;
      _submitError = null;
    });

    if (emailError != null || passwordError != null) {
      return;
    }

    try {
      await ref.read(authControllerProvider.notifier).login(
            _emailController.text.trim(),
            _passwordController.text,
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
    if (raw.contains('ConnectTimeout') || raw.contains('connection')) {
      return '서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.';
    }
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
                    decoration: _inputDecoration(hintText: 'admin@admin.com'),
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
                                      '로그인',
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
                        '계정이 없으신가요? ',
                        style: AppTypography.body2.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.go('/register'),
                        child: Text(
                          '회원가입',
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
