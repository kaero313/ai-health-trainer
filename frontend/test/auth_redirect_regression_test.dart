// 로그인·토큰 만료 시 라우터 redirect 회귀 테스트.
// 실제 routerProvider·AuthInterceptor·ProfileRepository를 쓰고 HTTP만 가짜 어댑터로 바꾼다.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/auth_interceptor.dart';
import 'package:frontend/core/network/secure_storage_service.dart';
import 'package:frontend/core/router/app_router.dart';
import 'package:frontend/features/auth/domain/auth_controller.dart';
import 'package:frontend/features/auth/domain/auth_state_provider.dart';
import 'package:frontend/features/profile/domain/profile_check_provider.dart';
import 'package:frontend/main.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String _validAccess = 'valid-access';
const String _validRefresh = 'valid-refresh';

void main() {
  testWidgets('증상 1: 프로필이 있으면 로그인 직후 /profile/edit를 거치지 않고 /dashboard로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = true;
    final _MemoryStorage storage = _MemoryStorage();
    final _Harness app = await _pumpApp(tester, backend, storage);

    // 앱 시작 시 토큰 없이 /profile/check가 한 번 나간다(RouterNotifier가 구독).
    expect(app.path, '/login');
    expect(backend.requests, contains('/profile/check'));

    await app.loginLikeLoginScreen(tester);

    expect(app.path, '/dashboard');
    expect(app.visited, isNot(contains('/profile/edit')));

    await app.finish(tester);
  });

  testWidgets('증상 2: access 만료 + refresh 실패면 토큰을 지우고 /login으로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = true;
    final _MemoryStorage storage = _MemoryStorage()
      ..accessToken = 'expired-access'
      ..refreshToken = 'expired-refresh';
    final _Harness app = await _pumpApp(tester, backend, storage);

    expect(backend.requests, contains('/auth/refresh'));
    expect(app.path, '/login');
    expect(app.visited, isNot(contains('/profile/edit')));
    expect(storage.accessToken, isNull);
    expect(storage.refreshToken, isNull);
    expect(
      app.container.read(authStateProvider).valueOrNull,
      AppAuthState.unauthenticated,
    );

    await app.finish(tester);
  });

  testWidgets('access 만료 + refresh 성공이면 재시도 후 /dashboard에 머문다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()
      ..hasProfile = true
      ..refreshSucceeds = true;
    final _MemoryStorage storage = _MemoryStorage()
      ..accessToken = 'expired-access'
      ..refreshToken = _validRefresh;
    final _Harness app = await _pumpApp(tester, backend, storage);

    expect(app.path, '/dashboard');
    expect(app.visited, isNot(contains('/profile/edit')));
    expect(storage.accessToken, _validAccess);

    await app.finish(tester);
  });

  testWidgets('has_profile: false면 로그인 직후 /profile/edit로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = false;
    final _Harness app = await _pumpApp(tester, backend, _MemoryStorage());

    await app.loginLikeLoginScreen(tester);

    expect(app.path, '/profile/edit');

    await app.finish(tester);
  });

  testWidgets('회원가입 직후 프로필이 없으면 /profile/edit로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = false;
    final _Harness app = await _pumpApp(tester, backend, _MemoryStorage());

    // register_screen.dart와 같은 순서: register 완료 뒤 /dashboard로 이동.
    app.container
        .read(authControllerProvider.notifier)
        .register('new@example.com', 'password1', 'password1')
        .then((_) => app.router.go('/dashboard'));
    await _settle(tester);

    expect(app.path, '/profile/edit');

    await app.finish(tester);
  });

  testWidgets('첫 프로필 저장 직후 /dashboard로 간다', (WidgetTester tester) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = false;
    final _Harness app = await _pumpApp(tester, backend, _MemoryStorage());
    await app.loginLikeLoginScreen(tester);
    expect(app.path, '/profile/edit');

    // profile_edit_screen.dart의 저장 성공 흐름: invalidate 뒤 /dashboard로 이동.
    backend.hasProfile = true;
    app.container.invalidate(profileCheckProvider);
    app.router.go('/dashboard');
    await _settle(tester);

    expect(app.path, '/dashboard');

    await app.finish(tester);
  });

  testWidgets('/profile/check가 5xx면 /profile/edit로 보내지 않고 현재 화면에 머문다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..profileCheckStatus = 500;
    final _Harness app = await _pumpApp(tester, backend, _MemoryStorage());

    await app.loginLikeLoginScreen(tester);

    expect(app.path, '/dashboard');
    expect(app.visited, isNot(contains('/profile/edit')));
    expect(app.container.read(profileCheckProvider).hasError, isTrue);

    await app.finish(tester);
  });

  testWidgets('/profile/check가 네트워크 오류면 /profile/edit로 보내지 않는다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend()..profileCheckOffline = true;
    final _Harness app = await _pumpApp(tester, backend, _MemoryStorage());

    await app.loginLikeLoginScreen(tester);

    expect(app.path, '/dashboard');
    expect(app.visited, isNot(contains('/profile/edit')));
    expect(app.container.read(profileCheckProvider).hasError, isTrue);

    await app.finish(tester);
  });

  testWidgets('로그아웃하면 토큰을 지우고 /login으로 간다', (WidgetTester tester) async {
    final _FakeBackend backend = _FakeBackend()..hasProfile = true;
    final _MemoryStorage storage = _MemoryStorage()
      ..accessToken = _validAccess
      ..refreshToken = _validRefresh;
    final _Harness app = await _pumpApp(tester, backend, storage);
    expect(app.path, '/dashboard');

    app.container.read(authStateProvider.notifier).logout();
    await _settle(tester);

    expect(app.path, '/login');
    expect(storage.accessToken, isNull);

    await app.finish(tester);
  });

  group('갱신 중 세션이 바뀌면 이전 갱신 결과로 저장소를 건드리지 않는다', () {
    test('이전 refresh가 새 로그인 뒤 성공해도 새 토큰을 덮어쓰지 않고, 새 요청은 새 refresh로 갱신한다', () async {
      final _SessionBackend backend = _SessionBackend();
      final _MemoryStorage storage = _MemoryStorage()
        ..accessToken = 'old-access'
        ..refreshToken = 'old-refresh';
      final Dio dio = _sessionDio(backend, storage);

      // 이전 세션 요청: 401 → old-refresh로 갱신 시작(붙잡힘).
      final Future<Response<dynamic>> oldRequest = dio.get<dynamic>('/whoami');
      await backend.oldRefreshArrived.future;

      // 새 로그인. 서버가 새 access를 거절해 새 요청도 401을 받는 경우.
      await storage.saveTokens(access: 'new-access', refresh: 'new-refresh');
      final Future<Response<dynamic>> newRequest = dio.get<dynamic>('/whoami');
      // 새 요청이 401을 받아 갱신 단계에 들어갈 때까지 진행한 뒤 이전 갱신을 끝낸다.
      await Future<void>.delayed(const Duration(milliseconds: 50));
      backend.releaseOldRefresh(succeed: true);

      final Response<dynamic> newResponse = await newRequest;
      expect(newResponse.data['auth'], 'Bearer new-session-access');
      await expectLater(oldRequest, throwsA(isA<DioException>()));
      expect(storage.accessToken, 'new-session-access');
      expect(storage.refreshToken, 'new-refresh');
    });

    test('이전 refresh가 새 로그인 뒤 실패해도 새 토큰을 지우지 않는다', () async {
      final _SessionBackend backend = _SessionBackend();
      final _MemoryStorage storage = _MemoryStorage()
        ..accessToken = 'old-access'
        ..refreshToken = 'old-refresh';
      final Dio dio = _sessionDio(backend, storage);

      final Future<Response<dynamic>> oldRequest = dio.get<dynamic>('/whoami');
      await backend.oldRefreshArrived.future;

      await storage.saveTokens(
        access: 'new-session-access',
        refresh: 'new-refresh',
      );

      backend.releaseOldRefresh(succeed: false);
      await expectLater(oldRequest, throwsA(isA<DioException>()));

      expect(storage.accessToken, 'new-session-access');
      expect(storage.refreshToken, 'new-refresh');
    });
  });
}

