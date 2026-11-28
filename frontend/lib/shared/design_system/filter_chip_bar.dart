// 가로 스크롤 선택 칩 (docs/DESIGN_SYSTEM.md §11-3). 하나만 고른다.
// 선택 칩은 primaryMuted 면 + primary 글자, 나머지는 1px border + foreground 글자.
// 보이는 높이는 36, 누르는 영역은 48이다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

@immutable
class FilterChipItem<T> {
  const FilterChipItem({required this.value, required this.label});

  /// null은 "전체" 같은 선택 없음 칩이다.
  final T? value;
  final String label;
}

class FilterChipBar<T> extends StatelessWidget {
  const FilterChipBar({
    super.key,
    required this.items,
    required this.selected,
    required this.onSelected,
  });

  static const double chipHeight = 36;
  static const double hitHeight = 48;

  final List<FilterChipItem<T>> items;
  final T? selected;
  final ValueChanged<T?> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: hitHeight,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (BuildContext context, int index) =>
            const SizedBox(width: AppSpace.s8),
        itemBuilder: (BuildContext context, int index) {
          final FilterChipItem<T> item = items[index];
          return _Chip(
            label: item.label,
            selected: item.value == selected,
            onTap: () => onSelected(item.value),
          );
        },
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      // 자식 의미 정보를 걸러 내므로 탭 동작을 여기서 직접 노출한다.
      onTap: onTap,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Center(
          child: Container(
            height: FilterChipBar.chipHeight,
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s12),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected ? cs.primaryMuted : null,
              borderRadius: BorderRadius.circular(AppRadii.full),
              border: Border.all(color: selected ? cs.primaryMuted : cs.border),
            ),
            child: Text(
              label,
              maxLines: 1,
              style: AppTextStyles.withWeight(
                AppTextStyles.bodySmall,
                selected ? FontWeight.w600 : FontWeight.w400,
              ).copyWith(color: selected ? cs.primary : cs.foreground),
            ),
          ),
        ),
      ),
    );
  }
}
