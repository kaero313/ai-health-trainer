// AI 진입 카드 (docs/DESIGN_SYSTEM.md §9 Action 카드, §16, §19-8).
// 화면당 1개이고, 전체 폭 Primary 버튼이 그 화면의 유일한 Primary라는 전제다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';
import 'app_card.dart';

class AiCoachCard extends StatelessWidget {
  const AiCoachCard({
    super.key,
    required this.description,
    required this.buttonLabel,
    required this.onPressed,
    this.title = 'AI 코치',
    this.icon = LucideIcons.sparkles,
  });

  final String title;
  final String description;
  final String buttonLabel;
  final VoidCallback? onPressed;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return AppCard(
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            AppIconTile(icon: icon),
            const SizedBox(width: AppSpace.s12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Semantics(
                    header: true,
                    child: Text(
                      title,
                      style: AppTextStyles.heading.copyWith(
                        color: cs.cardForeground,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpace.s4),
                  Text(
                    description,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: cs.mutedForeground,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        ShadButton(
          width: double.infinity,
          onPressed: onPressed,
          child: Text(buttonLabel),
        ),
      ],
    );
  }
}
