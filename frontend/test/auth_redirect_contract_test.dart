// 인증·라우팅 계약 테스트(qa 독립 작성).
//
// 기준: 작업 지시의 계약 1~9와 docs/API_SPECIFICATION.md(/auth/*, /profile, /profile/check).
// 실제 MyApp·routerProvider·dioProvider 구성(AuthInterceptor 포함)을 그대로 쓰고,
// 네트워크는 가짜 HttpClientAdapter, 토큰 저장소는 메모리 대역으로만 바꾼다.
// 판정은 라우터 위치, 저장된 토큰, 화면으로만 한다(구현 내부 플래그에 기대지 않는다).
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/auth_interceptor.dart';
import 'package:frontend/core/network/secure_storage_service.dart';
import 'package:frontend/core/router/app_router.dart';
import 'package:frontend/features/auth/domain/auth_state_provider.dart';
import 'package:frontend/features/auth/presentation/login_screen.dart';
import 'package:frontend/features/auth/presentation/register_screen.dart';
import 'package:frontend/features/profile/presentation/profile_edit_screen.dart';
import 'package:frontend/main.dart';
import 'package:frontend/shared/widgets/neo_widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('계약 1: 토큰이 없으면 시작 후 /login으로 가고 /profile/edit에는 가지 않는다', (
    WidgetTester tester,
  ) async {
    final _Harness h = _Harness(tester, _FakeBackend(), _MemoryTokenStorage());
    await h.start(onboardingDone: true);

    expect(h.path, '/login');
    expect(find.text('다시 만나서 반갑습니다'), findsOneWidget);
    h.expectNeverProfileEdit();
    expect(h.storage.accessToken, isNull);
    await h.finish();
  });

  testWidgets('계약 1: 토큰이 없고 첫 실행이면 /onboarding으로 간다', (
    WidgetTester tester,
  ) async {
    final _Harness h = _Harness(tester, _FakeBackend(), _MemoryTokenStorage());
    await h.start(onboardingDone: false);

    expect(h.path, '/onboarding');
    h.expectNeverProfileEdit();
    await h.finish();
  });

  testWidgets('계약 2: 프로필이 있는 계정으로 로그인하면 /profile/edit를 거치지 않고 /dashboard로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: true);
    final _Harness h = _Harness(tester, backend, _MemoryTokenStorage());
    await h.start(onboardingDone: true);
    expect(h.path, '/login');

    await h.login();

    expect(h.path, '/dashboard');
    h.expectNeverProfileEdit();
    expect(h.storage.accessToken, 'login-access');
    expect(h.storage.refreshToken, 'login-refresh');
    await h.finish();
  });

  testWidgets('계약 3: 프로필이 없는 계정으로 로그인하면 /profile/edit로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: false);
    final _Harness h = _Harness(tester, backend, _MemoryTokenStorage());
    await h.start(onboardingDone: true);

    await h.login();

    expect(h.path, '/profile/edit');
    expect(find.byType(ProfileEditScreen), findsOneWidget);
    await h.finish();
  });

  testWidgets('계약 3: 회원가입 직후(프로필 없음)에는 /profile/edit로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: false);
    final _Harness h = _Harness(tester, backend, _MemoryTokenStorage());
    await h.start(onboardingDone: true);

    await tester.tap(find.widgetWithText(TextButton, '회원가입'));
    await h.advance(const Duration(milliseconds: 500));
    expect(h.path, '/register');

    await h.register();

    expect(backend.requestCount('POST', '/auth/register'), 1);
    expect(h.path, '/profile/edit');
    expect(find.byType(ProfileEditScreen), findsOneWidget);
    await h.finish();
  });

  testWidgets('계약 4: access 만료 + refresh 실패면 토큰을 지우고 /login으로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: true);
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'expired-access',
      refreshToken: 'expired-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    await h.advance(const Duration(seconds: 1));

    expect(backend.requestCount('POST', '/auth/refresh'), greaterThan(0));
    expect(storage.accessToken, isNull);
    expect(storage.refreshToken, isNull);
    expect(h.path, '/login');
    h.expectNeverProfileEdit();
    await h.finish();
  });

  testWidgets('계약 4: 대시보드에 있는 동안 늦게 온 401(갱신 실패)도 /login으로 보낸다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: true);
    final _Hold check = backend.holdNext('GET', '/profile/check');
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'expired-access',
      refreshToken: 'expired-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    expect(check.arrived.isCompleted, isTrue);
    // 확인 응답을 기다리는 동안에는 프로필 화면으로 보내지 않는다.
    expect(h.path, isNot('/profile/edit'));

    check.release();
    await h.advance(const Duration(seconds: 1));

    expect(storage.accessToken, isNull);
    expect(storage.refreshToken, isNull);
    expect(h.path, '/login');
    h.expectNeverProfileEdit();
    await h.finish();
  });

  testWidgets('계약 5: access 만료여도 refresh가 성공하면 /dashboard로 간다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(
      hasProfile: true,
      validRefreshTokens: <String>{'valid-refresh'},
    );
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'expired-access',
      refreshToken: 'valid-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    await h.advance(const Duration(seconds: 1));

    expect(backend.requestCount('POST', '/auth/refresh'), greaterThan(0));
    expect(storage.accessToken, startsWith('refreshed-access-'));
    expect(storage.refreshToken, 'valid-refresh');
    expect(h.path, '/dashboard');
    h.expectNeverProfileEdit();
    await h.finish();
  });

  testWidgets('계약 6: /profile/check가 5xx면 /profile/edit로 보내지 않고 토큰도 지우지 않는다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(
      hasProfile: false,
      profileCheckFailure: _CheckFailure.serverError,
    );
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'valid-access',
      refreshToken: 'valid-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    await h.advance(const Duration(seconds: 1));

    expect(backend.requestCount('GET', '/profile/check'), greaterThan(0));
    expect(h.path, '/dashboard');
    h.expectNeverProfileEdit();
    expect(storage.accessToken, 'valid-access');
    expect(storage.refreshToken, 'valid-refresh');
    await h.finish();
  });

  testWidgets(
    '계약 6: /profile/check가 네트워크 오류면 /profile/edit로 보내지 않고 토큰도 지우지 않는다',
    (WidgetTester tester) async {
      final _FakeBackend backend = _FakeBackend(
        hasProfile: false,
        profileCheckFailure: _CheckFailure.network,
      );
      final _MemoryTokenStorage storage = _MemoryTokenStorage(
        accessToken: 'valid-access',
        refreshToken: 'valid-refresh',
      );
      final _Harness h = _Harness(tester, backend, storage);
      await h.start(onboardingDone: true);
      await h.advance(const Duration(seconds: 1));

      expect(backend.requestCount('GET', '/profile/check'), greaterThan(0));
      expect(h.path, '/dashboard');
      h.expectNeverProfileEdit();
      expect(storage.accessToken, 'valid-access');
      expect(storage.refreshToken, 'valid-refresh');
      await h.finish();
    },
  );

  testWidgets('계약 7: 처음 프로필을 저장하면 /profile/edit를 벗어나고 다시 돌아오지 않는다', (
    WidgetTester tester,
  ) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: false);
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'valid-access',
      refreshToken: 'valid-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    expect(h.path, '/profile/edit');
    expect(find.text('프로필 설정'), findsWidgets);

    final Finder fields = _fieldsIn(ProfileEditScreen);
    await tester.enterText(fields.at(0), '175');
    await tester.enterText(fields.at(1), '70');
    await tester.enterText(fields.at(2), '28');
    final Finder save = find.widgetWithText(NeoPrimaryButton, '저장하기');
    await tester.ensureVisible(save);
    // 저장 뒤 다시 확인하는 요청을 붙잡아 실제 네트워크 지연을 흉내 낸다.
    // 확인이 끝나기 전에 이전 값(프로필 없음)으로 판단하면 /profile/edit로 되돌아간다.
    final _Hold recheck = backend.holdNext('GET', '/profile/check');
    final int savedAt = h.visited.length;
    await tester.tap(save);
    await h.advance(const Duration(seconds: 1));

    expect(backend.requestCount('PUT', '/profile'), 1);
    expect(backend.hasProfile, isTrue);
    expect(recheck.arrived.isCompleted, isTrue);
    expect(h.path, isNot('/profile/edit'), reason: '위치 기록: ${h.visited}');

    recheck.release();
    await h.advance(const Duration(seconds: 1));

    final List<String> afterSave = h.visited.sublist(savedAt);
    expect(
      afterSave,
      isNot(contains('/profile/edit')),
      reason: '위치 기록: ${h.visited}',
    );
    expect(h.path, '/dashboard');
    expect(find.byType(ProfileEditScreen), findsNothing);
    await h.finish();
  });

  testWidgets('계약 8: 로그아웃하면 /login으로 가고 토큰이 지워진다', (WidgetTester tester) async {
    final _FakeBackend backend = _FakeBackend(hasProfile: true);
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'valid-access',
      refreshToken: 'valid-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    expect(h.path, '/dashboard');

    h.router.go('/profile');
    await h.advance(const Duration(seconds: 1));
    expect(h.path, '/profile');

    final Finder logout = find.widgetWithText(NeoOutlineButton, '로그아웃');
    await tester.ensureVisible(logout);
    await tester.tap(logout);
    await h.advance(const Duration(seconds: 1));

    expect(h.path, '/login');
    expect(storage.accessToken, isNull);
    expect(storage.refreshToken, isNull);
    await h.finish();
  });

  testWidgets(
    '계약 9: 로그인 전에 보낸 /profile/check가 로그인 뒤 401로 끝나도 새 토큰을 지우지 않는다(갱신 성공)',
    (WidgetTester tester) async {
      final _FakeBackend backend = _FakeBackend(hasProfile: true);
      // 토큰 없이 시작할 때 나가는 첫 확인 요청(인증 헤더 없음 → 401)을 붙잡아 둔다.
      final _Hold stale = backend.holdNext('GET', '/profile/check');
      final _MemoryTokenStorage storage = _MemoryTokenStorage();
      final _Harness h = _Harness(tester, backend, storage);
      await h.start(onboardingDone: true);
      expect(stale.arrived.isCompleted, isTrue);
      expect(h.path, '/login');

      await h.login();
      expect(h.path, '/dashboard');

      stale.release();
      await h.advance(const Duration(seconds: 1));

      expect(storage.accessToken, isNotNull);
      expect(storage.refreshToken, 'login-refresh');
      expect(h.authState, AppAuthState.authenticated);
      expect(h.path, '/dashboard');
      h.expectNeverProfileEdit();
      await h.finish();
    },
  );

  testWidgets('계약 9: 로그인 전에 보낸 /profile/check가 재시도까지 401로 끝나도 로그아웃하지 않는다', (
    WidgetTester tester,
  ) async {
    // 갱신으로 받은 access도 서버가 거절해 이전 요청의 최종 결과가 401이 되는 경우.
    final _FakeBackend backend = _FakeBackend(
      hasProfile: true,
      acceptRefreshedAccess: false,
    );
    final _Hold stale = backend.holdNext('GET', '/profile/check');
    final _MemoryTokenStorage storage = _MemoryTokenStorage();
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    expect(h.path, '/login');

    await h.login();
    expect(h.path, '/dashboard');
    final int checksBeforeRelease = backend.requestCount(
      'GET',
      '/profile/check',
    );

    stale.release();
    await h.advance(const Duration(seconds: 1));

    // 이전 요청이 실제로 401로 끝났는지(재시도까지 거절됐는지) 확인한다.
    expect(
      backend.requestCount('GET', '/profile/check'),
      greaterThan(checksBeforeRelease),
    );
    expect(storage.refreshToken, 'login-refresh');
    expect(storage.accessToken, isNotNull);
    expect(h.authState, AppAuthState.authenticated);
    expect(h.path, '/dashboard');
    await h.finish();
  });

  testWidgets('계약 9: 로그인 전에 시작된 토큰 갱신이 로그인 뒤 실패해도 새 토큰을 지우지 않는다', (
    WidgetTester tester,
  ) async {
    // 저장된 토큰이 모두 만료된 상태에서 시작한다. 첫 확인 요청의 갱신 호출을 붙잡아 둔 채
    // 로그아웃 → 새 계정 로그인을 끝낸 뒤 이전 갱신을 401로 끝낸다.
    final _FakeBackend backend = _FakeBackend(hasProfile: true);
    final _Hold staleRefresh = backend.holdNext('POST', '/auth/refresh');
    final _MemoryTokenStorage storage = _MemoryTokenStorage(
      accessToken: 'expired-access',
      refreshToken: 'expired-refresh',
    );
    final _Harness h = _Harness(tester, backend, storage);
    await h.start(onboardingDone: true);
    expect(staleRefresh.arrived.isCompleted, isTrue);

    await h.container.read(authStateProvider.notifier).logout();
    await h.advance(const Duration(milliseconds: 500));
    expect(h.path, '/login');

    await h.login();
    expect(h.path, '/dashboard');
    expect(storage.accessToken, 'login-access');

    staleRefresh.release();
    await h.advance(const Duration(seconds: 1));

    expect(
      storage.accessToken,
      isNotNull,
      reason: '로그인으로 저장한 access token이 지워졌다',
    );
    expect(storage.refreshToken, 'login-refresh');
    expect(h.authState, AppAuthState.authenticated);
    expect(h.path, '/dashboard');
    await h.finish();
  });
}

