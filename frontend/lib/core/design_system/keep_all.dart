// 한글 문장을 단어 중간에서 줄바꿈하지 않게 한다(CSS word-break: keep-all과 같은 효과).
// Flutter는 한글 음절 사이에서도 줄을 바꾸므로("됐습니/다"), 단어 안 글자 사이에
// 폭이 없는 WORD JOINER(U+2060)를 넣어 공백에서만 줄이 바뀌게 한다.
// 화면 낭독기와 테스트가 원문을 쓰도록 Text의 semanticsLabel에는 원문을 넘긴다.

const String _wordJoiner = '\u2060';

/// 이미 처리된 문장을 다시 넣어도 결과가 같다.
String keepAll(String text) {
  return withoutJoiners(text).splitMapJoin(
    RegExp(r'\s+'),
    onMatch: (Match m) => m[0]!,
    onNonMatch: (String word) =>
        word.runes.map(String.fromCharCode).join(_wordJoiner),
  );
}

/// [keepAll]이 넣은 WORD JOINER를 뺀 원문. 화면 낭독기 라벨에 쓴다.
String withoutJoiners(String text) => text.replaceAll(_wordJoiner, '');
