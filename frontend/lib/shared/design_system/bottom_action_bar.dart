// 입력 화면 하단 고정 바 (docs/DESIGN_SYSTEM.md §8, §10). 전체 폭 Primary 버튼 1개.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class AppBottomActionBar extends StatelessWidget {
  const AppBottomActionBar({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.loading = false,
    this.loadingLabel,
    this.errorText,
  });

  /// 버튼 위아래 12, 좌우는 페이지 여백 20.
  static const EdgeInsets padding = EdgeInsets.symmetric(
    horizontal: AppSpace.s20,
    vertical: AppSpace.s12,
  );

  final String label;

  /// null이면 비활성(투명도 0.5, 터치 차단).
  final VoidCallback? onPressed;

  /// 라벨 왼쪽 아이콘(18).
  final IconData? icon;

  /// 저장 중. 라벨 자리에 16 인디케이터를 두고 버튼 폭은 그대로다(§8).
  final bool loading;

  /// 저장 중일 때 스크린리더가 읽는 문구. 없으면 "[label] 중".
  final String? loadingLabel;

  /// 버튼 위 오류 문구. circle-x 아이콘과 error 색으로 보인다(§10).
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Widget button = ShadButton(
      width: double.infinity,
      // 저장 중에는 비활성처럼 흐려지지 않게 누름만 무시한다.
      onPressed: loading ? () {} : onPressed,
      leading: loading || icon == null ? null : Icon(icon, size: 18),
      child: loading
          ? SizedBox.square(
              dimension: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: cs.primaryForeground,
              ),
            )
          : Text(label),
    );
    return DecoratedBox(
      decoration: BoxDecoration(
        color: cs.background,
        border: Border(top: BorderSide(color: cs.border)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: padding,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (errorText != null) ...<Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Padding(
                      // bodySmall 행간 18에서 아이콘 16을 가운데로
                      padding: const EdgeInsets.only(top: 1),
                      child: Icon(
                        LucideIcons.circleX,
                        size: 16,
                        color: cs.error,
                      ),
                    ),
                    const SizedBox(width: AppSpace.s4),
                    Expanded(
                      child: Text(
                        errorText!,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: AppTextStyles.bodySmall.copyWith(
                          color: cs.error,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.s8),
              ],
              loading
                  ? Semantics(
                      label: loadingLabel ?? '$label 중',
                      button: true,
                      excludeSemantics: true,
                      child: button,
                    )
                  : button,
            ],
          ),
        ),
      ),
    );
  }
}
