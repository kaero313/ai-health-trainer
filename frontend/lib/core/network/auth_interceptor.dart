import 'package:dio/dio.dart';

import 'secure_storage_service.dart';

const String kRetryDataFactoryExtra = '_retry_data_factory';

typedef RetryDataFactory = Object? Function();

class AuthInterceptor extends Interceptor {
  final SecureStorageService storage;
  final Dio dio;
  Future<String?>? _refreshFuture;

  AuthInterceptor({required this.storage, required this.dio});

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final String? token = await storage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final int? statusCode = err.response?.statusCode;
    final String requestPath = err.requestOptions.path;
    final bool isRefreshCall = requestPath == '/auth/refresh';
    final bool alreadyRetried = err.requestOptions.extra['_retried'] == true;

    if (statusCode == 401 && !isRefreshCall && !alreadyRetried) {
      final String? newAccessToken = await _refreshAccessToken();
      if (newAccessToken == null || newAccessToken.isEmpty) {
        handler.reject(err);
        return;
      }

      try {
        final Object? retryData = _buildRetryData(err.requestOptions);

        final RequestOptions retryOptions = err.requestOptions.copyWith(
          data: retryData,
          headers: <String, dynamic>{
            ...err.requestOptions.headers,
            'Authorization': 'Bearer $newAccessToken',
          },
          extra: <String, dynamic>{
            ...err.requestOptions.extra,
            '_retried': true,
          },
        );

        final Response<dynamic> retryResponse = await dio.fetch<dynamic>(
          retryOptions,
        );
        handler.resolve(retryResponse);
        return;
      } on DioException catch (retryError) {
        handler.reject(retryError);
        return;
      } catch (_) {
        handler.reject(err);
        return;
      }
    }

    handler.next(err);
  }

  Object? _buildRetryData(RequestOptions options) {
    final Object? factory = options.extra[kRetryDataFactoryExtra];
    if (factory is RetryDataFactory) {
      return factory();
    }
    return options.data;
  }

  Future<String?> _refreshAccessToken() {
    final Future<String?>? activeRefresh = _refreshFuture;
    if (activeRefresh != null) {
      return activeRefresh;
    }

    final Future<String?> refresh = _performRefresh();
    _refreshFuture = refresh;
    refresh.whenComplete(() {
      if (identical(_refreshFuture, refresh)) {
        _refreshFuture = null;
      }
    });
    return refresh;
  }

  Future<String?> _performRefresh() async {
    final String? refreshToken = await storage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return null;
    }

    try {
      final Response<dynamic> refreshResp = await dio.post<dynamic>(
        '/auth/refresh',
        data: <String, dynamic>{'refresh_token': refreshToken},
        options: Options(headers: <String, dynamic>{}),
      );

      final dynamic data = refreshResp.data;
      final dynamic innerData =
          data is Map<String, dynamic> ? data['data'] : null;
      final dynamic tokenValue =
          innerData is Map<String, dynamic> ? innerData['access_token'] : null;
      if (tokenValue is! String || tokenValue.isEmpty) {
        await storage.clearTokens();
        return null;
      }

      await storage.saveAccessToken(tokenValue);
      return tokenValue;
    } catch (_) {
      await storage.clearTokens();
      return null;
    }
  }
}
