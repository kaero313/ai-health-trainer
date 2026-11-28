// 입력 칸 (docs/DESIGN_SYSTEM.md §10). 라벨은 항상 보이고, 오류는 테두리 + 문구 + circle-x 아이콘
// 한 가지 방식이다. 숫자 단위는 칸 안 오른쪽 접미사, 비밀번호 보기 같은 동작은 오른쪽 아이콘 버튼이다.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_shad_theme.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

/// 입력 칸 오른쪽 아이콘 버튼(예: 비밀번호 표시).
@immutable
class AppTextFieldAction {
  const AppTextFieldAction({
    required this.icon,
    required this.semanticLabel,
    required this.onPressed,
  });

  final IconData icon;

  /// 스크린리더가 읽는 이름(예: "비밀번호 표시").
  final String semanticLabel;
  final VoidCallback onPressed;
}

class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    required this.label,
    this.controller,
    this.placeholder,
    this.description,
    this.errorText,
    this.unit,
    this.action,
    this.keyboardType,
    this.textInputAction,
    this.autofillHints,
    this.inputFormatters,
    this.obscureText = false,
    this.enabled = true,
    this.onChanged,
    this.onSubmitted,
  }) : assert(unit == null || action == null, '단위와 동작 버튼은 함께 쓰지 않는다');

  /// 동작 버튼 크기. 칸 높이(48)에서 테두리 2를 뺀 값이라 칸 높이가 그대로다.
  static const double actionSize = 46;

  /// 칸 위 라벨. placeholder로 대신하지 않는다(§10).
  final String label;
  final TextEditingController? controller;
  final String? placeholder;

  /// 칸 아래 도움말. 오류가 있으면 오류가 대신 보인다.
  final String? description;

  /// 오류 문구. null이 아니면 테두리가 error 색이 되고 칸 아래에 아이콘과 함께 보인다.
  final String? errorText;

  /// 칸 안 오른쪽 단위 접미사(kg·g·kcal·cm·세).
  final String? unit;
  final AppTextFieldAction? action;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final Iterable<String>? autofillHints;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final bool enabled;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final AppTextFieldAction? a = action;
    return ShadInputFormField(
      controller: controller,
      label: Text(label),
      placeholder: placeholder == null ? null : Text(placeholder!),
      // 칸 아래에는 도움말이나 오류 중 하나만 보인다(§10).
      description: description == null || errorText != null
          ? null
          : Text(description!),
      forceErrorText: errorText,
      error: (String message) => _ErrorLine(message: message),
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      autofillHints: autofillHints,
      inputFormatters: inputFormatters,
      obscureText: obscureText,
      enabled: enabled,
      onChanged: onChanged,
      onSubmitted: onSubmitted,
      // 동작 버튼이 있으면 위아래 여백을 버튼이 채운다. 그래야 누르는 영역 46을 두고도 칸 높이가 48이다.
      padding: a == null ? null : const EdgeInsets.only(left: AppSpace.s12),
      trailing: a != null
          ? Semantics(
              label: a.semanticLabel,
              button: true,
              onTap: a.onPressed,
              excludeSemantics: true,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: a.onPressed,
                child: SizedBox.square(
                  dimension: actionSize,
                  child: Icon(a.icon, size: 20, color: cs.mutedForeground),
                ),
              ),
            )
          : unit == null
          ? null
          : Text(
              unit!,
              style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
            ),
    );
  }
}

class _ErrorLine extends StatelessWidget {
  const _ErrorLine({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Padding(
          // bodySmall 행간 18에서 아이콘 16을 가운데로
          padding: const EdgeInsets.only(top: 1),
          child: Icon(LucideIcons.circleX, size: 16, color: cs.error),
        ),
        const SizedBox(width: AppSpace.s4),
        Expanded(
          child: Text(
            message,
            style: AppTextStyles.bodySmall.copyWith(color: cs.error),
          ),
        ),
      ],
    );
  }
}
