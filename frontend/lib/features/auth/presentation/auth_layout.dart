import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';

class AuthSurface extends StatelessWidget {
  final Widget child;
  final String imageAsset;

  const AuthSurface({
    super.key,
    required this.child,
    this.imageAsset = 'assets/stitch/dashboard_gym.jpg',
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            imageAsset,
            fit: BoxFit.cover,
            color: Colors.black.withValues(alpha: 0.52),
            colorBlendMode: BlendMode.darken,
          ),
          ColoredBox(color: AppColors.background.withValues(alpha: 0.74)),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.pageHorizontal,
                  vertical: AppSpacing.lg,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: child,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AuthBrand extends StatelessWidget {
  final String title;
  final String? subtitle;

  const AuthBrand({super.key, required this.title, this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.surfaceHigh.withValues(alpha: 0.86),
                border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.48),
                ),
              ),
              child: const Icon(
                Icons.monitor_heart_outlined,
                color: AppColors.primary,
                size: 22,
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                'AI Health Trainer',
                style: AppTypography.h3.copyWith(color: AppColors.primary),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),
        Text(title, style: AppTypography.h1),
        if (subtitle != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            subtitle!,
            style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ],
    );
  }
}
