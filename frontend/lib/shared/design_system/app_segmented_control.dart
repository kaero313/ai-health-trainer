// 세그먼트 선택 (docs/DESIGN_SYSTEM.md §11-3). muted 트랙 + 선택 항목 card 면.
// 시안으로 채우지 않는다. 트랙 높이 48(위아래 4 + 항목 40)이라 누르는 영역도 48이다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_motion.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

@immutable
class AppSegment<T> {
  const AppSegment({required this.value, required this.label, this.icon});

  final T value;
  final String label;

  /// 라벨 왼쪽 아이콘(16).
  final IconData? icon;
}

class AppSegmentedControl<T> extends StatelessWidget {
  const AppSegmentedControl({
    super.key,
    required this.segments,
    required this.selected,
    required this.onChanged,
  });

  static const double height = 48;
  static const double inset = AppSpace.s4;

  final List<AppSegment<T>> segments;
  final T selected;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Container(
      height: height,
      padding: const EdgeInsets.all(inset),
      decoration: BoxDecoration(
        color: cs.muted,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Row(
        children: <Widget>[
          for (final AppSegment<T> s in segments)
            Expanded(
              child: _SegmentButton(
                segment: s,
                selected: s.value == selected,
                onTap: () {
                  if (s.value != selected) onChanged(s.value);
                },
              ),
            ),
        ],
      ),
    );
  }
}

class _SegmentButton extends StatelessWidget {
  const _SegmentButton({
    required this.segment,
    required this.selected,
    required this.onTap,
  });

  final AppSegment<dynamic> segment;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Color fg = selected ? cs.foreground : cs.mutedForeground;
    return Semantics(
      button: true,
      selected: selected,
      inMutuallyExclusiveGroup: true,
      label: segment.label,
      // 자식 의미 정보를 걸러 내므로 탭 동작을 여기서 직접 노출한다.
      onTap: onTap,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        // 선택 표시 이동만 150ms로 바뀐다(§23).
        child: AnimatedContainer(
          duration: AppMotion.selection,
          curve: AppMotion.standard,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? cs.card : Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadii.sm),
            border: selected ? Border.all(color: cs.border) : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              if (segment.icon != null) ...<Widget>[
                Icon(segment.icon, size: 16, color: fg),
                const SizedBox(width: AppSpace.s4),
              ],
              Flexible(
                child: Text(
                  segment.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.withWeight(
                    AppTextStyles.bodySmall,
                    selected ? FontWeight.w600 : FontWeight.w400,
                  ).copyWith(color: fg),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
