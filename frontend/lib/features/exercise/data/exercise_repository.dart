import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class ExerciseRepositoryException implements Exception {
  final String message;
  final int? statusCode;

  const ExerciseRepositoryException(this.message, {this.statusCode});

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
      throw ExerciseRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
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
      );

      final dynamic rawResponse = response.data;
      if (rawResponse is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException('?쒕쾭 ?묐떟 ?뺤떇???щ컮瑜댁? ?딆뒿?덈떎.');
      }
      if (rawResponse['status'] != 'success') {
        throw const ExerciseRepositoryException('AI ?대룞 異붿쿇 議고쉶???ㅽ뙣?덉뒿?덈떎.');
      }

      final dynamic rawData = rawResponse['data'];
      if (rawData is! Map<String, dynamic>) {
        throw const ExerciseRepositoryException(
          'AI ?대룞 異붿쿇 ?곗씠?곌? 鍮꾩뼱 ?덉뒿?덈떎.',
        );
      }
      return rawData;
    } on DioException catch (e) {
      throw ExerciseRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
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
      throw ExerciseRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
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
      throw ExerciseRepositoryException(
        _extractDioErrorMessage(e),
        statusCode: e.response?.statusCode,
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

final exerciseRepositoryProvider = Provider<ExerciseRepository>((ref) {
  return ExerciseRepository(dio: ref.read(dioProvider));
});
