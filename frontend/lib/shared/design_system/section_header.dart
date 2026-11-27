// 카드 밖 섹션 제목 + 선택적 Link 액션 (docs/DESIGN_SYSTEM.md §8 Link, §16).
// 카드 안 헤더 액션은 AppCardAction(Ghost)을 쓴다. 이 위젯은 카드들 위에 붙는 제목이다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_card.dart';

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onAction,
  }) : assert(
         (actionLabel == null) == (onAction == null),
         'actionLabel과 onAction은 함께 준다',
       );

  final String title;

  /// 오른쪽 Link 액션(예: "사진 분석", "전체 보기").
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Row(
      children: <Widget>[
        Expanded(
          child: Semantics(
            header: true,
            child: Text(
              title,
              style: AppTextStyles.heading.copyWith(color: cs.foreground),
            ),
          ),
        ),
        if (actionLabel != null) ...<Widget>[
          const SizedBox(width: AppSpace.s8),
          _LinkAction(label: actionLabel!, onPressed: onAction!),
        ],
      ],
    );
  }
}

/// Link compact: 보이는 높이 40, 누르는 영역 48(AppCardAction과 같은 값).
class _LinkAction extends StatelessWidget {
  const _LinkAction({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    // 버튼 위아래 4는 바깥 GestureDetector가 받고, 버튼 안은 버튼이 받는다.
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      excludeFromSemantics: true,
      onTap: onPressed,
      child: SizedBox(
        height: AppCardAction.hitHeight,
        child: Center(
          child: ShadButton.link(
            size: ShadButtonSize.sm,
            textStyle: AppTextStyles.buttonCompact,
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s8),
            onPressed: onPressed,
            child: Text(label),
          ),
        ),
      ),
    );
  }
}
