// TrendLineChart의 y축 범위. 눈금 3개(최소·중간·최대)가 "보기 좋은" 값에 오도록
// 간격을 1·2·2.5·5×10^n에서 고른다(§12-3: 눈금 3~4개, y축은 최소·중간·최대).
import 'dart:math' as math;

import 'app_number_format.dart';

class TrendScale {
  const TrendScale._(this.min, this.max, this.step, this.decimals);

  /// 데이터 [lo]~[hi]를 덮는 가장 촘촘한 2칸 눈금.
  factory TrendScale.fit(double lo, double hi) {
    final double span = hi - lo;
    double step = _niceCeil(
      span > 0 ? span / 2 : math.max(lo.abs() * 0.02, 0.1),
    );
    for (int guard = 0; guard < 24; guard++) {
      final double min = (lo / step).floorToDouble() * step;
      final double max = min + 2 * step;
      if (max >= hi - step * 1e-6) {
        return TrendScale._(min, max, step, _decimalsOf(step));
      }
      step = _niceCeil(step * 1.01);
    }
    return TrendScale._(lo, hi, (hi - lo) / 2, 1);
  }

  final double min;
  final double max;
  final double step;

  /// 축 라벨 소수 자릿수.
  final int decimals;

  String format(double value) => formatNumber(value, decimals: decimals);

  static const List<double> _nice = <double>[1, 2, 2.5, 5, 10];

  static double _niceCeil(double x) {
    if (x <= 0) return 1;
    final double magnitude = math
        .pow(10, (math.log(x) / math.ln10).floorToDouble())
        .toDouble();
    final double f = x / magnitude;
    for (final double n in _nice) {
      if (n >= f - 1e-9) return n * magnitude;
    }
    return 10 * magnitude;
  }

  static int _decimalsOf(double step) {
    for (int d = 0; d <= 3; d++) {
      final double scaled = step * math.pow(10, d);
      if ((scaled - scaled.roundToDouble()).abs() < 1e-6) return d;
    }
    return 3;
  }
}
