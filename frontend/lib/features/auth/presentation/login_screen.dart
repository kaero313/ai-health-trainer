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

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

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
      return '이메일을 입력해 주세요.';
    }
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email)) {
      return '올바른 이메일 형식을 입력해 주세요.';
    }
    return null;
  }

  String? _validatePassword(String value) {
    return value.isEmpty ? '비밀번호를 입력해 주세요.' : null;
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
      await ref
          .read(authControllerProvider.notifier)
          .login(_emailController.text.trim(), _passwordController.text);
      if (mounted) {
        context.go('/dashboard');
      }
    } catch (error) {
      if (mounted) {
        setState(() => _submitError = _extractErrorMessage(error));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isLoading = ref.watch(authControllerProvider).isLoading;
    return AuthSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AuthBrand(
            title: '다시 만나서 반갑습니다',
            subtitle: '오늘의 기록과 코칭을 이어서 확인하세요.',
          ),
          const SizedBox(height: AppSpacing.lg),
          NeoGlassCard(
            highlighted: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autofillHints: const <String>[AutofillHints.email],
                  style: AppTypography.body1,
                  onChanged: (String value) {
                    setState(() {
                      _emailError = _validateEmail(value);
                      _submitError = null;
                    });
                  },
                  decoration: InputDecoration(
                    labelText: '이메일',
                    hintText: 'name@example.com',
                    errorText: _emailError,
                    prefixIcon: const Icon(Icons.mail_outline),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                TextField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  textInputAction: TextInputAction.done,
                  autofillHints: const <String>[AutofillHints.password],
                  style: AppTypography.body1,
                  onChanged: (String value) {
                    setState(() {
                      _passwordError = _validatePassword(value);
                      _submitError = null;
                    });
                  },
                  onSubmitted: (_) => isLoading ? null : _submit(),
                  decoration: InputDecoration(
                    labelText: '비밀번호',
                    errorText: _passwordError,
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
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
                  ),
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
                  label: isLoading ? '로그인 중' : '로그인',
                  icon: Icons.login,
                  onPressed: isLoading ? null : _submit,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '처음이신가요?',
                style: AppTypography.body2.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              TextButton(
                onPressed: () => context.go('/register'),
                child: Text(
                  '회원가입',
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

String _extractErrorMessage(Object error) {
  if (error is AuthRepositoryException) {
    return error.message;
  }
  return '로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.';
}
