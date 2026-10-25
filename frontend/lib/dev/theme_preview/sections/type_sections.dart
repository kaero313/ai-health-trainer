// Typography, Radius, Spacing 섹션.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_text_styles.dart';
import '../../../core/design_system/app_tokens.dart';
import '../widgets.dart';

List<Widget> typographySections(BuildContext context) {
  final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
  return <Widget>[
    PreviewSection(
      title: 'Typography',
      description: '§4-2 11단계. 한글은 Noto Sans KR, 숫자는 Geist',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              for (final (String name, TextStyle style) in AppTextStyles.scale)
                _TypeRow(name: name, style: style, cs: cs),
            ],
          ),
        ),
      ],
    ),
  ];
}

List<Widget> radiusSpacingSections(BuildContext context) {
  final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
  final TextStyle label = AppTextStyles.caption.copyWith(
    color: cs.mutedForeground,
  );
  return <Widget>[
    PreviewSection(
      title: 'Radius',
      children: <Widget>[
        PreviewCard(
          child: Wrap(
            spacing: AppSpace.s12,
            runSpacing: AppSpace.s12,
            children: <Widget>[
              for (final (String name, double value) in AppRadii.all)
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: cs.muted,
                        border: Border.all(color: cs.input),
                        borderRadius: BorderRadius.circular(value),
                      ),
                    ),
                    const SizedBox(height: AppSpace.s4),
                    Text('$name ${value.toInt()}', style: label),
                  ],
                ),
            ],
          ),
        ),
      ],
    ),
    PreviewSection(
      title: 'Spacing',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (final (String name, double value) in AppSpace.all)
                SizedBox(
                  height: 32,
                  child: Row(
                    children: <Widget>[
                      SizedBox(width: 48, child: Text(name, style: label)),
                      Container(
                        width: value,
                        height: 16,
                        decoration: BoxDecoration(
                          color: cs.mutedForeground,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      const SizedBox(width: AppSpace.s8),
                      Text(
                        '${value.toInt()}',
                        style: AppTextStyles.numSmall.copyWith(
                          color: cs.foreground,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ],
    ),
  ];
}

class _TypeRow extends StatelessWidget {
  const _TypeRow({required this.name, required this.style, required this.cs});

  final String name;
  final TextStyle style;
  final ShadColorScheme cs;

  @override
  Widget build(BuildContext context) {
    final bool isNumber = style.fontFamily == AppTextStyles.numberFamily;
    final double size = style.fontSize!;
    final int lineHeight = (size * style.height!).round();
    final String family = isNumber ? 'Geist' : 'Noto Sans KR';
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.s16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '$name · ${size.toInt()}/$lineHeight · '
            '${style.fontWeight!.value} · $family',
            style: AppTextStyles.caption.copyWith(color: cs.mutedForeground),
          ),
          const SizedBox(height: AppSpace.s4),
          if (isNumber)
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: <Widget>[
                Text('72.4', style: style.copyWith(color: cs.foreground)),
                const SizedBox(width: AppSpace.s4),
                Text(
                  'kg',
                  style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
                ),
              ],
            )
          else
            Text(
              '오늘의 진행 1,185 kcal',
              style: style.copyWith(color: cs.foreground),
            ),
        ],
      ),
    );
  }
}
