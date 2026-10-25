// Theme Preview 공용 위젯. 색은 모두 ShadTheme 토큰에서 읽는다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

/// 섹션: 위 24, 제목(heading) + 설명(bodySmall) + 본문(카드 사이 12).
class PreviewSection extends StatelessWidget {
  const PreviewSection({
    super.key,
    required this.title,
    this.description,
    required this.children,
  });

  final String title;
  final String? description;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpace.s24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            title,
            style: AppTextStyles.heading.copyWith(color: cs.foreground),
          ),
          if (description != null) ...<Widget>[
            const SizedBox(height: AppSpace.s4),
            Text(
              description!,
              style: AppTextStyles.bodySmall.copyWith(
                color: cs.mutedForeground,
              ),
            ),
          ],
          const SizedBox(height: AppSpace.s12),
          for (int i = 0; i < children.length; i++) ...<Widget>[
            if (i > 0) const SizedBox(height: AppSpace.s12),
            children[i],
          ],
        ],
      ),
    );
  }
}

/// 카드 한 장(§9: card 면, 1px border, 반경 16, 안쪽 16, 그림자 없음은 테마가 준다).
class PreviewCard extends StatelessWidget {
  const PreviewCard({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return ShadCard(width: double.infinity, padding: padding, child: child);
  }
}

/// 토큰 이름 + hex 한 줄.
class TokenLabel extends StatelessWidget {
  const TokenLabel({
    super.key,
    required this.name,
    required this.color,
    this.textColor,
  });

  final String name;
  final Color color;
  final Color? textColor;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Color effective = textColor ?? cs.mutedForeground;
    return Wrap(
      spacing: AppSpace.s8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: <Widget>[
        Text(name, style: AppTextStyles.caption.copyWith(color: effective)),
        Text(
          AppContrast.hex(color),
          style: AppTextStyles.numSmall.copyWith(color: effective),
        ),
      ],
    );
  }
}

/// 면 견본: [surface] 위에 [onSurface] 글자 샘플과 토큰 이름을 보인다.
class SurfaceSwatch extends StatelessWidget {
  const SurfaceSwatch({
    super.key,
    required this.name,
    required this.surface,
    required this.onSurfaceName,
    required this.onSurface,
    this.sample = '오늘의 진행 1,185 kcal',
  });

  final String name;
  final Color surface;
  final String onSurfaceName;
  final Color onSurface;
  final String sample;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final double ratio = AppContrast.ratio(onSurface, surface);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.s16),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(AppRadii.lg),
        border: Border.all(color: cs.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          TokenLabel(name: name, color: surface, textColor: onSurface),
          const SizedBox(height: AppSpace.s8),
          Text(sample, style: AppTextStyles.body.copyWith(color: onSurface)),
          const SizedBox(height: AppSpace.s4),
          Text(
            '$onSurfaceName ${AppContrast.hex(onSurface)} · '
            '${ratio.toStringAsFixed(2)}:1 ${AppContrast.grade(ratio)}',
            style: AppTextStyles.caption.copyWith(color: onSurface),
          ),
        ],
      ),
    );
  }
}

/// 작은 색 칩 + 이름 + hex (+ 선택: 기준 면 대비).
class ColorChipRow extends StatelessWidget {
  const ColorChipRow({
    super.key,
    required this.name,
    required this.color,
    this.against,
    this.againstName,
  });

  final String name;
  final Color color;
  final Color? against;
  final String? againstName;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final double? ratio = against == null
        ? null
        : AppContrast.ratio(color, against!);
    return SizedBox(
      height: 40,
      child: Row(
        children: <Widget>[
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(AppRadii.sm),
              border: Border.all(color: cs.border),
            ),
          ),
          const SizedBox(width: AppSpace.s12),
          Expanded(
            child: Text(
              name,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.bodySmall.copyWith(color: cs.foreground),
            ),
          ),
          Text(
            ratio == null
                ? AppContrast.hex(color)
                : '${AppContrast.hex(color)}  ${ratio.toStringAsFixed(2)}',
            style: AppTextStyles.numSmall.copyWith(color: cs.mutedForeground),
          ),
        ],
      ),
    );
  }
}

/// 범례 점 + caption.
class LegendDot extends StatelessWidget {
  const LegendDot({super.key, required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: AppSpace.s4),
        Text(
          label,
          style: AppTextStyles.caption.copyWith(color: cs.foreground),
        ),
      ],
    );
  }
}
