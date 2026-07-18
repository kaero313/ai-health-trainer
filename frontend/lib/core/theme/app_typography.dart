import 'package:flutter/material.dart';

import 'app_colors.dart';

class AppTypography {
  static const List<String> _koreanFallback = <String>['NotoSansKR'];

  static TextStyle get display => const TextStyle(
    fontFamily: 'Sora',
    fontFamilyFallback: _koreanFallback,
    fontSize: 36,
    fontWeight: FontWeight.w800,
    height: 1.08,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get h1 => const TextStyle(
    fontFamily: 'Sora',
    fontFamilyFallback: _koreanFallback,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.16,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get h2 => const TextStyle(
    fontFamily: 'Sora',
    fontFamilyFallback: _koreanFallback,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.24,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get h3 => const TextStyle(
    fontFamily: 'Sora',
    fontFamilyFallback: _koreanFallback,
    fontSize: 18,
    fontWeight: FontWeight.w700,
    height: 1.28,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get body1 => const TextStyle(
    fontFamily: 'HankenGrotesk',
    fontFamilyFallback: _koreanFallback,
    fontSize: 16,
    fontWeight: FontWeight.w500,
    height: 1.55,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get body2 => const TextStyle(
    fontFamily: 'HankenGrotesk',
    fontFamilyFallback: _koreanFallback,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    height: 1.5,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get label => const TextStyle(
    fontFamily: 'Geist',
    fontFamilyFallback: _koreanFallback,
    fontSize: 12,
    fontWeight: FontWeight.w700,
    height: 1.15,
    letterSpacing: 0,
    color: AppColors.textSecondary,
  );

  static TextStyle get caption => const TextStyle(
    fontFamily: 'Geist',
    fontFamilyFallback: _koreanFallback,
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.25,
    letterSpacing: 0,
    color: AppColors.textSecondary,
  );

  static TextStyle get number => const TextStyle(
    fontFamily: 'Geist',
    fontFamilyFallback: _koreanFallback,
    fontSize: 32,
    fontWeight: FontWeight.w800,
    height: 1,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static TextStyle get numberSmall => const TextStyle(
    fontFamily: 'Geist',
    fontFamilyFallback: _koreanFallback,
    fontSize: 22,
    fontWeight: FontWeight.w800,
    height: 1,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );
}
