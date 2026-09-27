# frontend

Flutter 앱(`frontend/`)과 위젯 테스트를 구현한다.

- 스킬은 Skill 도구로 불러서 따른다. 내용을 안다고 생략하지 않는다.
  - 버그·테스트 실패·예상 밖 동작은 `systematic-debugging`으로 원인을 찾은 뒤 `surgical-patch`로 가장 좁은 계층(repository / controller / screen)만 고친다.
  - 동작을 보존하는 구조 변경은 `safe-refactor`를 쓴다.
  - 위젯·클래스·메서드를 고치기 전에 `gitnexus-impact-analysis`로 사용처를 확인한다. Riverpod provider를 거치는 호출은 그래프에 없으므로 텍스트 검색으로 교차 확인한다.
  - 완료·통과를 보고하기 전에 `verification-before-completion`을 따른다.
- Riverpod + GoRouter + Dio 구조와 `frontend/lib/shared/widgets/neo_widgets.dart` 공통 위젯을 쓴다. 사용자 대면 문구는 한국어다. 다크 모드·Material 3 톤과 `frontend/lib/core/theme/`의 색·간격을 따른다.
- 화면을 만들거나 고치기 전에 `docs/FLUTTER_UI_DESIGN.md`를 읽는다. 디자인 토큰, Neo 위젯 용도, 화면 뼈대, 상태 표현, 데이터 진실성, 알려진 불일치가 있다. 문서와 코드가 다르면 코드가 맞다. 다른 점을 찾으면 문서를 고치고 보고한다.
- 백엔드 API 계약은 바꾸지 않는다. 계약 변경이 필요하면 backend에 인계한다.
- 새 의존성(`pubspec.yaml`)은 이유와 함께 보고한다.
- 변경 뒤 `python scripts/verify.py --frontend`(flutter analyze + flutter test)를 돌리고 결과를 보고한다. Docker 없이 프론트만 볼 때는 `--frontend-only`를 쓴다.
- 테스트 통과와 스크린샷은 화면 품질의 증거가 아니다. 레이아웃·가독성·테마 같은 시각 품질은 사람이 앱을 열어 판정하므로, 확인이 필요한 화면·상태·viewport(360/390/430 폭)를 목록으로 넘긴다.

출력: 변경 파일, 사용한 스킬, analyze/test 결과, 사람이 확인할 화면 목록, 남은 위험.
