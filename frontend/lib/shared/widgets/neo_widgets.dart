import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_decorations.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

class NeoPage extends StatelessWidget {
  final List<Widget> children;
  final EdgeInsetsGeometry padding;
  final Widget? header;
  final Future<void> Function()? onRefresh;

  const NeoPage({
    super.key,
    required this.children,
    this.header,
    this.onRefresh,
    this.padding = const EdgeInsets.fromLTRB(20, 16, 20, 108),
  });

  @override
  Widget build(BuildContext context) {
    final Widget scrollView = RefreshConfiguration(
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            header ?? const NeoTopBar(),
            const SizedBox(height: AppSpacing.lg),
            ...children,
          ],
        ),
      ),
    );
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child:
            onRefresh == null
                ? scrollView
                : RefreshIndicator(
                  color: AppColors.primary,
                  backgroundColor: AppColors.surfaceLow,
                  onRefresh: onRefresh!,
                  child: scrollView,
                ),
      ),
    );
  }
}

class RefreshConfiguration extends StatelessWidget {
  final Widget child;

  const RefreshConfiguration({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return ScrollConfiguration(
      behavior: const _NeoScrollBehavior(),
      child: child,
    );
  }
}

class _NeoScrollBehavior extends ScrollBehavior {
  const _NeoScrollBehavior();

  @override
  Widget buildOverscrollIndicator(
    BuildContext context,
    Widget child,
    ScrollableDetails details,
  ) {
    return child;
  }
}

class NeoTopBar extends StatelessWidget {
  final String title;
  final bool showBack;
  final List<Widget> actions;

  const NeoTopBar({
    super.key,
    this.title = 'AI Health Trainer',
    this.showBack = false,
    this.actions = const <Widget>[],
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (showBack)
          _RoundIconButton(icon: Icons.arrow_back, onTap: () => context.pop())
        else
          const _BrandMark(),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.h3.copyWith(color: AppColors.primary),
          ),
        ),
        if (actions.isEmpty)
          const Icon(
            Icons.notifications_none,
            color: AppColors.textSecondary,
            size: 22,
          )
        else
          ...actions,
      ],
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.surfaceHigh,
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.42)),
      ),
      child: const Icon(
        Icons.monitor_heart_outlined,
        color: AppColors.primary,
        size: 18,
      ),
    );
  }
}

class _RoundIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _RoundIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(AppRadius.full),
      onTap: onTap,
      child: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AppColors.surfaceHigh,
          border: Border.all(color: AppColors.divider),
        ),
        child: Icon(icon, color: AppColors.textPrimary, size: 18),
      ),
    );
  }
}

class NeoGlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final bool highlighted;
  final VoidCallback? onTap;

  const NeoGlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.md),
    this.highlighted = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Widget content = DecoratedBox(
      decoration: highlighted ? glassCardDecoration : cardDecoration,
      child: Padding(padding: padding, child: child),
    );

    if (onTap == null) {
      return content;
    }

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        onTap: onTap,
        child: content,
      ),
    );
  }
}

class NeoStateCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const NeoStateCard({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      highlighted: true,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.primary, size: 28),
          const SizedBox(height: AppSpacing.md),
          Text(title, style: AppTypography.h2),
          const SizedBox(height: AppSpacing.sm),
          Text(
            message,
            style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
          ),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: AppSpacing.md),
            NeoPrimaryButton(label: actionLabel!, onPressed: onAction),
          ],
        ],
      ),
    );
  }
}

class NeoSectionHeader extends StatelessWidget {
  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  const NeoSectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Text(title, style: AppTypography.h2)),
        if (actionLabel != null)
          TextButton(
            onPressed: onAction,
            child: Text(
              actionLabel!,
              style: AppTypography.caption.copyWith(color: AppColors.primary),
            ),
          ),
      ],
    );
  }
}

class NeoMetricTile extends StatelessWidget {
  final String label;
  final String value;
  final String? unit;
  final String? delta;
  final Color accent;

  const NeoMetricTile({
    super.key,
    required this.label,
    required this.value,
    this.unit,
    this.delta,
    this.accent = AppColors.primary,
  });

  @override
  Widget build(BuildContext context) {
    return NeoGlassCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label.toUpperCase(), style: AppTypography.caption),
                const SizedBox(height: AppSpacing.xs),
                RichText(
                  text: TextSpan(
                    children: [
                      TextSpan(text: value, style: AppTypography.numberSmall),
                      if (unit != null)
                        TextSpan(
                          text: ' $unit',
                          style: AppTypography.caption.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (delta != null)
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  delta!,
                  style: AppTypography.label.copyWith(color: accent),
                ),
                const SizedBox(height: AppSpacing.xs),
                Container(width: 34, height: 3, color: accent),
              ],
            ),
        ],
      ),
    );
  }
}

class NeoInfoChip extends StatelessWidget {
  final String label;
  final Color color;
  final bool filled;

