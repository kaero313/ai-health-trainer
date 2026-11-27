// 수치 타일: caption 라벨 + numLarge 값 + 단위 + 선택적 배지 (docs/DESIGN_SYSTEM.md §9, §16).
// 값이 없으면 꾸미지 않고 "--"와 "기록 없음"을 muted로 보인다(§21-2).
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class MetricTile extends StatelessWidget {
  const MetricTile({
    super.key,
    required this.label,
    required this.value,
    this.unit,
    this.trailing,
    this.emptyLabel = '기록 없음',
  });

  final String label;

  /// 표시할 값(이미 포맷된 문자열). 기록이 없으면 null.
  final String? value;

  /// 값 뒤 단위(kg, %, kcal). 값이 없으면 숨긴다.
  final String? unit;

  /// 라벨 오른쪽 배지 1개(변화량 등). 중립 배지를 쓴다(§21-2).
  final Widget? trailing;

  /// 값이 없을 때 "--" 옆 문구.
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final bool hasValue = value != null;
    final String spoken = hasValue
        ? '$label ${value!}${unit == null ? '' : ' $unit'}'
        : '$label $emptyLabel';
    return ShadCard(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.s16),
      columnCrossAxisAlignment: CrossAxisAlignment.stretch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.caption.copyWith(
                    color: cs.mutedForeground,
                  ),
                ),
              ),
              if (trailing != null) ...<Widget>[
                const SizedBox(width: AppSpace.s8),
                trailing!,
              ],
            ],
          ),
          const SizedBox(height: AppSpace.s8),
          Semantics(
            label: spoken,
            excludeSemantics: true,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: <Widget>[
                Text(
                  hasValue ? value! : '--',
                  style: AppTextStyles.numLarge.copyWith(
                    color: hasValue ? cs.cardForeground : cs.mutedForeground,
                  ),
                ),
                const SizedBox(width: AppSpace.s4),
                Flexible(
                  child: Text(
                    hasValue ? (unit ?? '') : emptyLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.body.copyWith(
                      color: cs.mutedForeground,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
