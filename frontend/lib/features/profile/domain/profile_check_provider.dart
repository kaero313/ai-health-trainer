import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/domain/auth_state_provider.dart';
import '../data/profile_repository.dart';

/// 프로필 존재 여부를 비동기적으로 확인하는 Provider
/// 라우터 redirect에서 사용
final profileCheckProvider = FutureProvider<bool>((ref) async {
  // 로그인 등으로 다시 계산된 뒤 끝난 이전 요청이 새 토큰을 지우지 않게 한다.
  bool superseded = false;
  ref.onDispose(() => superseded = true);

  final ProfileRepository repo = ref.read(profileRepositoryProvider);
  try {
    return await repo.checkProfile();
  } on ProfileRepositoryException catch (e) {
    // 401은 AuthInterceptor의 토큰 갱신까지 실패했다는 뜻이다. 세션을 끝내 /login으로 보낸다.
    if (e.statusCode == 401 && !superseded) {
      await ref.read(authStateProvider.notifier).logout();
    }
    rethrow;
  }
});
