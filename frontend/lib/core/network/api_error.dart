import 'package:dio/dio.dart';

class ApiErrorDetails {
  final String? code;
  final String message;
  final int? statusCode;

  const ApiErrorDetails({
    required this.code,
    required this.message,
    required this.statusCode,
  });
}

ApiErrorDetails parseDioApiError(
  DioException exception, {
  required String fallbackMessage,
}) {
  return parseApiErrorBody(
    exception.response?.data,
    statusCode: exception.response?.statusCode,
    fallbackMessage: fallbackMessage,
    transportMessage: exception.message,
  );
}

ApiErrorDetails parseApiErrorBody(
  Object? body, {
  required String fallbackMessage,
  int? statusCode,
  String? transportMessage,
}) {
  final Map<String, dynamic>? root = _stringKeyedMap(body);
  final Map<String, dynamic>? detail = _stringKeyedMap(root?['detail']);
  final Map<String, dynamic>? error = _stringKeyedMap(root?['error']);
  final String? code = _firstNonEmptyString(<Object?>[
    detail?['code'],
    error?['code'],
    root?['code'],
  ]);
  final String? serverMessage = _firstNonEmptyString(<Object?>[
    detail?['message'],
    error?['message'],
    root?['message'],
    root?['detail'],
  ]);

  return ApiErrorDetails(
    code: code,
    message:
        _knownMessage(code) ??
        serverMessage ??
        _safeTransportMessage(transportMessage) ??
        fallbackMessage,
    statusCode: statusCode,
  );
}

String? _knownMessage(String? code) {
  return switch (code) {
    'AI_SCHEMA_INVALID' => 'AI 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해 주세요.',
    'RAG_CONTEXT_UNAVAILABLE' => '답변에 필요한 근거를 찾지 못했습니다. 조건을 바꿔 다시 시도해 주세요.',
    'DAILY_LIMIT_EXCEEDED' => '오늘 사용할 수 있는 AI 요청 횟수를 모두 사용했습니다.',
    'AI_TIMEOUT' => 'AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.',
    'AI_RATE_LIMITED' => 'AI 요청이 많습니다. 잠시 후 다시 시도해 주세요.',
    'AI_SERVICE_ERROR' => 'AI 서비스에 일시적인 문제가 발생했습니다.',
    'AI_BLOCKED' => '안전 정책에 따라 요청을 처리할 수 없습니다.',
    _ => null,
  };
}

Map<String, dynamic>? _stringKeyedMap(Object? value) {
  if (value is! Map) {
    return null;
  }
  return value.map<String, dynamic>(
    (dynamic key, dynamic item) =>
        MapEntry<String, dynamic>(key.toString(), item),
  );
}

String? _firstNonEmptyString(List<Object?> values) {
  for (final Object? value in values) {
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
  }
  return null;
}

String? _safeTransportMessage(String? message) {
  if (message == null || message.trim().isEmpty) {
    return null;
  }
  final String normalized = message.trim();
  if (normalized.length > 180 || normalized.contains('{')) {
    return null;
  }
  return normalized;
}
