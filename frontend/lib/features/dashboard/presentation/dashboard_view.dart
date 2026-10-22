// 홈 화면 본문(docs/DESIGN_SYSTEM.md §17). 데이터 연결 없이 상태·값·동작만 받아
// 실제 화면(DashboardScreen)과 내부 목업(lib/dev/mockups/)이 같은 화면을 그린다.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../../core/design_system/app_tokens.dart';
import '../../../shared/design_system/design_system.dart';
import 'dashboard_view_data.dart';
import 'widgets/dashboard_activity_cards.dart';
import 'widgets/dashboard_summary_cards.dart';

enum DashboardStatus { loading, profileRequired, error, ready }

class DashboardView extends StatelessWidget {
  const DashboardView({
    super.key,
    required this.status,
    required this.subtitle,
    this.data,
    this.errorMessage,
    this.bottomNav,
    this.onRefresh,
    required this.onSetupProfile,
    required this.onRetry,
    required this.onOpenDiet,
    required this.onOpenExercise,
    required this.onOpenCoach,
    required this.onOpenMonthly,
  }) : assert(status != DashboardStatus.ready || data != null);

  static const String greeting = '좋은 하루예요';
  static const String defaultErrorMessage = '네트워크를 확인하고 다시 시도하세요.';
  static const Key scrollKey = ValueKey<String>('dashboard-scroll');

  /// 스크롤 끝 확인용: 마지막 블록(월간 리포트·빈 상태·오류·마지막 스켈레톤)에 붙인다.
  static const Key lastBlockKey = ValueKey<String>('dashboard-last');

  /// 첫 로딩 스켈레톤 높이. 각 카드의 대략 높이(폭 390)에 맞췄다.
  static const List<double> skeletonHeights = <double>[232, 296, 216, 104, 128];

  final DashboardStatus status;

  /// 헤더 부제. 목표는 profile을 받았을 때만 붙인다(§21-2).
  final String subtitle;

  /// [DashboardStatus.ready]일 때 필수.
  final DashboardViewData? data;
  final String? errorMessage;

  /// 하단 탭. 실제 앱은 셸(MainShell)이 그리므로 null이다.
  final Widget? bottomNav;

  /// ready 상태에서만 당겨서 새로고침을 켠다.
  final RefreshCallback? onRefresh;
  final VoidCallback onSetupProfile;
  final VoidCallback onRetry;
  final VoidCallback onOpenDiet;
  final VoidCallback onOpenExercise;
  final VoidCallback onOpenCoach;
  final VoidCallback onOpenMonthly;

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      scrollKey: scrollKey,
      onRefresh: status == DashboardStatus.ready ? onRefresh : null,
      bottomNav: bottomNav,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          AppHeader.root(title: greeting, subtitle: subtitle),
          // 헤더 블록과 첫 카드 사이 24, 카드 사이 12
          const SizedBox(height: AppSpace.s24),
          ..._spaced(_body()),
        ],
      ),
    );
  }

  List<Widget> _spaced(List<Widget> cards) => <Widget>[
    for (int i = 0; i < cards.length; i++) ...<Widget>[
      if (i > 0) const SizedBox(height: AppSpace.s12),
      cards[i],
    ],
  ];

  List<Widget> _body() {
    switch (status) {
      case DashboardStatus.loading:
        return <Widget>[
          for (int i = 0; i < skeletonHeights.length; i++)
            SkeletonBlock(
              key: i == skeletonHeights.length - 1 ? lastBlockKey : null,
              height: skeletonHeights[i],
            ),
        ];
      case DashboardStatus.profileRequired:
        return <Widget>[
          AppCard(
            key: lastBlockKey,
            children: <Widget>[
              EmptyState(
                icon: LucideIcons.userRound,
                title: '프로필 설정이 필요합니다',
                description: '목표를 정하면 하루 목표 열량을 계산합니다.',
                actionLabel: '프로필 설정',
                onAction: onSetupProfile,
              ),
            ],
          ),
        ];
      case DashboardStatus.error:
        return <Widget>[
          ErrorState(
            key: lastBlockKey,
            title: '대시보드를 불러오지 못했습니다',
            description: errorMessage ?? defaultErrorMessage,
            onRetry: onRetry,
          ),
        ];
      case DashboardStatus.ready:
        final DashboardViewData d = data!;
        return <Widget>[
          TodayProgressCard(data: d),
          WeightCard(data: d),
          NutritionCard(data: d, onOpen: onOpenDiet),
          TodayExerciseCard(data: d, onOpen: onOpenExercise),
          WeeklyConsistencyCard(data: d),
          // 이 화면의 유일한 Primary 버튼(§8, §17)
          AiCoachCard(
            description: '목표와 기록을 바탕으로 답변합니다',
            buttonLabel: 'AI 코치에게 질문',
            onPressed: onOpenCoach,
          ),
          NavRowCard(
            key: lastBlockKey,
            icon: LucideIcons.chartColumn,
            title: '월간 리포트',
            subtitle: '이번 달 기록 요약',
            onTap: onOpenMonthly,
          ),
        ];
    }
  }
}
