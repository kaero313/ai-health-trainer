// 전체 폭 선택 칸 (docs/DESIGN_SYSTEM.md §10 선택).
// shadcn_ui 0.57.1의 Select는 내용 폭이 기본이라 부모 폭을 minWidth로 넘겨 입력 칸과 폭을 맞춘다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

class AppSelectField<T> extends StatelessWidget {
  const AppSelectField({
    super.key,
    this.id,
    required this.label,
    required this.options,
    this.initialValue,
    this.placeholder,
    this.description,
    this.onChanged,
    this.validator,
    this.enabled = true,
  });

  /// ShadForm 안에서 값을 읽는 키.
  final String? id;

  /// 칸 위 라벨. 항상 보인다(§10).
  final String label;

  /// 값 → 보이는 이름. 순서대로 보인다.
  final Map<T, String> options;
  final T? initialValue;
  final String? placeholder;
  final String? description;
  final ValueChanged<T?>? onChanged;
  final String? Function(T?)? validator;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        return ShadSelectFormField<T>(
          id: id,
          label: Text(label),
          initialValue: initialValue,
          enabled: enabled,
          minWidth: constraints.maxWidth,
          placeholder: placeholder == null ? null : Text(placeholder!),
          description: description == null ? null : Text(description!),
          onChanged: onChanged,
          validator: validator,
          options: <Widget>[
            for (final MapEntry<T, String> e in options.entries)
              ShadOption<T>(value: e.key, child: Text(e.value)),
          ],
          selectedOptionBuilder: (BuildContext context, T value) =>
              Text(options[value] ?? '$value'),
        );
      },
    );
  }
}