Dio _sessionDio(_SessionBackend backend, _MemoryStorage storage) {
  final Dio dio = Dio(BaseOptions(baseUrl: 'http://fake.test/api/v1'));
  dio.httpClientAdapter = backend;
  dio.interceptors.add(AuthInterceptor(storage: storage, dio: dio));
  return dio;
}

/// 세션 전환 경쟁용 HTTP 대역. old-refresh 갱신만 붙잡아 두고 나머지는 바로 답한다.
class _SessionBackend implements HttpClientAdapter {
  final Completer<void> oldRefreshArrived = Completer<void>();
  final Completer<bool> _oldRefreshResult = Completer<bool>();

  void releaseOldRefresh({required bool succeed}) {
    _oldRefreshResult.complete(succeed);
  }

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path == '/auth/refresh') {
      final Object? data = options.data;
      final Object? refresh = data is Map ? data['refresh_token'] : null;
      if (refresh == 'old-refresh') {
        oldRefreshArrived.complete();
        if (!await _oldRefreshResult.future) {
          return _sessionJson(401, <String, dynamic>{'detail': 'expired'});
        }
        return _refreshed('old-session-access');
      }
      if (refresh == 'new-refresh') {
        return _refreshed('new-session-access');
      }
      return _sessionJson(401, <String, dynamic>{'detail': 'expired'});
    }
    final Object? auth = options.headers['Authorization'];
    if (auth == 'Bearer old-session-access' ||
        auth == 'Bearer new-session-access') {
      return _sessionJson(200, <String, dynamic>{'auth': auth});
    }
    return _sessionJson(401, <String, dynamic>{'detail': 'Not authenticated'});
  }

  ResponseBody _refreshed(String access) {
    return _sessionJson(200, <String, dynamic>{
      'status': 'success',
      'data': <String, dynamic>{'access_token': access},
    });
  }

  ResponseBody _sessionJson(int status, Map<String, dynamic> body) {
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>[Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

class _Harness {
  final ProviderContainer container;
  final GoRouter router;
  final List<String> visited;

  _Harness(this.container, this.router, this.visited);

  String get path => router.routerDelegate.currentConfiguration.uri.path;

  /// 위젯 트리를 내리고 진행 중인 가짜 요청 타이머를 비운다.
  Future<void> finish(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(seconds: 1));
  }

  /// login_screen.dart와 같은 순서: login 완료 직후 /dashboard로 이동.
  Future<void> loginLikeLoginScreen(WidgetTester tester) async {
    container
        .read(authControllerProvider.notifier)
        .login('user@example.com', 'password1')
        .then((_) => router.go('/dashboard'));
    await _settle(tester);
  }
}

Future<_Harness> _pumpApp(
  WidgetTester tester,
  _FakeBackend backend,
  _MemoryStorage storage,
) async {
  SharedPreferences.setMockInitialValues(<String, Object>{
    'onboarding_done': true,
  });
  final ProviderContainer container = ProviderContainer(
    overrides: <Override>[
      secureStorageServiceProvider.overrideWithValue(storage),
      dioProvider.overrideWith((Ref ref) {
        final Dio dio = Dio(BaseOptions(baseUrl: 'http://fake.test/api/v1'));
        dio.httpClientAdapter = backend;
        dio.interceptors.add(AuthInterceptor(storage: storage, dio: dio));
        return dio;
      }),
    ],
  );
  addTearDown(container.dispose);

  final GoRouter router = container.read(routerProvider);
  final List<String> visited = <String>[];
  router.routerDelegate.addListener(() {
    visited.add(router.routerDelegate.currentConfiguration.uri.path);
  });

  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const MyApp()),
  );
  // 스플래시 1.5초 대기와 시작 시 요청이 끝날 때까지 진행한다.
  await tester.pump(const Duration(milliseconds: 1500));
  await _settle(tester);
  return _Harness(container, router, visited);
}

