// Buttons, Inputs 섹션.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_shad_theme.dart';
import '../../../core/design_system/app_text_styles.dart';
import '../../../core/design_system/app_tokens.dart';
import '../widgets.dart';

void _noop() {}

List<Widget> buttonInputSections(BuildContext context) {
  final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
  final TextStyle label = AppTextStyles.caption.copyWith(
    color: cs.mutedForeground,
  );

  Widget variantRow(
    String name,
    Widget Function(ShadButtonSize size, TextStyle? style) build,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.s12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('$name · default 48 / compact 40', style: label),
          const SizedBox(height: AppSpace.s8),
          Wrap(
            spacing: AppSpace.s8,
            runSpacing: AppSpace.s8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              build(ShadButtonSize.regular, null),
              build(ShadButtonSize.sm, AppTextStyles.buttonCompact),
            ],
          ),
        ],
      ),
    );
  }

  return <Widget>[
    PreviewSection(
      title: 'Buttons',
      description: '한 화면의 Primary는 1개(§8). 여기서는 견본으로 모두 보인다',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              variantRow(
                'Primary',
                (s, t) => ShadButton(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('기록 저장'),
                ),
              ),
              variantRow(
                'Secondary',
                (s, t) => ShadButton.secondary(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('나중에'),
                ),
              ),
              variantRow(
                'Outline',
                (s, t) => ShadButton.outline(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('다시 시도'),
                ),
              ),
              variantRow(
                'Ghost',
                (s, t) => ShadButton.ghost(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('편집'),
                ),
              ),
              variantRow(
                'Link',
                (s, t) => ShadButton.link(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('전체 보기'),
                ),
              ),
              variantRow(
                'Destructive',
                (s, t) => ShadButton.destructive(
                  size: s,
                  textStyle: t,
                  onPressed: _noop,
                  child: const Text('삭제'),
                ),
              ),
              Text('비활성 (투명도 0.5)', style: label),
              const SizedBox(height: AppSpace.s8),
              const Wrap(
                spacing: AppSpace.s8,
                runSpacing: AppSpace.s8,
                children: <Widget>[
                  ShadButton(enabled: false, child: Text('기록 저장')),
                  ShadButton.outline(enabled: false, child: Text('다시 시도')),
                ],
              ),
              const SizedBox(height: AppSpace.s12),
              Text('로딩 (16 인디케이터, 폭 유지)', style: label),
              const SizedBox(height: AppSpace.s8),
              ShadButton(
                width: double.infinity,
                onPressed: _noop,
                leading: SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: cs.primaryForeground,
                  ),
                ),
                child: const Text('저장 중'),
              ),
              const SizedBox(height: AppSpace.s12),
              Text('아이콘 라벨 18 / 아이콘 버튼 48 (아이콘 20)', style: label),
              const SizedBox(height: AppSpace.s8),
              Wrap(
                spacing: AppSpace.s8,
                runSpacing: AppSpace.s8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: <Widget>[
                  const ShadButton(
                    onPressed: _noop,
                    leading: Icon(LucideIcons.plus, size: 18),
                    child: Text('운동 추가'),
                  ),
                  for (final (IconData icon, String semantic)
                      in <(IconData, String)>[
                        (LucideIcons.chevronLeft, '뒤로'),
                        (LucideIcons.trash2, '삭제'),
                        (LucideIcons.ellipsis, '더보기'),
                      ])
                    Semantics(
                      label: semantic,
                      button: true,
                      child: ShadIconButton.ghost(
                        onPressed: _noop,
                        iconSize: 20,
                        icon: Icon(icon),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ],
    ),
    PreviewSection(
      title: 'Inputs',
      description: '라벨은 항상 보이고, 오류는 테두리 + 문구 + 아이콘(§10)',
      children: <Widget>[
        PreviewCard(
          child: ShadForm(
            autovalidateMode: ShadAutovalidateMode.always,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                ShadInputFormField(
                  id: 'name',
                  label: const Text('이름'),
                  placeholder: const Text('이름을 입력하세요'),
                  description: const Text('코치가 부를 이름입니다.'),
                ),
                const SizedBox(height: AppSpace.s16),
                ShadInputFormField(
                  id: 'weight',
                  label: const Text('체중'),
                  initialValue: '72.4',
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  trailing: _unit(cs, 'kg'),
                  description: const Text('소수점 한 자리까지 입력합니다.'),
                ),
                const SizedBox(height: AppSpace.s16),
                ShadInputFormField(
                  id: 'height',
                  label: const Text('키'),
                  initialValue: '500',
                  keyboardType: TextInputType.number,
                  trailing: _unit(cs, 'cm'),
                  validator: (String v) {
                    final double? n = double.tryParse(v);
                    if (n == null || n < 100 || n > 250) {
                      return '100~250 사이로 입력하세요.';
                    }
                    return null;
                  },
                  error: (String message) => Row(
                    children: <Widget>[
                      Icon(LucideIcons.circleX, size: 16, color: cs.error),
                      const SizedBox(width: AppSpace.s4),
                      Flexible(child: Text(message)),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpace.s16),
                ShadTextareaFormField(
                  id: 'memo',
                  label: const Text('메모'),
                  placeholder: const Text('오늘 컨디션을 적어 두세요'),
                  description: const Text('최소 3줄 높이입니다.'),
                ),
                const SizedBox(height: AppSpace.s16),
                // 0.57.1 Select는 내용 폭이 기본이라 부모 폭을 minWidth로 넘겨 전체 폭으로 맞춘다(§10).
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    return ShadSelectFormField<String>(
                      id: 'goal',
                      label: const Text('목표'),
                      initialValue: 'cut',
                      minWidth: constraints.maxWidth,
                      options: <Widget>[
                        for (final MapEntry<String, String> e
                            in _goals.entries)
                          ShadOption<String>(
                            value: e.key,
                            child: Text(e.value),
                          ),
                      ],
                      selectedOptionBuilder:
                          (BuildContext context, String value) =>
                              Text(_goals[value] ?? value),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  ];
}

const Map<String, String> _goals = <String, String>{
  'cut': '체지방 감량',
  'bulk': '근육 증가',
  'keep': '체중 유지',
};

Widget _unit(ShadColorScheme cs, String unit) {
  return Text(
    unit,
    style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
  );
}
