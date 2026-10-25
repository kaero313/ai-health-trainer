// 색 섹션: Surfaces, Actions, Text, Border·Input·Ring, Status.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_shad_theme.dart';
import '../../../core/design_system/app_text_styles.dart';
import '../../../core/design_system/app_tokens.dart';
import '../widgets.dart';

List<Widget> colorSections(BuildContext context) {
  final ShadThemeData theme = ShadTheme.of(context);
  final ShadColorScheme cs = theme.colorScheme;
  final AppColorTokens tokens = AppColorTokens.of(theme.brightness);

  TextStyle muted(TextStyle s) => s.copyWith(color: cs.mutedForeground);

  return <Widget>[
    PreviewSection(
      title: 'Surfaces',
      description: 'background < card < popover 순서의 면',
      children: <Widget>[
        SurfaceSwatch(
          name: 'background',
          surface: cs.background,
          onSurfaceName: 'foreground',
          onSurface: cs.foreground,
        ),
        SurfaceSwatch(
          name: 'card (Surface)',
          surface: cs.card,
          onSurfaceName: 'cardForeground',
          onSurface: cs.cardForeground,
        ),
        SurfaceSwatch(
          name: 'muted',
          surface: cs.muted,
          onSurfaceName: 'mutedForeground',
          onSurface: cs.mutedForeground,
          sample: '트랙·스켈레톤·비활성 면',
        ),
        SurfaceSwatch(
          name: 'popover',
          surface: cs.popover,
          onSurfaceName: 'popoverForeground',
          onSurface: cs.popoverForeground,
          sample: '시트·토스트 72.4 kg',
        ),
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Text(
                '전체 토큰 ${tokens.entries.length}개',
                style: AppTextStyles.bodyStrong.copyWith(color: cs.foreground),
              ),
              const SizedBox(height: AppSpace.s8),
              for (final (String name, Color color) in tokens.entries)
                ColorChipRow(name: name, color: color),
            ],
          ),
        ),
      ],
    ),
    PreviewSection(
      title: 'Actions',
      description: '면 위 글자는 각 foreground 토큰',
      children: <Widget>[
        SurfaceSwatch(
          name: 'primary',
          surface: cs.primary,
          onSurfaceName: 'primaryForeground',
          onSurface: cs.primaryForeground,
          sample: '기록 저장',
        ),
        SurfaceSwatch(
          name: 'secondary',
          surface: cs.secondary,
          onSurfaceName: 'secondaryForeground',
          onSurface: cs.secondaryForeground,
          sample: '취소',
        ),
        SurfaceSwatch(
          name: 'destructive',
          surface: cs.destructive,
          onSurfaceName: 'destructiveForeground',
          onSurface: cs.destructiveForeground,
          sample: '삭제',
        ),
      ],
    ),
    PreviewSection(
      title: 'Text',
      description: 'WCAG 2.x 대비. 본문 4.5, 큰 글자·UI 3.0',
      children: <Widget>[
        for (final (String bgName, Color bg) in <(String, Color)>[
          ('background', cs.background),
          ('card', cs.card),
        ])
          Container(
            padding: const EdgeInsets.all(AppSpace.s16),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(AppRadii.lg),
              border: Border.all(color: cs.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('$bgName 위', style: muted(AppTextStyles.caption)),
                const SizedBox(height: AppSpace.s8),
                for (final (String fgName, Color fg) in <(String, Color)>[
                  ('foreground', cs.foreground),
                  ('mutedForeground', cs.mutedForeground),
                  ('primary (링크)', cs.primary),
                ])
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpace.s8),
                    child: Text(
                      '$fgName · 하루 목표 2,085 kcal · '
                      '${AppContrast.ratio(fg, bg).toStringAsFixed(2)}:1 '
                      '${AppContrast.grade(AppContrast.ratio(fg, bg))}',
                      style: AppTextStyles.body.copyWith(color: fg),
                    ),
                  ),
              ],
            ),
          ),
      ],
    ),
    PreviewSection(
      title: 'Border · Input · Ring',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              TokenLabel(name: 'border (장식선)', color: cs.border),
              const SizedBox(height: AppSpace.s8),
              Container(height: 1, color: cs.border),
              const SizedBox(height: AppSpace.s16),
              TokenLabel(
                name:
                    'input · card 대비 '
                    '${AppContrast.ratio(cs.input, cs.card).toStringAsFixed(2)}',
                color: cs.input,
              ),
              const SizedBox(height: AppSpace.s8),
              _outlinedBox(cs, cs.input, 1, '입력 칸 테두리 1px'),
              const SizedBox(height: AppSpace.s16),
              TokenLabel(name: 'ring (포커스 2px)', color: cs.ring),
              const SizedBox(height: AppSpace.s8),
              _outlinedBox(cs, cs.ring, 2, '포커스 상태'),
            ],
          ),
        ),
      ],
    ),
    PreviewSection(
      title: 'Status',
      description: '상태는 아이콘과 문구를 함께 쓴다(§13)',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              for (final _Status s in _statuses(cs)) ...<Widget>[
                ColorChipRow(
                  name: s.name,
                  color: s.fg,
                  against: cs.card,
                ),
                ColorChipRow(name: '${s.name}Muted', color: s.bg),
                Container(
                  margin: const EdgeInsets.only(bottom: AppSpace.s12),
                  padding: const EdgeInsets.all(AppSpace.s12),
                  decoration: BoxDecoration(
                    color: s.bg,
                    borderRadius: BorderRadius.circular(AppRadii.md),
                  ),
                  child: Row(
                    children: <Widget>[
                      Icon(s.icon, size: 20, color: s.fg),
                      const SizedBox(width: AppSpace.s8),
                      Expanded(
                        child: Text(
                          s.message,
                          style: AppTextStyles.bodySmall.copyWith(color: s.fg),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        Wrap(
          spacing: AppSpace.s8,
          runSpacing: AppSpace.s8,
          children: <Widget>[
            for (final _Status s in _statuses(cs))
              statusBadge(s.fg, s.bg, s.icon, s.label),
          ],
        ),
        ShadAlert(
          icon: const Icon(LucideIcons.circleCheck),
          iconColor: cs.success,
          title: const Text('저장했습니다'),
          description: const Text('오늘 식단 기록이 반영되었습니다.'),
          titleStyle: AppTextStyles.bodyStrong.copyWith(color: cs.success),
          decoration: _alertDecoration(cs.successMuted, cs.success),
        ),
        ShadAlert(
          icon: const Icon(LucideIcons.triangleAlert),
          iconColor: cs.warning,
          title: const Text('AI 일일 한도 임박'),
          description: const Text('오늘 남은 AI 요청은 2회입니다.'),
          titleStyle: AppTextStyles.bodyStrong.copyWith(color: cs.warning),
          decoration: _alertDecoration(cs.warningMuted, cs.warning),
        ),
        ShadAlert.destructive(
          icon: const Icon(LucideIcons.circleX),
          title: const Text('분석에 실패했습니다'),
          description: const Text('네트워크를 확인하고 다시 시도하세요.'),
          decoration: _alertDecoration(cs.errorMuted, cs.error),
        ),
        ShadAlert(
          icon: const Icon(LucideIcons.info),
          iconColor: cs.info,
          title: const Text('출처 안내'),
          description: const Text('AI 답변은 검증된 자료만 출처로 보입니다.'),
          titleStyle: AppTextStyles.bodyStrong.copyWith(color: cs.info),
          decoration: _alertDecoration(cs.infoMuted, cs.info),
        ),
      ],
    ),
  ];
}

/// 상태 배지: 아이콘 16 + caption.
Widget statusBadge(Color fg, Color bg, IconData icon, String label) {
  return ShadBadge(
    backgroundColor: bg,
    hoverBackgroundColor: bg,
    foregroundColor: fg,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(icon, size: 16, color: fg),
        const SizedBox(width: AppSpace.s4),
        Text(label, style: AppTextStyles.caption.copyWith(color: fg)),
      ],
    ),
  );
}

ShadDecoration _alertDecoration(Color bg, Color line) {
  return ShadDecoration(
    color: bg,
    border: ShadBorder.all(
      color: line,
      width: 1,
      radius: const BorderRadius.all(Radius.circular(AppRadii.md)),
      padding: const EdgeInsets.all(AppSpace.s16),
    ),
  );
}

Widget _outlinedBox(ShadColorScheme cs, Color line, double width, String text) {
  return Container(
    height: 48,
    alignment: Alignment.centerLeft,
    padding: const EdgeInsets.symmetric(horizontal: AppSpace.s12),
    decoration: BoxDecoration(
      color: cs.card,
      borderRadius: BorderRadius.circular(AppRadii.md),
      border: Border.all(color: line, width: width),
    ),
    child: Text(text, style: AppTextStyles.body.copyWith(color: cs.foreground)),
  );
}

class _Status {
  const _Status(
    this.name,
    this.fg,
    this.bg,
    this.icon,
    this.label,
    this.message,
  );
  final String name;
  final Color fg;
  final Color bg;
  final IconData icon;
  final String label;
  final String message;
}

List<_Status> _statuses(ShadColorScheme cs) => <_Status>[
  _Status(
    'success',
    cs.success,
    cs.successMuted,
    LucideIcons.circleCheck,
    '목표 달성',
    '저장 완료 · 목표 달성',
  ),
  _Status(
    'warning',
    cs.warning,
    cs.warningMuted,
    LucideIcons.triangleAlert,
    '320kcal 초과',
    '목표보다 320kcal 초과했습니다',
  ),
  _Status(
    'error',
    cs.error,
    cs.errorMuted,
    LucideIcons.circleX,
    '분석 실패',
    '저장에 실패했습니다',
  ),
  _Status(
    'info',
    cs.info,
    cs.infoMuted,
    LucideIcons.info,
    '새 기능',
    '출처는 검증된 자료만 보입니다',
  ),
];
