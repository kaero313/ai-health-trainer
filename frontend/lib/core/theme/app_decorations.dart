import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_spacing.dart';

BoxDecoration cardDecoration = BoxDecoration(
  color: AppColors.surfaceLow.withValues(alpha: 0.82),
  borderRadius: BorderRadius.circular(AppRadius.md),
  border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
  gradient: LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Colors.white.withValues(alpha: 0.045),
      Colors.white.withValues(alpha: 0.005),
    ],
  ),
);

BoxDecoration glassCardDecoration = BoxDecoration(
  color: AppColors.surfaceLow.withValues(alpha: 0.66),
  borderRadius: BorderRadius.circular(AppRadius.xl),
  border: Border.all(color: AppColors.primary.withValues(alpha: 0.20)),
  boxShadow: [
    BoxShadow(
      color: AppColors.primary.withValues(alpha: 0.10),
      blurRadius: 30,
      offset: const Offset(0, 12),
    ),
  ],
  gradient: LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Colors.white.withValues(alpha: 0.055),
      Colors.white.withValues(alpha: 0.008),
    ],
  ),
);

BoxDecoration primaryButtonDecoration = BoxDecoration(
  color: AppColors.primary,
  borderRadius: BorderRadius.circular(AppRadius.lg),
  boxShadow: [
    BoxShadow(
      color: AppColors.primary.withValues(alpha: 0.24),
      blurRadius: 24,
      offset: const Offset(0, 10),
    ),
  ],
);

BoxDecoration outlineButtonDecoration = BoxDecoration(
  color: Colors.transparent,
  borderRadius: BorderRadius.circular(AppRadius.lg),
  border: Border.all(color: AppColors.primary.withValues(alpha: 0.45)),
);

BoxDecoration chipDecoration({bool selected = false, Color? color}) {
  final Color resolved = color ?? AppColors.primary;
  return BoxDecoration(
    color:
        selected ? resolved : AppColors.surfaceHighest.withValues(alpha: 0.72),
    borderRadius: BorderRadius.circular(AppRadius.full),
    border: Border.all(color: resolved.withValues(alpha: selected ? 1 : 0.45)),
  );
}
