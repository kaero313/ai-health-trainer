import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/secure_storage_service.dart';
import '../data/auth_repository.dart';
import 'auth_state_provider.dart';

class AuthController extends AsyncNotifier<void> {
  @override
  FutureOr<void> build() {}

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();

    try {
      final Map<String, dynamic> tokens = await ref.read(authRepositoryProvider).login(
            email: email,
            password: password,
          );
      await ref.read(secureStorageServiceProvider).saveTokens(
            access: tokens['access_token'] as String,
            refresh: tokens['refresh_token'] as String,
          );
      ref.invalidate(authStateProvider);
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }

  Future<void> register(
    String email,
    String password,
    String passwordConfirm,
  ) async {
    state = const AsyncLoading();

    try {
      final Map<String, dynamic> tokens = await ref.read(authRepositoryProvider).register(
            email: email,
            password: password,
            passwordConfirm: passwordConfirm,
          );
      await ref.read(secureStorageServiceProvider).saveTokens(
            access: tokens['access_token'] as String,
            refresh: tokens['refresh_token'] as String,
          );
      ref.invalidate(authStateProvider);
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, void>(
  AuthController.new,
);
