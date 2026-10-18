// 타입 스케일 (docs/DESIGN_SYSTEM.md §4-2). 색은 넣지 않고 쓰는 곳에서 토큰으로 준다.
// NotoSansKR·Geist 모두 가변 폰트라 fontWeight와 wght 축(fontVariations)을 함께 지정한다.
import 'package:flutter/painting.dart';

abstract final class AppTextStyles {
  /// 앱 asset 한글 폰트 (pubspec family 이름).
  static const String textFamily = 'NotoSansKR';

  /// shadcn_ui 번들 Geist. `package:` 인자는 fallback에도 접두사를 붙이므로 경로를 직접 쓴다.
  static const String numberFamily = 'packages/shadcn_ui/Geist';

  static const List<String> _numberFallback = <String>[textFamily];

  static const TextStyle display = TextStyle(
    fontFamily: textFamily,
    fontSize: 28,
    height: 36 / 28,
    fontWeight: FontWeight.w700,
    fontVariations: <FontVariation>[FontVariation.weight(700)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle title = TextStyle(
    fontFamily: textFamily,
    fontSize: 20,
    height: 28 / 20,
    fontWeight: FontWeight.w700,
    fontVariations: <FontVariation>[FontVariation.weight(700)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle heading = TextStyle(
    fontFamily: textFamily,
    fontSize: 17,
    height: 24 / 17,
    fontWeight: FontWeight.w600,
    fontVariations: <FontVariation>[FontVariation.weight(600)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle body = TextStyle(
    fontFamily: textFamily,
    fontSize: 15,
    height: 22 / 15,
    fontWeight: FontWeight.w400,
    fontVariations: <FontVariation>[FontVariation.weight(400)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle bodyStrong = TextStyle(
    fontFamily: textFamily,
    fontSize: 15,
    height: 22 / 15,
    fontWeight: FontWeight.w600,
    fontVariations: <FontVariation>[FontVariation.weight(600)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: textFamily,
    fontSize: 13,
    height: 18 / 13,
    fontWeight: FontWeight.w400,
    fontVariations: <FontVariation>[FontVariation.weight(400)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: textFamily,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w500,
    fontVariations: <FontVariation>[FontVariation.weight(500)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle numHero = TextStyle(
    fontFamily: numberFamily,
    fontFamilyFallback: _numberFallback,
    fontSize: 40,
    height: 44 / 40,
    fontWeight: FontWeight.w700,
    fontVariations: <FontVariation>[FontVariation.weight(700)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle numLarge = TextStyle(
    fontFamily: numberFamily,
    fontFamilyFallback: _numberFallback,
    fontSize: 28,
    height: 32 / 28,
    fontWeight: FontWeight.w700,
    fontVariations: <FontVariation>[FontVariation.weight(700)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle numMedium = TextStyle(
    fontFamily: numberFamily,
    fontFamilyFallback: _numberFallback,
    fontSize: 20,
    height: 24 / 20,
    fontWeight: FontWeight.w600,
    fontVariations: <FontVariation>[FontVariation.weight(600)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  static const TextStyle numSmall = TextStyle(
    fontFamily: numberFamily,
    fontFamilyFallback: _numberFallback,
    fontSize: 13,
    height: 16 / 13,
    fontWeight: FontWeight.w500,
    fontVariations: <FontVariation>[FontVariation.weight(500)],
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  /// §8 compact 버튼 라벨(14/600). 11단계 스케일 밖의 파생값이다.
  static const TextStyle buttonCompact = TextStyle(
    fontFamily: textFamily,
    fontSize: 14,
    height: 20 / 14,
    fontWeight: FontWeight.w600,
    fontVariations: <FontVariation>[FontVariation.weight(600)],
    fontStyle: FontStyle.normal,
    letterSpacing: 0,
    leadingDistribution: TextLeadingDistribution.even,
  );

  /// §4-2 11단계 (토큰 이름, 스타일).
  static const List<(String, TextStyle)> scale = <(String, TextStyle)>[
    ('display', display),
    ('title', title),
    ('heading', heading),
    ('body', body),
    ('bodyStrong', bodyStrong),
    ('bodySmall', bodySmall),
    ('caption', caption),
    ('numHero', numHero),
    ('numLarge', numLarge),
    ('numMedium', numMedium),
    ('numSmall', numSmall),
  ];

  /// 굵기를 바꿀 때 wght 축도 같이 바꾼다. copyWith(fontWeight:)만 쓰면
  /// 남아 있는 fontVariations가 이전 굵기를 유지한다.
  static TextStyle withWeight(TextStyle style, FontWeight weight) {
    return style.copyWith(
      fontWeight: weight,
      fontVariations: <FontVariation>[
        FontVariation.weight(weight.value.toDouble()),
      ],
    );
  }
}
