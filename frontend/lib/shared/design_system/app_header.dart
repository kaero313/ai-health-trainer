// Root / Detail 헤더 (docs/DESIGN_SYSTEM.md §11-2). 브랜드명과 알림 아이콘은 두지 않는다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class AppHeader extends StatelessWidget {
  /// 탭 루트 화면: display 큰 제목 + 선택적 부제 + 선택적 오른쪽 액션.
  const AppHeader.root({
    super.key,
    required this.title,
    this.subtitle,
    this.action,
  }) : onBack = null,
       backLabel = '뒤로',
       _detail = false;

  /// 상세 화면: Ghost 뒤로 버튼(48) + title 제목 + 선택적 오른쪽 액션.
  const AppHeader.detail({
    super.key,
    required this.title,
    required this.onBack,
    this.backLabel = '뒤로',
    this.action,
  }) : subtitle = null,
       _detail = true;

  final String title;
  final String? subtitle;

  /// 오른쪽 Ghost 아이콘 액션 1개. 기능이 있는 액션만 둔다.
  final Widget? action;
  final VoidCallback? onBack;

  /// 뒤로 버튼 접근성 라벨.
  final String backLabel;
  final bool _detail;

  @override
  Widget build(BuildContext context) {
    return _detail ? _buildDetail(context) : _buildRoot(context);
  }

  Widget _buildRoot(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpace.s16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Semantics(
                  header: true,
                  child: Text(
                    title,
                    style: AppTextStyles.display.copyWith(color: cs.foreground),
                  ),
                ),
                if (subtitle != null) ...<Widget>[
                  const SizedBox(height: AppSpace.s4),
                  Text(
                    subtitle!,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: cs.mutedForeground,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (action != null) ...<Widget>[
            const SizedBox(width: AppSpace.s8),
            action!,
          ],
        ],
      ),
    );
  }

  Widget _buildDetail(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpace.s8),
      child: Row(
        children: <Widget>[
          Semantics(
            label: backLabel,
            button: true,
            // 자식 의미 정보를 걸러 내므로 탭 동작을 여기서 직접 노출한다.
            onTap: onBack,
            excludeSemantics: true,
            child: ShadIconButton.ghost(
              onPressed: onBack,
              iconSize: 20,
              icon: const Icon(LucideIcons.arrowLeft),
            ),
          ),
          const SizedBox(width: AppSpace.s4),
          Expanded(
            child: Semantics(
              header: true,
              child: Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTextStyles.title.copyWith(color: cs.foreground),
              ),
            ),
          ),
          if (action != null) ...<Widget>[
            const SizedBox(width: AppSpace.s4),
            action!,
          ],
        ],
      ),
    );
  }
}
