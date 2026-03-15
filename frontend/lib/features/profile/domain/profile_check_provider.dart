import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/profile_repository.dart';

/// 프로필 존재 여부를 비동기적으로 확인하는 Provider
/// 라우터 redirect에서 사용
final profileCheckProvider = FutureProvider<bool>((ref) async {
  final ProfileRepository repo = ref.read(profileRepositoryProvider);
  return repo.checkProfile();
});
