// 수치 표기 도우미 (docs/DESIGN_SYSTEM.md §4-2: 천 단위 구분 기호).
// 로케일 데이터 초기화가 필요 없도록 직접 구현한다.

/// 1185 → "1,185", 72.4 (decimals: 1) → "72.4".
String formatNumber(num value, {int decimals = 0}) {
  final bool negative = value < 0;
  final String fixed = value.abs().toStringAsFixed(decimals);
  final List<String> parts = fixed.split('.');
  final String whole = parts.first;
  final StringBuffer buffer = StringBuffer();
  for (int i = 0; i < whole.length; i++) {
    final int fromEnd = whole.length - i;
    buffer.write(whole[i]);
    if (fromEnd > 1 && fromEnd % 3 == 1) buffer.write(',');
  }
  final String fraction = parts.length > 1 ? '.${parts[1]}' : '';
  return '${negative ? '-' : ''}$buffer$fraction';
}
