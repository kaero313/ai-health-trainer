// 하루 목표 진행 링 (docs/DESIGN_SYSTEM.md §12-1, §12-4).
// 트랙 muted, 진행 primary, 두께 10, 둥근 끝. 중앙에 numLarge 값 + caption 라벨.
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class ProgressRing extends StatelessWidget {
  const ProgressRing({
    super.key,
    required this.value,
    required this.label,
    this.valueText,
    this.size = 112,
    this.semanticLabel,
  });

  static const double strokeWidth = 10;

  /// 목표 대비 비율. 1을 넘을 수 있고, 링은 [clampedValue]로 그린다.
  final double value;

  /// 중앙 아래 caption 라벨(예: "열량 목표").
  final String label;

  /// 중앙 수치. 없으면 [value]의 백분율(자르지 않은 값, 예: 115%)이다.
  final String? valueText;

  final double size;
  final String? semanticLabel;

  /// 링에 그리는 값(0~1).
  double get clampedValue => value.isNaN ? 0 : value.clamp(0.0, 1.0);

  /// 목표를 넘긴 양(1 초과분). 0보다 크면 호출부가 warning 배지를 붙인다(§12-4).
  double get overflow => value.isNaN ? 0 : math.max(0, value - 1);

  bool get isOver => overflow > 0;

  String get effectiveValueText =>
      valueText ?? '${((value.isNaN ? 0 : math.max(0, value)) * 100).round()}%';

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final String text = effectiveValueText;
    return Semantics(
      label: semanticLabel ?? '$label $text',
      excludeSemantics: true,
      child: SizedBox.square(
        dimension: size,
        child: CustomPaint(
          painter: _RingPainter(
            progress: clampedValue,
            track: cs.muted,
            color: cs.primary,
          ),
          child: Padding(
            // 링 안쪽에 글자가 닿지 않게 두께 + 8만큼 비운다.
            padding: const EdgeInsets.all(strokeWidth + AppSpace.s8),
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      text,
                      style: AppTextStyles.numLarge.copyWith(
                        color: cs.foreground,
                      ),
                    ),
                    Text(
                      label,
                      style: AppTextStyles.caption.copyWith(
                        color: cs.mutedForeground,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.track,
    required this.color,
  });

  final double progress;
  final Color track;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    const double stroke = ProgressRing.strokeWidth;
    final Rect rect = Rect.fromLTWH(
      stroke / 2,
      stroke / 2,
      size.width - stroke,
      size.height - stroke,
    );
    final Paint trackPaint = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    canvas.drawArc(rect, 0, math.pi * 2, false, trackPaint);
    if (progress <= 0) return;
    final Paint arcPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      // 가득 찬 링은 끝이 겹쳐 보이지 않게 butt로 그린다.
      ..strokeCap = progress >= 1 ? StrokeCap.butt : StrokeCap.round;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * progress, false, arcPaint);
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.progress != progress || old.track != track || old.color != color;
}
