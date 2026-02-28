import 'package:dio/dio.dart';

import 'secure_storage_service.dart';

class AuthInterceptor extends Interceptor {
  final SecureStorageService storage;
  final Dio dio;

  AuthInterceptor({
    required this.storage,
    required this.dio,
  });

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
      final String? refreshToken = await storage.getRefreshToken();
      if (refreshToken == null || refreshToken.isEmpty) {
        handler.reject(err);
        return;
      }

      try {
        final Response<dynamic> refreshResp = await dio.post(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
          options: Options(headers: <String, dynamic>{}),
        );

        final dynamic data = refreshResp.data;
        String? newAccessToken;
        if (data is Map<String, dynamic>) {
          final dynamic innerData = data['data'];
          if (innerData is Map<String, dynamic>) {
            final dynamic tokenValue = innerData['access_token'];
            if (tokenValue is String) {
              newAccessToken = tokenValue;
            }
          }
        }

        if (newAccessToken == null || newAccessToken.isEmpty) {
          await storage.clearTokens();
          handler.reject(err);
          return;
        }

        await storage.saveAccessToken(newAccessToken);

        final RequestOptions retryOptions = err.requestOptions.copyWith(
          headers: <String, dynamic>{
            ...err.requestOptions.headers,
            'Authorization': 'Bearer $newAccessToken',
          },
          extra: <String, dynamic>{
            ...err.requestOptions.extra,
            '_retried': true,
          },
        );

        final Response<dynamic> retryResponse = await dio.fetch<dynamic>(retryOptions);
        handler.resolve(retryResponse);
        return;
      } catch (_) {
        await storage.clearTokens();
        handler.reject(err);
        return;
      }
    }

    handler.next(err);
  }
}
