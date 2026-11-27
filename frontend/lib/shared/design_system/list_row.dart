// List 카드와 행 (docs/DESIGN_SYSTEM.md §9 List, §16 ListRow).
// 카드 한 장 안에 행을 구분선으로 잇는다. 행이 눌리면 카드 폭 전체가 accent 면이 된다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_card.dart';

/// 선택적 heading 제목 + 구분선으로 이은 [ListRow]들.
class AppListCard extends StatelessWidget {
  const AppListCard({super.key, this.title, this.trailing, required this.rows});

  /// 행과 제목의 좌우 여백. 카드 안쪽 여백과 같다.
  static const double inset = AppSpace.s16;

  final String? title;

  /// 제목 오른쪽 배지나 AppCardAction 1개.
  final Widget? trailing;
  final List<Widget> rows;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return ShadCard(
      width: double.infinity,
      padding: EdgeInsets.zero,
      columnCrossAxisAlignment: CrossAxisAlignment.stretch,
      // 첫·마지막 행의 눌림 면이 둥근 모서리 밖으로 나가지 않게 자른다(반경 16 - 테두리 1).
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadii.lg - 1),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (title != null || trailing != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(inset, inset, inset, 4),
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: title == null
                          ? const SizedBox.shrink()
                          : Semantics(
                              header: true,
                              child: Text(
                                title!,
                                style: AppTextStyles.heading.copyWith(
                                  color: cs.cardForeground,
                                ),
                              ),
                            ),
                    ),
                    if (trailing != null) ...<Widget>[
                      const SizedBox(width: AppSpace.s8),
                      trailing!,
                    ],
                  ],
                ),
              ),
            for (int i = 0; i < rows.length; i++) ...<Widget>[
              if (i > 0)
                Divider(
                  height: 1,
                  thickness: 1,
                  indent: inset,
                  endIndent: inset,
                  color: cs.border,
                ),
              rows[i],
            ],
          ],
        ),
      ),
    );
  }
}

/// 아이콘 타일·제목·부제·값·chevron 행. [onTap]이 있으면 행 전체가 눌린다.
class ListRow extends StatefulWidget {
  const ListRow({
    super.key,
    required this.title,
    this.subtitle,
    this.icon,
    this.value,
    this.valueMuted = false,
    this.onTap,
  });

  /// 행 최소 높이(누르는 영역 48 이상).
  static const double minHeight = 56;

  final String title;
  final String? subtitle;

  /// 왼쪽 아이콘 타일(40).
  final IconData? icon;

  /// 오른쪽 값. 숫자 글꼴(Geist), body 크기다.
  final String? value;

  /// 값이 없음을 뜻하는 문구("기록 없음", "기기 미연결")면 mutedForeground로 칠한다(§21-2).
  final bool valueMuted;
  final VoidCallback? onTap;

  @override
  State<ListRow> createState() => _ListRowState();
}

class _ListRowState extends State<ListRow> {
  bool _pressed = false;

  void _setPressed(bool value) {
    if (_pressed != value) setState(() => _pressed = value);
  }

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final bool tappable = widget.onTap != null;
    final Widget content = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: ListRow.minHeight),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppListCard.inset,
          vertical: AppSpace.s12,
        ),
        child: Row(
          children: <Widget>[
            if (widget.icon != null) ...<Widget>[
              AppIconTile(icon: widget.icon!),
              const SizedBox(width: AppSpace.s12),
            ],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    widget.title,
                    style: AppTextStyles.body.copyWith(
                      color: cs.cardForeground,
                    ),
                  ),
                  if (widget.subtitle != null)
                    Text(
                      widget.subtitle!,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: cs.mutedForeground,
                      ),
                    ),
                ],
              ),
            ),
            if (widget.value != null) ...<Widget>[
              const SizedBox(width: AppSpace.s12),
              Text(
                widget.value!,
                textAlign: TextAlign.end,
                style: AppTextStyles.body.copyWith(
                  fontFamily: AppTextStyles.numberFamily,
                  fontFamilyFallback: const <String>[AppTextStyles.textFamily],
                  fontFeatures: const <FontFeature>[
                    FontFeature.tabularFigures(),
                  ],
                  color: widget.valueMuted
                      ? cs.mutedForeground
                      : cs.cardForeground,
                ),
              ),
            ],
            if (tappable) ...<Widget>[
              const SizedBox(width: AppSpace.s8),
              Icon(
                LucideIcons.chevronRight,
                size: 20,
                color: cs.mutedForeground,
              ),
            ],
          ],
        ),
      ),
    );
    if (!tappable) {
      return Semantics(
        label: widget.value == null ? null : '${widget.title}, ${widget.value}',
        excludeSemantics: widget.value != null,
        child: content,
      );
    }
    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _setPressed(true),
        onTapUp: (_) => _setPressed(false),
        onTapCancel: () => _setPressed(false),
        onTap: widget.onTap,
        // 눌림은 애니메이션 없이 즉시 accent 면(§23).
        child: ColoredBox(
          color: _pressed ? cs.accent : Colors.transparent,
          child: content,
        ),
      ),
    );
  }
}
