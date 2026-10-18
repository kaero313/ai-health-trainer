// 모션 토큰. 값의 원본은 docs/DESIGN_SYSTEM.md §11-1(선택 표시 150ms)과 §13-2(스켈레톤 펄스 1.2s)다.
import 'package:flutter/animation.dart';

abstract final class AppMotion {
  /// 하단 탭·세그먼트 선택 표시 전환 (§11-1).
  static const Duration selection = Duration(milliseconds: 150);

  /// 스켈레톤 투명도 펄스 한 주기 (§13-2). 밝아졌다 어두워지는 왕복이 1.2s다.
  static const Duration skeletonPulse = Duration(milliseconds: 1200);

  /// 스켈레톤 펄스의 가장 옅은 투명도.
  static const double skeletonMinOpacity = 0.5;

  static const Curve standard = Curves.easeInOut;
}