Finder _fieldsIn(Type screen) =>
    find.descendant(of: find.byType(screen), matching: find.byType(TextField));

/// 앱을 띄우고 라우터 위치 변화를 기록한다.
class _Harness {
  final WidgetTester tester;
  final _FakeBackend backend;
  final _MemoryTokenStorage storage;
  final List<String> visited = <String>[];
  bool sawProfileEditScreen = false;
  late final GoRouter router;

  _Harness(this.tester, this.backend, this.storage);

  String get path => router.routerDelegate.currentConfiguration.uri.path;

  ProviderContainer get container =>
      ProviderScope.containerOf(tester.element(find.byType(MyApp)));

  AppAuthState? get authState => container.read(authStateProvider).valueOrNull;

  Future<void> start({required bool onboardingDone}) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      if (onboardingDone) 'onboarding_done': true,
    });
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureStorageServiceProvider.overrideWithValue(storage),
          // api_client.dart와 같은 구성(AuthInterceptor 포함)에 어댑터만 가짜로 바꾼다.
          dioProvider.overrideWith((Ref ref) {
            final SecureStorageService tokenStorage = ref.read(
              secureStorageServiceProvider,
            );
            final Dio dio = Dio(
              BaseOptions(baseUrl: 'http://contract.test/api/v1'),
            );
            dio.httpClientAdapter = backend;
            dio.interceptors.add(
              AuthInterceptor(storage: tokenStorage, dio: dio),
            );
            return dio;
          }),
        ],
        child: const MyApp(),
      ),
    );
    router = container.read(routerProvider);
    router.routerDelegate.addListener(_recordPath);
    _record();
    // 스플래시(1.5초) 뒤 이동과 그에 따른 redirect·요청이 끝날 때까지 진행한다.
    await advance(const Duration(milliseconds: 2500));
  }

  void _recordPath() {
    final String current = path;
    if (visited.isEmpty || visited.last != current) {
      visited.add(current);
    }
  }

  void _record() {
    _recordPath();
    if (find.byType(ProfileEditScreen).evaluate().isNotEmpty) {
      sawProfileEditScreen = true;
    }
  }

  Future<void> advance(
    Duration total, {
    Duration step = const Duration(milliseconds: 50),
  }) async {
    Duration elapsed = Duration.zero;
    while (elapsed < total) {
      await tester.pump(step);
      elapsed += step;
      _record();
    }
  }

  Future<void> login({
    String email = 'member@example.com',
    String password = 'Passw0rd!',
  }) async {
    // 전환 중인 이전 화면의 입력 필드와 섞이지 않게 로그인 화면 안에서만 찾는다.
    final Finder fields = _fieldsIn(LoginScreen);
    await tester.enterText(fields.at(0), email);
    await tester.enterText(fields.at(1), password);
    final Finder submit = find.widgetWithText(NeoPrimaryButton, '로그인');
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    await advance(const Duration(seconds: 2));
  }

  Future<void> register({
    String email = 'newbie@example.com',
    String password = 'Passw0rd!',
  }) async {
    // 로그인 화면이 전환으로 아직 남아 있을 수 있어 회원가입 화면 안에서만 찾는다.
    final Finder fields = _fieldsIn(RegisterScreen);
    await tester.enterText(fields.at(0), email);
    await tester.enterText(fields.at(1), password);
    await tester.enterText(fields.at(2), password);
    final Finder submit = find.widgetWithText(NeoPrimaryButton, '회원가입');
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    await advance(const Duration(seconds: 2));
  }

  void expectNeverProfileEdit() {
    expect(
      visited,
      isNot(contains('/profile/edit')),
      reason: '위치 기록: $visited',
    );
    expect(sawProfileEditScreen, isFalse, reason: '프로필 편집 화면이 그려졌다');
  }

  /// 남은 타이머(스낵바 등)를 정리하고 트리를 내린다.
  Future<void> finish() async {
    router.routerDelegate.removeListener(_recordPath);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(seconds: 5));
  }
}

