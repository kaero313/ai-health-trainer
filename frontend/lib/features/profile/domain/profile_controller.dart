import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/profile_repository.dart';

class ProfileController extends AsyncNotifier<Map<String, dynamic>> {
  @override
  Future<Map<String, dynamic>> build() {
    return ref.read(profileRepositoryProvider).getProfile();
  }

  Future<void> updateProfile(Map<String, dynamic> payload) async {
    state = const AsyncLoading();

    try {
      final Map<String, dynamic> updated = await ref
          .read(profileRepositoryProvider)
          .updateProfile(payload);
      state = AsyncData(updated);
    } catch (e, st) {
      state = AsyncError(e, st);
      rethrow;
    }
  }
}

final profileControllerProvider =
    AsyncNotifierProvider<ProfileController, Map<String, dynamic>>(
      ProfileController.new,
    );
