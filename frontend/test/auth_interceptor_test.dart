import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/auth_interceptor.dart';
import 'package:frontend/core/network/secure_storage_service.dart';

void main() {
  test('refreshes and replays multipart data with a fresh body', () async {
    final _FakeSecureStorage storage = _FakeSecureStorage(
      accessToken: 'expired-access',
      refreshToken: 'refresh-token',
    );
    final _AuthTestAdapter adapter = _AuthTestAdapter();
    final Dio dio = _createDio(storage, adapter);

    int retryFactoryCalls = 0;
    FormData createFormData() {
      retryFactoryCalls += 1;
      return FormData.fromMap(<String, dynamic>{
        'image': MultipartFile.fromBytes(
          Uint8List.fromList(<int>[1, 2, 3, 4]),
          filename: 'meal.jpg',
        ),
      });
    }

    final FormData initialData = createFormData();
    retryFactoryCalls = 0;
    final Response<dynamic> response = await dio.post<dynamic>(
      '/diet/analyze-image',
      data: initialData,
      options: Options(
        extra: <String, dynamic>{kRetryDataFactoryExtra: createFormData},
      ),
    );

    expect(response.statusCode, 200);
    expect(adapter.refreshCalls, 1);
    expect(adapter.pathCalls['/diet/analyze-image'], 2);
    expect(adapter.uploadBodySizes, hasLength(2));
    expect(adapter.uploadBodySizes.every((int size) => size > 0), isTrue);
    expect(retryFactoryCalls, 1);
    expect(storage.accessToken, 'fresh-access');
    expect(storage.clearCount, 0);
  });

  test('coalesces concurrent 401 responses into one refresh call', () async {
    final _FakeSecureStorage storage = _FakeSecureStorage(
      accessToken: 'expired-access',
      refreshToken: 'refresh-token',
    );
    final _AuthTestAdapter adapter = _AuthTestAdapter(
      refreshDelay: const Duration(milliseconds: 30),
    );
    final Dio dio = _createDio(storage, adapter);

    final List<Response<dynamic>> responses = await Future.wait(
      <Future<Response<dynamic>>>[
        dio.get<dynamic>('/first'),
        dio.get<dynamic>('/second'),
      ],
    );

    expect(
      responses.map((Response<dynamic> response) => response.statusCode),
      <int>[200, 200],
    );
    expect(adapter.refreshCalls, 1);
    expect(adapter.pathCalls['/first'], 2);
    expect(adapter.pathCalls['/second'], 2);
    expect(storage.clearCount, 0);
  });

  test(
    'does not clear valid refreshed tokens when the retried request fails',
    () async {
      final _FakeSecureStorage storage = _FakeSecureStorage(
        accessToken: 'expired-access',
        refreshToken: 'refresh-token',
      );
      final _AuthTestAdapter adapter = _AuthTestAdapter(
        failRetriedRequest: true,
      );
      final Dio dio = _createDio(storage, adapter);

      await expectLater(
        dio.get<dynamic>('/retry-fails'),
        throwsA(
          isA<DioException>().having(
            (DioException error) => error.response?.statusCode,
            'statusCode',
            500,
          ),
        ),
      );

      expect(adapter.refreshCalls, 1);
      expect(storage.accessToken, 'fresh-access');
      expect(storage.refreshToken, 'refresh-token');
      expect(storage.clearCount, 0);
    },
  );
}

Dio _createDio(_FakeSecureStorage storage, _AuthTestAdapter adapter) {
  final Dio dio = Dio(BaseOptions(baseUrl: 'http://localhost'));
  dio.httpClientAdapter = adapter;
  dio.interceptors.add(AuthInterceptor(storage: storage, dio: dio));
  return dio;
}

class _FakeSecureStorage extends SecureStorageService {
  String? accessToken;
  String? refreshToken;
  int clearCount = 0;

  _FakeSecureStorage({this.accessToken, this.refreshToken});

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<String?> getRefreshToken() async => refreshToken;

  @override
  Future<void> saveAccessToken(String token) async {
    accessToken = token;
  }

  @override
  Future<void> clearTokens() async {
    clearCount += 1;
    accessToken = null;
    refreshToken = null;
  }
}

class _AuthTestAdapter implements HttpClientAdapter {
  final Duration refreshDelay;
  final bool failRetriedRequest;
  final Map<String, int> pathCalls = <String, int>{};
  final List<int> uploadBodySizes = <int>[];
  int refreshCalls = 0;

  _AuthTestAdapter({
    this.refreshDelay = Duration.zero,
    this.failRetriedRequest = false,
  });

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    int bodySize = 0;
    if (requestStream != null) {
      await for (final Uint8List chunk in requestStream) {
        bodySize += chunk.length;
      }
    }

    final String path = options.path;
    pathCalls[path] = (pathCalls[path] ?? 0) + 1;
    if (path == '/diet/analyze-image') {
      uploadBodySizes.add(bodySize);
    }

    if (path == '/auth/refresh') {
      refreshCalls += 1;
      if (refreshDelay > Duration.zero) {
        await Future<void>.delayed(refreshDelay);
      }
      return _jsonResponse(200, <String, dynamic>{
        'status': 'success',
        'data': <String, dynamic>{'access_token': 'fresh-access'},
      });
    }

    final String? authorization = options.headers['Authorization'] as String?;
    if (authorization != 'Bearer fresh-access') {
      return _jsonResponse(401, <String, dynamic>{'detail': 'expired'});
    }
    if (failRetriedRequest && path == '/retry-fails') {
      return _jsonResponse(500, <String, dynamic>{'detail': 'failed'});
    }
    return _jsonResponse(200, <String, dynamic>{'status': 'success'});
  }

  ResponseBody _jsonResponse(int statusCode, Map<String, dynamic> body) {
    return ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