class _MemoryTokenStorage extends SecureStorageService {
  String? accessToken;
  String? refreshToken;

  _MemoryTokenStorage({this.accessToken, this.refreshToken});

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

enum _CheckFailure { none, serverError, network }

/// 붙잡아 둔 요청. 요청이 도착하면 [arrived]가 완료되고 [release] 전까지 응답하지 않는다.
class _Hold {
  final Completer<void> arrived = Completer<void>();
  final Completer<void> _gate = Completer<void>();

  void release() => _gate.complete();
}

class _Request {
  final String method;
  final String path;
  final String? authorization;

  _Request(this.method, this.path, this.authorization);
}

/// API 명세 형식으로 답하는 가짜 서버. 응답 내용은 요청이 도착한 시점의 상태로 정한다.
class _FakeBackend implements HttpClientAdapter {
  bool hasProfile;
  final _CheckFailure profileCheckFailure;
  final bool acceptRefreshedAccess;
  final Set<String> validAccessTokens = <String>{'valid-access'};
  final Set<String> validRefreshTokens;
  final List<_Request> requests = <_Request>[];
  final Map<String, List<_Hold>> _holds = <String, List<_Hold>>{};
  int _refreshSeq = 0;

  _FakeBackend({
    this.hasProfile = true,
    this.profileCheckFailure = _CheckFailure.none,
    this.acceptRefreshedAccess = true,
    Set<String>? validRefreshTokens,
  }) : validRefreshTokens = validRefreshTokens ?? <String>{'valid-refresh'};

