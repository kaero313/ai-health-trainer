import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_error.dart';

void main() {
  test('structured AI errors expose code and safe Korean message', () {
    final RequestOptions request = RequestOptions(path: '/ai/chat');
    final DioException exception = DioException(
      requestOptions: request,
      response: Response<Map<String, dynamic>>(
        requestOptions: request,
        statusCode: 503,
        data: <String, dynamic>{
          'detail': <String, dynamic>{
            'code': 'RAG_CONTEXT_UNAVAILABLE',
            'message': 'provider raw detail should not be shown',
          },
        },
      ),
    );

    final ApiErrorDetails result = parseDioApiError(
      exception,
      fallbackMessage: 'fallback',
    );

    expect(result.code, 'RAG_CONTEXT_UNAVAILABLE');
    expect(result.statusCode, 503);
    expect(result.message, contains('근거를 찾지 못했습니다'));
    expect(result.message, isNot(contains('provider raw detail')));
  });
}
