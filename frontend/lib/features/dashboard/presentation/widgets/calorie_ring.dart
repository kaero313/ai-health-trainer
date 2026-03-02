import 'dart:math' show pi;

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_typography.dart';

class CalorieRing extends StatefulWidget {
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
  State<CalorieRing> createState() => _CalorieRingState();
}

class _CalorieRingState extends State<CalorieRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late CurvedAnimation _curve;
  late Animation<double> _progressAnimation;

  double get _safeProgress => widget.progress.clamp(0.0, 1.0);

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _curve = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
    _progressAnimation = Tween<double>(
      begin: 0.0,
      end: _safeProgress,
    ).animate(_curve);
    _controller.forward();
  }

  @override
  void didUpdateWidget(covariant CalorieRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.progress != widget.progress) {
      _progressAnimation = Tween<double>(
        begin: 0.0,
        end: _safeProgress,
      ).animate(_curve);
      _controller.forward(from: 0.0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 180,
      height: 180,
      child: AnimatedBuilder(
        animation: _progressAnimation,
        builder: (BuildContext context, Widget? child) {
          final double animatedProgress = _progressAnimation.value;
          final int animatedConsumed =
              (animatedProgress * widget.consumed).round();

          return Stack(
            alignment: Alignment.center,
            children: [
              CustomPaint(
                size: const Size(180, 180),
                painter: _CalorieRingPainter(progress: animatedProgress),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    animatedConsumed.toString(),
                    style: AppTypography.number,
                  ),
                  Text('/${widget.target}', style: AppTypography.body2),
                  Text('kcal', style: AppTypography.caption),
                ],
              ),
            ],
          );
        },
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

    final Paint backgroundPaint =
        Paint()
          ..color = AppColors.surfaceLight
          ..style = PaintingStyle.stroke
          ..strokeWidth = strokeWidth
          ..strokeCap = StrokeCap.round;

    final Paint progressPaint =
        Paint()
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
