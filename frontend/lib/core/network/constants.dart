import 'package:flutter/foundation.dart' show kIsWeb;

const String _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

final String kBaseUrl =
    _configuredBaseUrl.isNotEmpty
        ? _configuredBaseUrl
        : kIsWeb
        ? 'http://localhost:8000/api/v1'
        : 'http://10.0.2.2:8000/api/v1';

const String kAccessTokenKey = 'access_token';
const String kRefreshTokenKey = 'refresh_token';
