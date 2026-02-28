import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/secure_storage_service.dart';

enum AppAuthState {
  loading,
  authenticated,
  unauthenticated,
}

class AuthStateNotifier extends AsyncNotifier<AppAuthState> {
  @override
  Future<AppAuthState> build() async {
    final String? token = await ref.read(secureStorageServiceProvider).getAccessToken();
    if (token != null && token.isNotEmpty) {
      return AppAuthState.authenticated;
    }
    return AppAuthState.unauthenticated;
  }

  Future<void> logout() async {
    await ref.read(secureStorageServiceProvider).clearTokens();
    state = const AsyncData(AppAuthState.unauthenticated);
  }
}

final authStateProvider = AsyncNotifierProvider<AuthStateNotifier, AppAuthState>(
  AuthStateNotifier.new,
);