  _Hold holdNext(String method, String path) {
    final _Hold hold = _Hold();
    _holds.putIfAbsent('$method $path', () => <_Hold>[]).add(hold);
    return hold;
  }

  int requestCount(String method, String path) => requests
      .where((_Request r) => r.method == method && r.path == path)
      .length;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final Map<String, dynamic> body = await _readJson(requestStream);
    final String method = options.method.toUpperCase();
    final String path = options.path;
    final String? authorization = options.headers['Authorization'] as String?;
    requests.add(_Request(method, path, authorization));

    final _Reply reply = _respond(method, path, authorization, body);

    final List<_Hold>? queue = _holds['$method $path'];
    if (queue != null && queue.isNotEmpty) {
      final _Hold hold = queue.removeAt(0);
      hold.arrived.complete();
      await hold._gate.future;
    }

    if (reply.networkError) {
      throw DioException.connectionError(
        requestOptions: options,
        reason: '테스트용 네트워크 오류',
      );
    }
    return ResponseBody.fromString(
      jsonEncode(reply.body),
      reply.status,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>[Headers.jsonContentType],
      },
    );
  }

  _Reply _respond(
    String method,
    String path,
    String? authorization,
    Map<String, dynamic> body,
  ) {
    if (method == 'POST' &&
        (path == '/auth/login' || path == '/auth/register')) {
      validAccessTokens.add('login-access');
      validRefreshTokens.add('login-refresh');
      return _Reply(path == '/auth/register' ? 201 : 200, <String, dynamic>{
        'status': 'success',
        'data': <String, dynamic>{
          'access_token': 'login-access',
          'refresh_token': 'login-refresh',
          'token_type': 'bearer',
        },
      });
    }
    if (method == 'POST' && path == '/auth/refresh') {
      final Object? refreshToken = body['refresh_token'];
      if (refreshToken is String && validRefreshTokens.contains(refreshToken)) {
        _refreshSeq += 1;
        final String access = 'refreshed-access-$_refreshSeq';
        if (acceptRefreshedAccess) {
          validAccessTokens.add(access);
        }
        return _Reply(200, <String, dynamic>{
          'status': 'success',
          'data': <String, dynamic>{
            'access_token': access,
            'token_type': 'bearer',
          },
        });
      }
      return _unauthorized();
    }

    final String? token =
        authorization != null && authorization.startsWith('Bearer ')
        ? authorization.substring('Bearer '.length)
        : null;
    if (token == null || !validAccessTokens.contains(token)) {
      return _unauthorized();
    }

    if (method == 'GET' && path == '/profile/check') {
      switch (profileCheckFailure) {
        case _CheckFailure.serverError:
          return _Reply(500, <String, dynamic>{
            'detail': <String, dynamic>{
              'code': 'INTERNAL_ERROR',
              'message': '서버 오류',
            },
          });
        case _CheckFailure.network:
          return _Reply.network();
        case _CheckFailure.none:
          return _Reply(200, <String, dynamic>{'has_profile': hasProfile});
      }
    }
    if (method == 'GET' && path == '/profile') {
      if (!hasProfile) {
        return _Reply(404, <String, dynamic>{
          'detail': <String, dynamic>{
            'code': 'NOT_FOUND',
            'message': '프로필이 없습니다.',
          },
        });
      }
      return _Reply(200, <String, dynamic>{
        'status': 'success',
        'data': _profile,
      });
    }
    if (method == 'PUT' && path == '/profile') {
      hasProfile = true;
      return _Reply(200, <String, dynamic>{
        'status': 'success',
        'data': <String, dynamic>{..._profile, ...body},
      });
    }
    // 이 계약과 무관한 화면 데이터 요청은 404로 답한다(화면은 오류 상태를 그린다).
    return _Reply(404, <String, dynamic>{
      'detail': <String, dynamic>{'code': 'NOT_FOUND', 'message': '없음'},
    });
  }

  static const Map<String, dynamic> _profile = <String, dynamic>{
    'user_id': 1,
    'height_cm': 175.0,
    'weight_kg': 70.0,
    'age': 28,
    'gender': 'male',
    'goal': 'maintain',
    'activity_level': 'moderate',
    'allergies': <String>[],
    'food_preferences': <String>[],
    'tdee_kcal': 2500,
    'target_calories': 2500,
    'target_protein_g': 112.0,
    'target_carbs_g': 300.0,
    'target_fat_g': 70.0,
  };

  _Reply _unauthorized() => _Reply(401, <String, dynamic>{
    'detail': <String, dynamic>{
      'code': 'UNAUTHORIZED',
      'message': '인증이 필요합니다.',
    },
  });

  Future<Map<String, dynamic>> _readJson(Stream<Uint8List>? stream) async {
    if (stream == null) {
      return <String, dynamic>{};
    }
    final BytesBuilder bytes = BytesBuilder();
    await for (final Uint8List chunk in stream) {
      bytes.add(chunk);
    }
    if (bytes.isEmpty) {
      return <String, dynamic>{};
    }
    final Object? decoded = jsonDecode(utf8.decode(bytes.takeBytes()));
    return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
  }

  @override
  void close({bool force = false}) {}
}

class _Reply {
  final int status;
  final Map<String, dynamic> body;
  final bool networkError;

  _Reply(this.status, this.body) : networkError = false;

  _Reply.network()
    : status = 0,
      body = const <String, dynamic>{},
      networkError = true;
}
