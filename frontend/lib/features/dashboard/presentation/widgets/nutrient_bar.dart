import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';

class NutrientBar extends StatefulWidget {
  final String label;
  final double current;
  final double target;
  final Color color;
  final Duration delay;

  const NutrientBar({
    super.key,
    required this.label,
    required this.current,
    required this.target,
    required this.color,
    this.delay = Duration.zero,
  });

  @override
  State<NutrientBar> createState() => _NutrientBarState();
}

class _NutrientBarState extends State<NutrientBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final CurvedAnimation _curve;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _curve = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
    _startAnimation();
  }

  @override
  void didUpdateWidget(covariant NutrientBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.current != widget.current ||
        oldWidget.target != widget.target ||
        oldWidget.delay != widget.delay) {
      _controller.reset();
      _startAnimation();
    }
  }

  void _startAnimation() {
    Future<void>.delayed(widget.delay, () {
      if (!mounted) {
        return;
      }
      _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final double baseProgress =
        widget.target <= 0
            ? 0
            : (widget.current / widget.target).clamp(0.0, 1.0);

    return AnimatedBuilder(
      animation: _curve,
      builder: (BuildContext context, Widget? child) {
        final double animatedProgress = baseProgress * _curve.value;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(widget.label, style: AppTypography.body2),
                Text(
                  '${_format(widget.current)} / ${_format(widget.target)}g',
                  style: AppTypography.caption,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.full),
              child: LinearProgressIndicator(
                value: animatedProgress,
                minHeight: 6,
                valueColor: AlwaysStoppedAnimation<Color>(widget.color),
                backgroundColor: AppColors.surfaceLight,
              ),
            ),
          ],
        );
      },
    );
  }

  String _format(double value) {
    if (value == value.roundToDouble()) {
      return value.toInt().toString();
    }
    return value.toStringAsFixed(1);
  }
}