/// 로딩 애니메이션 때문에 pumpAndSettle 대신 고정 횟수만큼 진행한다.
Future<void> _settle(WidgetTester tester) async {
  for (int i = 0; i < 30; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

class _MemoryStorage extends SecureStorageService {
  String? accessToken;
  String? refreshToken;

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<String?> getRefreshToken() async => refreshToken;

  @override
  Future<void> saveAccessToken(String token) async {
    accessToken = token;
  }

  @override
  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    accessToken = access;
    refreshToken = refresh;
  }

  @override
  Future<void> clearTokens() async {
    accessToken = null;
    refreshToken = null;
  }
}

/// 백엔드 계약을 흉내 내는 HTTP 대역. 실제 네트워크는 쓰지 않는다.
class _FakeBackend implements HttpClientAdapter {
  bool hasProfile = true;
  bool refreshSucceeds = false;
  int profileCheckStatus = 200;
  bool profileCheckOffline = false;
  final List<String> requests = <String>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    // 응답 지연: 로그인 직후 다시 계산되는 도중의 상태가 redirect에 보이게 한다.
    await Future<void>.delayed(const Duration(milliseconds: 100));
    final String path = options.path;
    requests.add(path);
    final Object? auth = options.headers['Authorization'];
    final bool authorized = auth == 'Bearer $_validAccess';

    switch (path) {
      case '/auth/login':
      case '/auth/register':
        return _json(200, <String, dynamic>{
          'status': 'success',
          'data': <String, dynamic>{
            'access_token': _validAccess,
            'refresh_token': _validRefresh,
          },
        });
      case '/auth/refresh':
        if (!refreshSucceeds) {
          return _unauthorized(auth);
        }
        return _json(200, <String, dynamic>{
          'status': 'success',
          'data': <String, dynamic>{'access_token': _validAccess},
        });
      case '/profile/check':
        if (!authorized) {
          return _unauthorized(auth);
        }
        if (profileCheckOffline) {
          throw DioException.connectionError(
            requestOptions: options,
            reason: 'offline',
          );
        }
        if (profileCheckStatus != 200) {
          return _json(profileCheckStatus, <String, dynamic>{
            'detail': <String, dynamic>{
              'code': 'INTERNAL_ERROR',
              'message': '서버 오류',
            },
          });
        }
        return _json(200, <String, dynamic>{'has_profile': hasProfile});
      default:
        if (!authorized) {
          return _unauthorized(auth);
        }
        return _json(404, <String, dynamic>{
          'detail': <String, dynamic>{'code': 'NOT_FOUND', 'message': '없음'},
        });
    }
  }

  ResponseBody _unauthorized(Object? auth) {
    // 헤더가 없으면 FastAPI OAuth2PasswordBearer 기본 응답과 같다.
    if (auth == null) {
      return _json(401, <String, dynamic>{'detail': 'Not authenticated'});
    }
    return _json(401, <String, dynamic>{
      'detail': <String, dynamic>{
        'code': 'UNAUTHORIZED',
        'message': 'Invalid or expired access token',
      },
    });
  }

  ResponseBody _json(int status, Map<String, dynamic> body) {
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>[Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
