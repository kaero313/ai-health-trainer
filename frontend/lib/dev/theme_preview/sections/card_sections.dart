// Cards, Badges, Progress 섹션.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_shad_theme.dart';
import '../../../core/design_system/app_text_styles.dart';
import '../../../core/design_system/app_tokens.dart';
import '../widgets.dart';
import 'color_sections.dart' show statusBadge;

List<Widget> cardBadgeProgressSections(BuildContext context) {
  final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
  final TextStyle fg = AppTextStyles.body.copyWith(color: cs.foreground);
  final TextStyle mutedSmall = AppTextStyles.bodySmall.copyWith(
    color: cs.mutedForeground,
  );
  final TextStyle heading = AppTextStyles.heading.copyWith(
    color: cs.foreground,
  );

  Widget listRow(String label, String value, {bool empty = false}) {
    return SizedBox(
      height: 48,
      child: Row(
        children: <Widget>[
          Expanded(child: Text(label, style: fg)),
          Text(
            value,
            style: AppTextStyles.numSmall.copyWith(
              color: empty ? cs.mutedForeground : cs.foreground,
            ),
          ),
        ],
      ),
    );
  }

  Widget progressRow(String label, String value, double v, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                label,
                style: AppTextStyles.caption.copyWith(color: cs.foreground),
              ),
            ),
            Text(
              value,
              style: AppTextStyles.numSmall.copyWith(color: cs.foreground),
            ),
          ],
        ),
        const SizedBox(height: AppSpace.s8),
        ShadProgress(value: v, color: color),
      ],
    );
  }

  return <Widget>[
    PreviewSection(
      title: 'Cards',
      description: 'card 면 + 1px border, 반경 16, 그림자 없음(§9)',
      children: <Widget>[
        PreviewCard(
          padding: const EdgeInsets.all(AppSpace.s20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(child: Text('체중', style: heading)),
                  const ShadBadge.secondary(
                    child: Text('↓ 1.1kg', style: AppTextStyles.caption),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.s16),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: <Widget>[
                  Text(
                    '72.4',
                    style: AppTextStyles.numHero.copyWith(color: cs.foreground),
                  ),
                  const SizedBox(width: AppSpace.s4),
                  Text(
                    'kg',
                    style: AppTextStyles.body.copyWith(
                      color: cs.mutedForeground,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.s8),
              Text('지난주보다 1.1kg 줄었습니다 · 대표 카드 안쪽 20', style: mutedSmall),
            ],
          ),
        ),
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Text('활력 지표', style: heading),
              const SizedBox(height: AppSpace.s8),
              listRow('안정 심박', '62 bpm'),
              const ShadSeparator.horizontal(margin: EdgeInsets.zero),
              listRow('평균 수면', '7시간 12분'),
              const ShadSeparator.horizontal(margin: EdgeInsets.zero),
              listRow('걸음 수', '-- / 기록 없음', empty: true),
            ],
          ),
        ),
        ShadCard(
          width: double.infinity,
          padding: EdgeInsets.zero,
          child: Material(
            type: MaterialType.transparency,
            child: InkWell(
              onTap: () {},
              borderRadius: BorderRadius.circular(AppRadii.lg),
              highlightColor: cs.accent,
              child: Padding(
                padding: const EdgeInsets.all(AppSpace.s16),
                child: Row(
                  children: <Widget>[
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: cs.muted,
                        borderRadius: BorderRadius.circular(AppRadii.md),
                      ),
                      child: Icon(
                        LucideIcons.chartLine,
                        size: 20,
                        color: cs.foreground,
                      ),
                    ),
                    const SizedBox(width: AppSpace.s12),
                    Expanded(
                      child: Text(
                        '월간 리포트 보기',
                        style: AppTextStyles.bodyStrong.copyWith(
                          color: cs.foreground,
                        ),
                      ),
                    ),
                    Icon(
                      LucideIcons.chevronRight,
                      size: 20,
                      color: cs.mutedForeground,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    ),
    PreviewSection(
      title: 'Badges',
      description: 'caption, 반경 full. 상태 배지는 아이콘 + 문구',
      children: <Widget>[
        Wrap(
          spacing: AppSpace.s8,
          runSpacing: AppSpace.s8,
          children: <Widget>[
            const ShadBadge(child: Text('기본', style: AppTextStyles.caption)),
            const ShadBadge.secondary(
              child: Text('운동 1일 연속', style: AppTextStyles.caption),
            ),
            ShadBadge.outline(
              foregroundColor: cs.foreground,
              child: const Text('단백질', style: AppTextStyles.caption),
            ),
            statusBadge(
              cs.success,
              cs.successMuted,
              LucideIcons.circleCheck,
              '목표 달성',
            ),
            statusBadge(
              cs.warning,
              cs.warningMuted,
              LucideIcons.triangleAlert,
              '320kcal 초과',
            ),
            statusBadge(
              cs.error,
              cs.errorMuted,
              LucideIcons.circleX,
              '분석 실패',
            ),
            statusBadge(cs.info, cs.infoMuted, LucideIcons.info, '새 기능'),
          ],
        ),
      ],
    ),
    PreviewSection(
      title: 'Progress',
      description: '높이 6, 트랙 muted. 열량은 primary, 매크로는 대상 색',
      children: <Widget>[
        PreviewCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              progressRow('열량', '1,185 / 2,085 kcal', 0.57, cs.primary),
              const SizedBox(height: AppSpace.s16),
              progressRow('단백질', '69 / 120 g', 0.58, cs.chartProtein),
              const SizedBox(height: AppSpace.s16),
              progressRow('탄수화물', '165 / 260 g', 0.63, cs.chartCarbs),
              const SizedBox(height: AppSpace.s16),
              progressRow('지방', '26 / 58 g', 0.45, cs.chartFat),
            ],
          ),
        ),
      ],
    ),
  ];
}
