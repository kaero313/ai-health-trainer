// 날짜·월 이동 (docs/DESIGN_SYSTEM.md §11-3). 가운데 heading 날짜 + 좌우 Ghost 아이콘 버튼(48).
// 가운데를 누르면 날짜 선택을 열 수 있다(onTapLabel).
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class DateStepper extends StatelessWidget {
  const DateStepper({
    super.key,
    required this.label,
    this.caption,
    required this.onPrevious,
    required this.onNext,
    this.onTapLabel,
    this.previousLabel = '이전 날짜',
    this.nextLabel = '다음 날짜',
    this.tapLabelHint = '날짜 선택',
  });

  /// 가운데 날짜(예: "11월 24일 월요일", "2026년 11월").
  final String label;

  /// 날짜 위 caption(예: "오늘").
  final String? caption;

  /// null이면 그 방향 버튼이 비활성이다(예: 다음 달이 미래).
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;

  /// 가운데를 눌렀을 때(날짜 선택 열기). null이면 가운데는 눌리지 않는다.
  final VoidCallback? onTapLabel;

  /// 스크린리더 이름.
  final String previousLabel;
  final String nextLabel;
  final String tapLabelHint;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Widget center = Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        if (caption != null)
          Text(
            caption!,
            style: AppTextStyles.caption.copyWith(color: cs.mutedForeground),
          ),
        Text(
          label,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTextStyles.heading.copyWith(color: cs.foreground),
        ),
      ],
    );
    return Row(
      children: <Widget>[
        _StepButton(
          icon: LucideIcons.chevronLeft,
          label: previousLabel,
          onPressed: onPrevious,
        ),
        const SizedBox(width: AppSpace.s4),
        Expanded(
          child: onTapLabel == null
              ? Semantics(
                  label: caption == null ? label : '$caption $label',
                  excludeSemantics: true,
                  child: Center(child: center),
                )
              : Semantics(
                  button: true,
                  label: caption == null ? label : '$caption $label',
                  hint: tapLabelHint,
                  // 자식 의미 정보를 걸러 내므로 탭 동작을 여기서 직접 노출한다.
                  onTap: onTapLabel,
                  excludeSemantics: true,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: onTapLabel,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 48),
                      child: Center(child: center),
                    ),
                  ),
                ),
        ),
        const SizedBox(width: AppSpace.s4),
        _StepButton(
          icon: LucideIcons.chevronRight,
          label: nextLabel,
          onPressed: onNext,
        ),
      ],
    );
  }
}

class _StepButton extends StatelessWidget {
  const _StepButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      button: true,
      enabled: onPressed != null,
      onTap: onPressed,
      excludeSemantics: true,
      child: ShadIconButton.ghost(
        onPressed: onPressed,
        // shadcn 버튼은 onPressed가 null이어도 enabled로만 흐린 모양을 정한다.
        enabled: onPressed != null,
        iconSize: 20,
        icon: Icon(icon),
      ),
    );
  }
}
