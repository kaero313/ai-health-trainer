import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_error.dart';

class ExerciseRepositoryException implements Exception {
  final String message;
  final int? statusCode;
  final String? code;

  const ExerciseRepositoryException(this.message, {this.statusCode, this.code});

  @override
  String toString() => message;
}

class ExerciseRepository {
  final Dio dio;

  ExerciseRepository({required this.dio});

  Future<Map<String, dynamic>> getExerciseLogs(String date) async {
    try {
      final Response<dynamic> response = await dio.get<dynamic>(
        '/exercise/logs',
        queryParameters: <String, dynamic>{'date': date},
      );
      return _parseExerciseLogsResponse(response.data);
    } on DioException catch (e) {
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '운동 조회 요청 중 오류가 발생했습니다.',
      );
      throw ExerciseRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
      );
    }
  }

  Future<Map<String, dynamic>> getRecommendation({String? muscleGroup}) async {
    try {
      final Map<String, dynamic> queryParameters = <String, dynamic>{};
      if (muscleGroup != null && muscleGroup.trim().isNotEmpty) {
        queryParameters['muscle_group'] = muscleGroup.trim();
      }

      final Response<dynamic> response = await dio.get<dynamic>(
        '/exercise/recommend',
        queryParameters: queryParameters.isEmpty ? null : queryParameters,
        options: Options(receiveTimeout: kAiReceiveTimeout),
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const ExerciseRepositoryException('AI 운동 추천 조회에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('AI 운동 추천 데이터가 비어 있습니다.');
      }
      return rawData;
    } on DioException catch (e) {
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: 'AI 운동 추천 요청 중 오류가 발생했습니다.',
      );
      throw ExerciseRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
      );
    }
  }

  Future<Map<String, dynamic>> createExerciseLog(
    Map<String, dynamic> payload,
  ) async {
    try {
      final Response<dynamic> response = await dio.post<dynamic>(
        '/exercise/logs',
        data: payload,
      );
      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const ExerciseRepositoryException('운동 저장에 실패했습니다.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('운동 저장 응답 데이터가 비어 있습니다.');
      }
      return rawData;
    } on DioException catch (e) {
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '운동 저장 요청 중 오류가 발생했습니다.',
      );
      throw ExerciseRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
      );
    }
  }

  Future<void> deleteExerciseLog(int logId) async {
    try {
      final Response<dynamic> response = await dio.delete<dynamic>(
        '/exercise/logs/$logId',
      );
      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('서버 응답 형식이 올바르지 않습니다.');
      }
      if (rawResponse['status'] != 'success') {
        throw const ExerciseRepositoryException('운동 삭제에 실패했습니다.');
      }
    } on DioException catch (e) {
      final ApiErrorDetails error = parseDioApiError(
        e,
        fallbackMessage: '운동 삭제 요청 중 오류가 발생했습니다.',
      );
      throw ExerciseRepositoryException(
        error.message,
        statusCode: error.statusCode,
        code: error.code,
      );
    }
  }

  Map<String, dynamic> _parseExerciseLogsResponse(dynamic rawResponse) {
    if (rawResponse is! Map<String, dynamic>) {
      throw const ExerciseRepositoryException('서버 응답 형식이 올바르지 않습니다.');
    }

    if (rawResponse['status'] != 'success') {
      throw const ExerciseRepositoryException('운동 조회에 실패했습니다.');
    }

    final dynamic rawData = rawResponse['data'];
    if (rawData is! Map<String, dynamic>) {
      throw const ExerciseRepositoryException('운동 데이터가 비어 있습니다.');
    }

    return rawData;
  }
}

final exerciseRepositoryProvider = Provider<ExerciseRepository>((ref) {
  return ExerciseRepository(dio: ref.read(dioProvider));
});
