import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class ChatRepositoryException implements Exception {
  final String message;
  final int? statusCode;

  const ChatRepositoryException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ChatRepository {
  final Dio dio;

  ChatRepository({required this.dio});

  Future<Map<String, dynamic>> sendMessage(
    String message,
    String contextType,
  ) async {
    try {
      final Response<dynamic> response = await dio.post<dynamic>(
        '/ai/chat',
        data: <String, dynamic>{
          'message': message,
          'context_type': contextType,
        },
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const ChatRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const ChatRepositoryException('AI 코칭 응답 조회에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const ChatRepositoryException('AI 코칭 응답 데이터가 비어 있습니다.');
      }

      return rawData;
    } on DioException catch (e) {
      throw ChatRepositoryException(
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

final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  return ChatRepository(dio: ref.read(dioProvider));
});
