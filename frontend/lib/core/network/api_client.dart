import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_interceptor.dart';
import 'constants.dart';
import 'secure_storage_service.dart';

final dioProvider = Provider<Dio>((ref) {
  final SecureStorageService storage = ref.read(secureStorageServiceProvider);

  final Dio dio = Dio(
    BaseOptions(
      baseUrl: kBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );

  dio.interceptors.add(
    AuthInterceptor(
      storage: storage,
      dio: dio,
    ),
  );

  return dio;
});
