import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/secure_storage_service.dart';
import 'package:frontend/features/auth/data/auth_repository.dart';
import 'package:frontend/features/auth/domain/auth_controller.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:frontend/features/profile/domain/profile_check_provider.dart';

void main() {
  test(
    'login invalidates a profile check cached before authentication',
    () async {
      final _FakeAuthRepository authRepository = _FakeAuthRepository();
      final _FakeSecureStorage storage = _FakeSecureStorage();
      final _SwitchableProfileRepository profileRepository =
          _SwitchableProfileRepository();
      final ProviderContainer container = ProviderContainer(
        overrides: <Override>[
          authRepositoryProvider.overrideWithValue(authRepository),
          secureStorageServiceProvider.overrideWithValue(storage),
          profileRepositoryProvider.overrideWithValue(profileRepository),
        ],
      );
      addTearDown(container.dispose);

      expect(await container.read(profileCheckProvider.future), isFalse);
      profileRepository.hasProfile = true;

      await container
          .read(authControllerProvider.notifier)
          .login('ui-e2e@example.com', 'password');

      expect(await container.read(profileCheckProvider.future), isTrue);
      expect(storage.accessToken, 'access-token');
    },
  );
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository() : super(dio: Dio());

  @override
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    return <String, dynamic>{
      'access_token': 'access-token',
      'refresh_token': 'refresh-token',
    };
  }
}

class _FakeSecureStorage extends SecureStorageService {
  String? accessToken;
  String? refreshToken;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<String?> getRefreshToken() async => refreshToken;

  @override
  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    accessToken = access;
    refreshToken = refresh;
  }
}

class _SwitchableProfileRepository extends ProfileRepository {
  bool hasProfile = false;

  _SwitchableProfileRepository() : super(dio: Dio());

  @override
  Future<bool> checkProfile() async => hasProfile;
}
