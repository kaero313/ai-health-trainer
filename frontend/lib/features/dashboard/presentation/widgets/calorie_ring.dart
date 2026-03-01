import 'dart:math' show pi;

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_typography.dart';

class CalorieRing extends StatelessWidget {
  final double progress;
  final int consumed;
  final int target;

  const CalorieRing({
    super.key,
    required this.progress,
    required this.consumed,
    required this.target,
  });

  @override
  Widget build(BuildContext context) {
    final double safeProgress = progress.clamp(0.0, 1.0);

    return SizedBox(
      width: 180,
      height: 180,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: const Size(180, 180),
            painter: _CalorieRingPainter(progress: safeProgress),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(consumed.toString(), style: AppTypography.number),
              Text('/${target.toString()}', style: AppTypography.body2),
              Text('kcal', style: AppTypography.caption),
            ],
          ),
        ],
      ),
    );
  }
}

class _CalorieRingPainter extends CustomPainter {
  final double progress;

  const _CalorieRingPainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    const double strokeWidth = 12;
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double radius = (size.width / 2) - strokeWidth / 2;
    final Rect rect = Rect.fromCircle(center: center, radius: radius);

    final Paint backgroundPaint = Paint()
      ..color = AppColors.surfaceLight
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final Paint progressPaint = Paint()
      ..color = AppColors.calories
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(rect, 0, pi * 2, false, backgroundPaint);
    canvas.drawArc(rect, -pi / 2, (pi * 2) * progress, false, progressPaint);
  }

  @override
  bool shouldRepaint(covariant _CalorieRingPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