  const NeoInfoChip({
    super.key,
    required this.label,
    this.color = AppColors.primary,
    this.filled = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: chipDecoration(selected: filled, color: color),
      child: Text(
        label,
        style: AppTypography.caption.copyWith(
          color: filled ? AppColors.background : color,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class NeoPrimaryButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;

  const NeoPrimaryButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: onPressed == null ? 0.55 : 1,
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          onTap: onPressed,
          child: Container(
            height: 48,
            decoration: primaryButtonDecoration,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: AppColors.background, size: 18),
                  const SizedBox(width: AppSpacing.xs),
                ],
                Text(
                  label,
                  style: AppTypography.label.copyWith(
                    color: AppColors.background,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class NeoOutlineButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;

  const NeoOutlineButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        onTap: onPressed,
        child: Container(
          height: 46,
          decoration: outlineButtonDecoration,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, color: AppColors.primary, size: 18),
                const SizedBox(width: AppSpacing.xs),
              ],
              Text(
                label,
                style: AppTypography.label.copyWith(color: AppColors.primary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NeoProgressBar extends StatelessWidget {
  final double value;
  final Color color;
  final double height;

  const NeoProgressBar({
    super.key,
    required this.value,
    this.color = AppColors.primary,
    this.height = 8,
  });

  @override
  Widget build(BuildContext context) {
    final double clamped = value.clamp(0, 1);
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.full),
      child: Container(
        height: height,
        color: Colors.white.withValues(alpha: 0.06),
        child: Align(
          alignment: Alignment.centerLeft,
          child: FractionallySizedBox(
            widthFactor: clamped,
            child: Container(color: color),
          ),
        ),
      ),
    );
  }
}

class NeoAssetImage extends StatelessWidget {
  final String path;
  final double? height;
  final double? width;
  final BorderRadius borderRadius;
  final BoxFit fit;

  const NeoAssetImage({
    super.key,
    required this.path,
    this.height,
    this.width,
    this.borderRadius = const BorderRadius.all(Radius.circular(AppRadius.md)),
    this.fit = BoxFit.cover,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius,
      child: Image.asset(path, height: height, width: width, fit: fit),
    );
  }
}

class NeoLineChart extends StatelessWidget {
  final List<double> values;
  final Color color;
  final double height;
  final bool fill;

  const NeoLineChart({
    super.key,
    required this.values,
    this.color = AppColors.primary,
    this.height = 120,
    this.fill = true,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      child: CustomPaint(
        painter: _NeoLineChartPainter(values: values, color: color, fill: fill),
        size: Size.infinite,
      ),
    );
  }
}

class _NeoLineChartPainter extends CustomPainter {
  final List<double> values;
  final Color color;
  final bool fill;

  const _NeoLineChartPainter({
    required this.values,
    required this.color,
    required this.fill,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2 || size.width <= 0 || size.height <= 0) {
      return;
    }

    final double minValue = values.reduce(math.min);
    final double maxValue = values.reduce(math.max);
    final double range = math.max(maxValue - minValue, 1);
    final double step = size.width / (values.length - 1);
    final Path path = Path();

    for (int i = 0; i < values.length; i++) {
      final double x = step * i;
      final double normalized = (values[i] - minValue) / range;
      final double y = size.height - (normalized * size.height * 0.78) - 12;
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    if (fill) {
      final Path area =
          Path.from(path)
            ..lineTo(size.width, size.height)
            ..lineTo(0, size.height)
            ..close();
      final Paint fillPaint =
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                color.withValues(alpha: 0.28),
                color.withValues(alpha: 0.0),
              ],
            ).createShader(Offset.zero & size);
      canvas.drawPath(area, fillPaint);
    }

    final Paint linePaint =
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..strokeWidth = 3;
    canvas.drawPath(path, linePaint);
  }

  @override
  bool shouldRepaint(covariant _NeoLineChartPainter oldDelegate) {
    return oldDelegate.values != values ||
        oldDelegate.color != color ||
        oldDelegate.fill != fill;
  }
}

class NeoRing extends StatelessWidget {
  final double value;
  final double size;
  final Color color;
  final String centerText;
  final String label;

  const NeoRing({
    super.key,
    required this.value,
    required this.centerText,
    required this.label,
    this.size = 150,
    this.color = AppColors.primary,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _NeoRingPainter(value: value, color: color),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(centerText, style: AppTypography.h2),
              Text(label, style: AppTypography.caption),
            ],
          ),
        ),
      ),
    );
  }
}

class _NeoRingPainter extends CustomPainter {
  final double value;
  final Color color;

  const _NeoRingPainter({required this.value, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = size.center(Offset.zero);
    final double radius = math.min(size.width, size.height) / 2 - 14;
    final Rect rect = Rect.fromCircle(center: center, radius: radius);
    final Paint track =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.08)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 16
          ..strokeCap = StrokeCap.round;
    final Paint progress =
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 16
          ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2, false, track);
    canvas.drawArc(
      rect,
      -math.pi / 2,
      math.pi * 2 * value.clamp(0, 1),
      false,
      progress,
    );
  }

  @override
  bool shouldRepaint(covariant _NeoRingPainter oldDelegate) {
    return oldDelegate.value != value || oldDelegate.color != color;
  }
}
