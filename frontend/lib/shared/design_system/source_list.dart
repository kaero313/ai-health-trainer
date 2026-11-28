// 검증된 AI 출처 목록 (docs/DESIGN_SYSTEM.md §16 SourceList, §21-2).
// backend가 검증한 sources만 보이고, 없으면 없다고 보인다. 출처는 정보라 강조색을 쓰지 않는다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_badge.dart';

class SourceList extends StatelessWidget {
  const SourceList({
    super.key,
    required this.sources,
    this.maxVisible,
    this.title = '검증된 출처',
    this.emptyLabel = '확인된 출처가 없습니다',
  });

  final List<String> sources;

  /// 이 개수까지만 보이고 나머지는 "+N" 배지로 줄인다(채팅 말풍선 등). null이면 모두.
  final int? maxVisible;
  final String title;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final int visible = maxVisible == null
        ? sources.length
        : sources.length.clamp(0, maxVisible!);
    final int hidden = sources.length - visible;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Semantics(
          header: true,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(LucideIcons.badgeCheck, size: 16, color: cs.mutedForeground),
              const SizedBox(width: AppSpace.s4),
              Text(
                title,
                style: AppTextStyles.caption.copyWith(
                  color: cs.mutedForeground,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.s8),
        if (sources.isEmpty)
          Text(
            emptyLabel,
            style: AppTextStyles.bodySmall.copyWith(color: cs.mutedForeground),
          )
        else
          Wrap(
            spacing: AppSpace.s8,
            runSpacing: AppSpace.s8,
            children: <Widget>[
              for (final String source in sources.take(visible))
                AppBadge.outline(icon: LucideIcons.fileText, label: source),
              if (hidden > 0)
                AppBadge.neutral(
                  label: '+$hidden',
                  semanticLabel: '출처 $hidden개 더 있음',
                ),
            ],
          ),
      ],
    );
  }
}
