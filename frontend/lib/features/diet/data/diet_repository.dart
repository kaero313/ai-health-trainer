import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class DietRepositoryException implements Exception {
  final String message;
  final int? statusCode;

  const DietRepositoryException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class DietRepository {
  final Dio dio;

  DietRepository({required this.dio});

  Future<Map<String, dynamic>> analyzeImage(String imagePath) async {
    try {
      final String fileName = imagePath.split(RegExp(r'[\\/]')).last;
      final FormData formData = FormData.fromMap(<String, dynamic>{
        'image': await MultipartFile.fromFile(imagePath, filename: fileName),
      });

      final Response<dynamic> response = await dio.post<dynamic>(
        '/diet/analyze-image',
        data: formData,
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const DietRepositoryException('이미지 분석에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const DietRepositoryException('이미지 분석 응답 데이터가 비어 있습니다.');
      }

      return rawData;
    } on DioException catch (e) {
      throw DietRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Future<Map<String, dynamic>> createDietLog(
    Map<String, dynamic> payload,
  ) async {
    try {
      final Response<dynamic> response = await dio.post<dynamic>(
        '/diet/logs',
        data: payload,
      );
      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const DietRepositoryException('식단 저장에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const DietRepositoryException('식단 저장 응답 데이터가 비어 있습니다.');
      }
      return rawData;
    } on DioException catch (e) {
      throw DietRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Future<Map<String, dynamic>> getDietLogs(String date) async {
    try {
      final Response<dynamic> response = await dio.get<dynamic>(
        '/diet/logs',
        queryParameters: <String, dynamic>{'date': date},
      );
      return _parseDietLogsResponse(response.data);
    } on DioException catch (e) {
      throw DietRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Future<Map<String, dynamic>> getRecommendation({String? date}) async {
    try {
      final Map<String, dynamic> queryParameters = <String, dynamic>{};
      if (date != null && date.trim().isNotEmpty) {
        queryParameters['date'] = date.trim();
      }

      final Response<dynamic> response = await dio.get<dynamic>(
        '/diet/recommend',
        queryParameters: queryParameters.isEmpty ? null : queryParameters,
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const DietRepositoryException('AI 식단 추천 조회에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const DietRepositoryException('AI 식단 추천 데이터가 비어 있습니다.');
      }
      return rawData;
    } on DioException catch (e) {
      throw DietRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Future<void> deleteDietLog(int logId) async {
    try {
      final Response<dynamic> response = await dio.delete<dynamic>(
        '/diet/logs/$logId',
      );
      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const DietRepositoryException('식단 삭제에 실패했습니다.');
      }
    } on DioException catch (e) {
      throw DietRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
      );
    }
  }

  Map<String, dynamic> _parseDietLogsResponse(dynamic rawResponse) {
    if (rawResponse is! Map<String, dynamic>) {
      throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
    }

    if (rawResponse['status'] != 'success') {
      throw const DietRepositoryException('식단 조회에 실패했습니다.');
    }

    final dynamic rawData = rawResponse['data'];
    if (rawData is! Map<String, dynamic>) {
      throw const DietRepositoryException('식단 데이터가 누락되었습니다.');
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

final dietRepositoryProvider = Provider<DietRepository>((ref) {
  return DietRepository(dio: ref.read(dioProvider));
});
