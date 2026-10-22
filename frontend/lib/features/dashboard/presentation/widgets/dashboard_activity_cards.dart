// 홈 활동 카드: 오늘 운동 기록, 주간 일관성 (docs/DESIGN_SYSTEM.md §17 5~6).
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../../core/design_system/app_text_styles.dart';
import '../../../../core/design_system/app_tokens.dart';
import '../../../../shared/design_system/design_system.dart';
import '../dashboard_view_data.dart';

/// 오늘 운동 기록. 장식 사진은 두지 않는다(§19-3).
class TodayExerciseCard extends StatelessWidget {
  const TodayExerciseCard({
    super.key,
    required this.data,
    required this.onOpen,
  });

  final DashboardViewData data;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final String? title = data.todayExerciseTitle;
    if (title == null) {
      return AppCard(
        title: '오늘 운동 기록',
        trailing: AppCardAction(label: '기록하기', onPressed: onOpen),
        children: <Widget>[
          Text(
            '오늘 운동 기록이 없습니다',
            style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
          ),
        ],
      );
    }
    return AppCard(
      title: '오늘 운동 기록',
      trailing: AppCardAction(label: '보기', onPressed: onOpen),
      children: <Widget>[
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title,
              style: AppTextStyles.bodyStrong.copyWith(
                color: cs.cardForeground,
              ),
            ),
            if (data.todayExerciseDetail != null) ...<Widget>[
              const SizedBox(height: AppSpace.s4),
              Text(
                data.todayExerciseDetail!,
                style: AppTextStyles.bodySmall.copyWith(
                  color: cs.mutedForeground,
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

/// 주간 일관성: 요일별 점 2개 + 범례.
class WeeklyConsistencyCard extends StatelessWidget {
  const WeeklyConsistencyCard({super.key, required this.data});

  final DashboardViewData data;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return AppCard(
      title: '주간 일관성',
      children: <Widget>[
        if (data.week.isEmpty)
          Text(
            '이번 주 기록이 없습니다',
            style: AppTextStyles.body.copyWith(color: cs.mutedForeground),
          )
        else
          WeekConsistency(days: data.week),
      ],
    );
  }
}
