import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_spacing.dart';

final BoxDecoration cardDecoration = BoxDecoration(
  color: AppColors.surface,
  borderRadius: BorderRadius.circular(AppRadius.md),
  border: Border.all(color: AppColors.divider, width: 0.5),
);

final BoxDecoration glassCardDecoration = BoxDecoration(
  color: AppColors.surface.withValues(alpha: 0.7),
  borderRadius: BorderRadius.circular(AppRadius.lg),
  border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
  boxShadow: [
    BoxShadow(
      color: AppColors.primary.withValues(alpha: 0.05),
      blurRadius: 20,
      offset: const Offset(0, 4),
    ),
  ],
);

final BoxDecoration primaryButtonDecoration = BoxDecoration(
  gradient: const LinearGradient(
    colors: [AppColors.primary, AppColors.primaryDark],
  ),
  borderRadius: BorderRadius.circular(AppRadius.md),
);
