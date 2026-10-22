// 탭·상세 화면 뼈대 (docs/DESIGN_SYSTEM.md §5, §11-1, §13-2, §16).
// background 바탕, 상단 SafeArea, 세로 스크롤(좌우 20), 선택적 당겨서 새로고침과 하단 탭.
import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../../core/design_system/app_text_styles.dart';
import '../../core/design_system/app_tokens.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.child,
    this.bottomNav,
    this.onRefresh,
    this.scrollKey,
    this.scrollController,
  });

  /// 스크롤 영역 안의 내용. 좌우 20 여백은 AppScaffold가 준다.
  final Widget child;

  /// 화면 아래에 붙는 하단 탭(AppBottomNav). 없으면 상세 화면이다.
  final Widget? bottomNav;

  /// 지정하면 당겨서 새로고침을 켠다(Material RefreshIndicator, 색 primary).
  final RefreshCallback? onRefresh;

  final Key? scrollKey;
  final ScrollController? scrollController;

  @override
  Widget build(BuildContext context) {
    final ShadColorScheme cs = ShadTheme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.background,
      // 내용이 하단 탭 뒤까지 이어지게 둔다. 그러면 body의 MediaQuery 아래 padding이
      // "하단 탭 높이(64 + safe area)"가 되고, 끝 여백을 그 값 + 16으로 잡을 수 있다(§5).
      extendBody: bottomNav != null,
      bottomNavigationBar: bottomNav,
      body: DefaultTextStyle(
        style: AppTextStyles.body.copyWith(color: cs.foreground),
        child: SafeArea(
          bottom: false,
          // Scaffold가 body에 준 MediaQuery를 읽어야 하므로 body 안의 context를 쓴다.
          child: Builder(
            builder: (BuildContext bodyContext) => _scroll(bodyContext, cs),
          ),
        ),
      ),
    );
  }

  Widget _scroll(BuildContext context, ShadColorScheme cs) {
    // 하단 탭이 있으면 탭 높이 + safe area, 없으면 safe area만 들어 있다.
    final double bottomInset = MediaQuery.paddingOf(context).bottom;
    final Widget scroll = SingleChildScrollView(
      key: scrollKey,
      controller: scrollController,
      physics: onRefresh == null ? null : const AlwaysScrollableScrollPhysics(),
      padding: EdgeInsets.fromLTRB(
        AppSpace.s20,
        0,
        AppSpace.s20,
        bottomInset + AppSpace.s16,
      ),
      child: child,
    );
    if (onRefresh == null) return scroll;
    return RefreshIndicator(
      onRefresh: onRefresh!,
      color: cs.primary,
      backgroundColor: cs.card,
      child: scroll,
    );
  }
}
