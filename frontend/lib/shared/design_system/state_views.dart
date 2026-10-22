// 화면 상태 표현 (docs/DESIGN_SYSTEM.md §13-2): 빈 상태, 오류, 첫 로딩 스켈레톤.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_motion.dart';
import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

/// 가운데 정렬 아이콘 24 + heading + bodySmall + Outline 버튼 1개.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.description,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  });

  final IconData icon;
  final String title;
  final String? description;
  final String? actionLabel;
  final VoidCallback? onAction;

  /// 카드 한 칸 안에 넣는 축소형. 위아래 여백 32 대신 8을 쓴다.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    // 기본형은 카드 안쪽 여백 16과 합쳐 위아래 48(§5 s48 "빈 상태 위아래")이 되게 32를 쓴다.
    final double vertical = compact ? AppSpace.s8 : AppSpace.s32;
    return Padding(
      padding: EdgeInsets.symmetric(vertical: vertical),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: <Widget>[
          Icon(icon, size: 24, color: cs.mutedForeground),
          const SizedBox(height: AppSpace.s12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: AppTextStyles.heading.copyWith(color: cs.cardForeground),
          ),
          if (description != null) ...<Widget>[
            const SizedBox(height: AppSpace.s4),
            Text(
              description!,
              textAlign: TextAlign.center,
              style: AppTextStyles.bodySmall.copyWith(
                color: cs.mutedForeground,
              ),
            ),
          ],
          if (actionLabel != null) ...<Widget>[
            const SizedBox(height: AppSpace.s16),
            ShadButton.outline(
              size: compact ? ShadButtonSize.sm : null,
              textStyle: compact ? AppTextStyles.buttonCompact : null,
              onPressed: onAction,
              child: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }
}

/// error 색 ShadAlert(아이콘 + 제목 + 설명) + Outline "다시 시도".
class ErrorState extends StatelessWidget {
  const ErrorState({
    super.key,
    required this.title,
    this.description,
    this.retryLabel = '다시 시도',
    this.onRetry,
  });

  final String title;
  final String? description;
  final String retryLabel;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Semantics(
          liveRegion: true,
          child: ShadAlert.destructive(
            icon: const Icon(LucideIcons.circleX),
            iconSize: 20,
            title: Text(title),
            description: description == null ? null : Text(description!),
          ),
        ),
        const SizedBox(height: AppSpace.s12),
        ShadButton.outline(
          width: double.infinity,
          onPressed: onRetry,
          leading: const Icon(LucideIcons.rotateCw, size: 18),
          child: Text(retryLabel),
        ),
      ],
    );
  }
}

/// 카드 모양 스켈레톤: muted 면, 반경 16, 투명도 펄스 1.2s.
/// 반짝이며 지나가는 효과는 쓰지 않고, 애니메이션 끄기 설정이면 멈춘다.
class SkeletonBlock extends StatefulWidget {
  const SkeletonBlock({
    super.key,
    required this.height,
    this.width = double.infinity,
    this.radius = AppRadii.lg,
  });

  final double height;
  final double width;
  final double radius;

  @override
  State<SkeletonBlock> createState() => _SkeletonBlockState();
}

class _SkeletonBlockState extends State<SkeletonBlock>
    with SingleTickerProviderStateMixin {
  // 한 방향이 주기의 절반이다(밝기 → 옅음 → 밝기 = 1.2s).
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: AppMotion.skeletonPulse ~/ 2,
    value: 1,
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller
        ..stop()
        ..value = 1;
    } else if (!_controller.isAnimating) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    final Animation<double> opacity = Tween<double>(
      begin: AppMotion.skeletonMinOpacity,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: AppMotion.standard));
    return Semantics(
      label: '불러오는 중',
      child: FadeTransition(
        opacity: opacity,
        child: Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            color: cs.muted,
            borderRadius: BorderRadius.circular(widget.radius),
          ),
        ),
      ),
    );
  }
}
