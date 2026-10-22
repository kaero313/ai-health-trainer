// 카드 (docs/DESIGN_SYSTEM.md §9). ShadCard 한 가지 모양이고 그림자·glow가 없다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    this.title,
    this.trailing,
    required this.children,
    this.emphasis = false,
  });

  /// 안쪽 여백. 화면 대표 카드 1개만 [emphasisPadding]을 쓴다(§5).
  static const double padding = AppSpace.s16;
  static const double emphasisPadding = AppSpace.s20;

  /// 헤더 왼쪽 heading 제목.
  final String? title;

  /// 헤더 오른쪽 배지 1개나 [AppCardAction] 1개.
  final Widget? trailing;

  /// 본문 블록. 블록 사이는 16이다.
  final List<Widget> children;

  /// 화면 대표 카드면 안쪽 여백 20.
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final bool hasHeader = title != null || trailing != null;
    final double inset = emphasis ? emphasisPadding : padding;
    // AppCardAction의 누르는 영역은 보이는 버튼보다 위아래로 4씩 넓다. 그만큼 위 여백과
    // 헤더 아래 간격을 줄여 보이는 배치는 높이 40 헤더와 같게 둔다.
    final double overflow = trailing is AppCardAction
        ? AppCardAction.hitOverflow
        : 0;
    final List<Widget> blocks = <Widget>[
      if (hasHeader)
        Row(
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
      ...children,
    ];
    return ShadCard(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(inset, inset - overflow, inset, inset),
      columnCrossAxisAlignment: CrossAxisAlignment.stretch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          for (int i = 0; i < blocks.length; i++) ...<Widget>[
            if (i > 0)
              SizedBox(
                height: hasHeader && i == 1
                    ? AppSpace.s16 - overflow
                    : AppSpace.s16,
              ),
            blocks[i],
          ],
        ],
      ),
    );
  }
}

/// 카드 헤더 오른쪽 이동 액션("보기", "기록하기"). Ghost라 강조색을 쓰지 않는다(§9).
/// 보이는 높이는 compact 40이고, 누르는 영역은 위아래로 4씩 넓혀 48이다.
class AppCardAction extends StatelessWidget {
  const AppCardAction({
    super.key,
    required this.label,
    required this.onPressed,
  });

  static const double visualHeight = 40;
  static const double hitHeight = 48;

  /// 누르는 영역이 보이는 버튼 위아래로 넘치는 길이.
  static const double hitOverflow = (hitHeight - visualHeight) / 2;

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    // 버튼 위아래 4는 바깥 GestureDetector가 받고, 버튼 안은 버튼이 받는다.
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      excludeFromSemantics: true,
      onTap: onPressed,
      child: SizedBox(
        height: hitHeight,
        child: Center(
          child: ShadButton.ghost(
            size: ShadButtonSize.sm,
            textStyle: AppTextStyles.buttonCompact,
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s8),
            onPressed: onPressed,
            trailing: Icon(
              LucideIcons.chevronRight,
              size: 16,
              color: cs.mutedForeground,
            ),
            child: Text(label),
          ),
        ),
      ),
    );
  }
}

/// 아이콘 타일: 40, muted 면, 반경 12, 아이콘 20 foreground (§9, §14).
class AppIconTile extends StatelessWidget {
  const AppIconTile({super.key, required this.icon});

  static const double size = 40;

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: cs.muted,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Icon(icon, size: 20, color: cs.foreground),
    );
  }
}

/// 카드 전체가 눌리는 이동 행: 아이콘 타일 + 제목 + 선택적 부제 + chevron (§9 Nav row).
class NavRowCard extends StatefulWidget {
  const NavRowCard({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  State<NavRowCard> createState() => _NavRowCardState();
}

class _NavRowCardState extends State<NavRowCard> {
  bool _pressed = false;

  void _setPressed(bool value) {
    if (_pressed != value) setState(() => _pressed = value);
  }

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _setPressed(true),
        onTapUp: (_) => _setPressed(false),
        onTapCancel: () => _setPressed(false),
        onTap: widget.onTap,
        child: ShadCard(
          width: double.infinity,
          backgroundColor: _pressed ? cs.accent : cs.card,
          child: Row(
            children: <Widget>[
              AppIconTile(icon: widget.icon),
              const SizedBox(width: AppSpace.s12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      widget.title,
                      style: AppTextStyles.bodyStrong.copyWith(
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
              const SizedBox(width: AppSpace.s8),
              Icon(
                LucideIcons.chevronRight,
                size: 20,
                color: cs.mutedForeground,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
