import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_error.dart';
import '../../../core/network/auth_interceptor.dart';

class DietRepositoryException implements Exception {
  final String message;
  final int? statusCode;
  final String? code;

  const DietRepositoryException(this.message, {this.statusCode, this.code});

  @override
  String toString() => message;
}

class DietRepository {
  final Dio dio;

  DietRepository({required this.dio});

  Future<Map<String, dynamic>> analyzeImage({
    required Uint8List bytes,
    required String filename,
    required String contentType,
  }) async {
    try {
      FormData createFormData() => FormData.fromMap(<String, dynamic>{
        'image': MultipartFile.fromBytes(
          bytes,
          filename: filename,
          contentType: DioMediaType.parse(contentType),
        ),
      });

      final Response<dynamic> response = await dio.post<dynamic>(
        '/diet/analyze-image',
        data: createFormData(),
        options: Options(
          receiveTimeout: kAiReceiveTimeout,
          extra: <String, dynamic>{kRetryDataFactoryExtra: createFormData},
        ),
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
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '이미지 분석 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
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
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '식단 저장 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
      );
    }
  }

  Future<List<Map<String, dynamic>>> searchFoods(
    String query, {
    int limit = 10,
  }) async {
    try {
      final Response<dynamic> response = await dio.get<dynamic>(
        '/diet/foods',
        queryParameters: <String, dynamic>{
          'query': query.trim(),
          'limit': limit,
        },
      );
      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const DietRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const DietRepositoryException('음식 검색에 실패했습니다.');
      }
      final dynamic rawData = rawResponse['data'];
      if (rawData is! List<dynamic>) {
        throw const DietRepositoryException('음식 검색 데이터가 비어 있습니다.');
      }
      return rawData.whereType<Map<String, dynamic>>().toList();
    } on DioException catch (e) {
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '음식 검색 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
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
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '식단 조회 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
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
        options: Options(receiveTimeout: kAiReceiveTimeout),
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
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: 'AI 식단 추천 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
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
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '식단 삭제 요청 중 오류가 발생했습니다.',
      );
      throw DietRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
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
}

final dietRepositoryProvider = Provider<DietRepository>((ref) {
  return DietRepository(dio: ref.read(dioProvider));
});
