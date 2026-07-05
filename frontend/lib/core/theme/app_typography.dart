import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

class AppTypography {
  static TextStyle get display => GoogleFonts.notoSansKr(
    fontSize: 36,
    fontWeight: FontWeight.w800,
    height: 1.08,
    color: AppColors.textPrimary,
  );

  static TextStyle get h1 => GoogleFonts.notoSansKr(
    fontSize: 28,
    fontWeight: FontWeight.w800,
    height: 1.12,
    color: AppColors.textPrimary,
  );

  static TextStyle get h2 => GoogleFonts.notoSansKr(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: AppColors.textPrimary,
  );

  static TextStyle get h3 => GoogleFonts.notoSansKr(
    fontSize: 18,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: AppColors.textPrimary,
  );

  static TextStyle get body1 => GoogleFonts.notoSansKr(
    fontSize: 16,
    fontWeight: FontWeight.w500,
    height: 1.5,
    color: AppColors.textPrimary,
  );

  static TextStyle get body2 => GoogleFonts.notoSansKr(
    fontSize: 14,
    fontWeight: FontWeight.w500,
    height: 1.45,
    color: AppColors.textPrimary,
  );

  static TextStyle get label => GoogleFonts.notoSansKr(
    fontSize: 12,
    fontWeight: FontWeight.w700,
    height: 1.0,
    letterSpacing: 0,
    color: AppColors.textSecondary,
  );

  static TextStyle get caption => GoogleFonts.notoSansKr(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.2,
    color: AppColors.textSecondary,
  );

  static TextStyle get number => GoogleFonts.notoSansKr(
    fontSize: 32,
    fontWeight: FontWeight.w800,
    height: 1.0,
    color: AppColors.textPrimary,
  );

  static TextStyle get numberSmall => GoogleFonts.notoSansKr(
    fontSize: 22,
    fontWeight: FontWeight.w800,
    height: 1.0,
    color: AppColors.textPrimary,
  );
}
