// 내부 전용 진입점: flutter run -t lib/main_design_mockups.dart
// 웹: flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3002 -t lib/main_design_mockups.dart
// 바로 열기: http://127.0.0.1:3002/#/dashboard?state=data&mode=dark
import 'package:flutter/widgets.dart';

import 'dev/mockups/mockup_app.dart';

void main() => runApp(const MockupApp());
