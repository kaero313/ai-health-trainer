// 매크로 진행 바 (docs/DESIGN_SYSTEM.md §12-4).
// 위 한 줄에 색 점 + caption 라벨 + numSmall 값, 아래 ShadProgress(높이 6, 채움은 대상 색).
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_badge.dart';
import 'app_number_format.dart';

class MacroBar extends StatelessWidget {
  const MacroBar({
    super.key,
    required this.label,
    required this.value,
    required this.target,
    required this.color,
    this.unit = 'g',
  });

  final String label;
  final num value;

  /// 목표가 없으면 null. 값만 보이고 막대는 비운다.
  final num? target;

  /// 대상 색(chartProtein·chartCarbs·chartFat). 점과 막대에만 쓰고 글자에는 쓰지 않는다.
  final Color color;
  final String unit;

  double get progress => target == null || target! <= 0
      ? 0
      : (value / target!).toDouble().clamp(0.0, 1.0);

  String get valueText => target == null
      ? '${formatNumber(value)} $unit'
      : '${formatNumber(value)} / ${formatNumber(target!)} $unit';

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Semantics(
      label: '$label $valueText',
      excludeSemantics: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: AppLegendDot(color: color, label: label),
              ),
              const SizedBox(width: AppSpace.s8),
              Text(
                valueText,
                style: AppTextStyles.numSmall.copyWith(color: cs.foreground),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.s8),
          ShadProgress(value: progress, color: color),
        ],
      ),
    );
  }
}
