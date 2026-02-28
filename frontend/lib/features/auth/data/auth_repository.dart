import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class AuthRepositoryException implements Exception {
  final String message;
  final int? statusCode;

  const AuthRepositoryException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class AuthRepository {
  final Dio dio;

  AuthRepository({required this.dio});

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) {
    return _authenticate(
      path: '/auth/login',
      body: <String, dynamic>{
        'email': email,
        'password': password,
      },
    );
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String passwordConfirm,
  }) {
    return _authenticate(
      path: '/auth/register',
      body: <String, dynamic>{
        'email': email,
        'password': password,
        'password_confirm': passwordConfirm,
      },
    );
  }

  Future<Map<String, dynamic>> _authenticate({
    required String path,
    required Map<String, dynamic> body,
  }) async {
    try {
      final Response<dynamic> response = await dio.post<dynamic>(
        path,
        data: body,
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const AuthRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }

      if (rawResponse['status'] != 'success') {
        throw const AuthRepositoryException('인증 요청에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const AuthRepositoryException('토큰 데이터가 누락되었습니다.');
      }

      final dynamic accessToken = rawData['access_token'];
      final dynamic refreshToken = rawData['refresh_token'];
      if (accessToken is! String || accessToken.isEmpty) {
        throw const AuthRepositoryException('access_token이 유효하지 않습니다.');
      }
      if (refreshToken is! String || refreshToken.isEmpty) {
        throw const AuthRepositoryException('refresh_token이 유효하지 않습니다.');
      }

      return <String, dynamic>{
        'access_token': accessToken,
        'refresh_token': refreshToken,
      };
    } on DioException catch (e) {
      throw AuthRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  String _extractDioErrorMessage(DioException e) {
    final dynamic body = e.response?.data;
    if (body is Map<String, dynamic>) {
      final dynamic detail = body['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail is Map<String, dynamic>) {
        final dynamic detailMessage = detail['message'];
        if (detailMessage is String && detailMessage.isNotEmpty) {
          return detailMessage;
        }
      }

      final dynamic error = body['error'];
      if (error is Map<String, dynamic>) {
        final dynamic errorMessage = error['message'];
        if (errorMessage is String && errorMessage.isNotEmpty) {
          return errorMessage;
        }
      }

      final dynamic message = body['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }

    if (e.message != null && e.message!.isNotEmpty) {
      return e.message!;
    }
    return '요청 처리 중 오류가 발생했습니다.';
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(dio: ref.read(dioProvider));
});
