import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class ProfileRepositoryException implements Exception {
  final String message;
  final int? statusCode;

  const ProfileRepositoryException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ProfileRepository {
  final Dio dio;

  ProfileRepository({required this.dio});

  Future<Map<String, dynamic>> getProfile() async {
    try {
      final Response<dynamic> response = await dio.get<dynamic>('/profile');
      return _parseProfileResponse(response.data);
    } on DioException catch (e) {
      throw ProfileRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> payload) async {
    try {
      final Response<dynamic> response = await dio.put<dynamic>(
        '/profile',
        data: payload,
      );
      return _parseProfileResponse(response.data);
    } on DioException catch (e) {
      throw ProfileRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Map<String, dynamic> _parseProfileResponse(dynamic rawResponse) {
    if (rawResponse is! Map<String, dynamic>) {
      throw const ProfileRepositoryException('서버 응답 형식이 올바르지 않습니다.');
    }

    if (rawResponse['status'] != 'success') {
      throw const ProfileRepositoryException('프로필 요청에 실패했습니다.');
    }

    final dynamic rawData = rawResponse['data'];
    if (rawData is! Map<String, dynamic>) {
      throw const ProfileRepositoryException('프로필 데이터가 누락되었습니다.');
    }

    return rawData;
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

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(dio: ref.read(dioProvider));
});
