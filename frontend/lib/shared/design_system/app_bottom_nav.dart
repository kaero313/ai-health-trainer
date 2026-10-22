// 화면 아래에 붙은 하단 탭 (docs/DESIGN_SYSTEM.md §11-1).
// 바 면은 하단 safe area까지 이어지고, 아이콘과 라벨은 그 위 64 안에 둔다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_motion.dart';
import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

@immutable
class AppBottomNavItem {
  const AppBottomNavItem({required this.icon, required this.label});

  final IconData icon;
  final String label;
}

class AppBottomNav extends StatelessWidget {
  const AppBottomNav({
    super.key,
    required this.items,
    required this.selectedIndex,
    required this.onSelected,
  });

  /// 아이콘·라벨이 들어가는 영역 높이. 바 전체 높이는 여기에 하단 safe area를 더한다.
  static const double contentHeight = 64;

  /// 선택 표시 알약 크기 (§11-1).
  static const Size indicatorSize = Size(56, 32);

  static ValueKey<String> itemKey(int index) =>
      ValueKey<String>('app-bottom-nav-item-$index');

  final List<AppBottomNavItem> items;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final double bottomInset = MediaQuery.paddingOf(context).bottom;
    // DecoratedBox는 border 두께만큼 안쪽 여백을 만들지 않는다. 그래서 바 높이가
    // 정확히 64 + safe area이고, 위쪽 1px 선은 64 영역 맨 위에 그려진다.
    return DecoratedBox(
      decoration: BoxDecoration(
        color: cs.card,
        border: Border(top: BorderSide(color: cs.border)),
      ),
      child: Padding(
        padding: EdgeInsets.only(bottom: bottomInset),
        child: SizedBox(
          height: contentHeight,
          child: Row(
            children: <Widget>[
              for (int i = 0; i < items.length; i++)
                Expanded(
                  child: _NavItem(
                    key: itemKey(i),
                    item: items[i],
                    selected: i == selectedIndex,
                    onTap: () => onSelected(i),
                    position: i + 1,
                    count: items.length,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    super.key,
    required this.item,
    required this.selected,
    required this.onTap,
    required this.position,
    required this.count,
  });

  final AppBottomNavItem item;
  final bool selected;
  final VoidCallback onTap;
  final int position;
  final int count;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Color fg = selected ? cs.primary : cs.mutedForeground;
    return Semantics(
      button: true,
      selected: selected,
      label: '${item.label} 탭, $count개 중 $position번째',
      // 자식 의미 정보를 걸러 내므로 탭 동작을 여기서 직접 노출한다.
      onTap: onTap,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            AnimatedContainer(
              duration: AppMotion.selection,
              curve: AppMotion.standard,
              width: AppBottomNav.indicatorSize.width,
              height: AppBottomNav.indicatorSize.height,
              decoration: BoxDecoration(
                color: selected
                    ? cs.primaryMuted
                    : cs.primaryMuted.withAlpha(0),
                borderRadius: BorderRadius.circular(AppRadii.full),
              ),
              alignment: Alignment.center,
              child: TweenAnimationBuilder<Color?>(
                tween: ColorTween(end: fg),
                duration: AppMotion.selection,
                builder: (BuildContext context, Color? color, Widget? _) =>
                    Icon(item.icon, size: 24, color: color),
              ),
            ),
            const SizedBox(height: AppSpace.s4),
            AnimatedDefaultTextStyle(
              duration: AppMotion.selection,
              style: AppTextStyles.caption.copyWith(color: fg),
              child: Text(
                item.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                // 탭 라벨은 64 영역 안에 있어야 하므로 큰 글자 배율을 1.3에서 멈춘다.
                textScaler: MediaQuery.textScalerOf(
                  context,
                ).clamp(maxScaleFactor: 1.3),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
