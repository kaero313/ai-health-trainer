import 'package:flutter/foundation.dart' show kIsWeb;

// ignore: prefer_const_declarations
final String kBaseUrl =
    kIsWeb
        ? 'http://localhost:8000/api/v1'
        : 'http://10.0.2.2:8000/api/v1';

const String kAccessTokenKey = 'access_token';
const String kRefreshTokenKey = 'refresh_token';
