# 제3자 스킬 출처 표기

이 디렉터리의 스킬 중 아래 두 개는 [obra/superpowers](https://github.com/obra/superpowers)(MIT License)에서 유래했다.
내용을 수정하지 않고 옮겼으며, 원본 저장소의 최신 파일과 한 줄씩 대조하지는 않았다.

- `systematic-debugging/` — SKILL.md, root-cause-tracing.md, defense-in-depth.md, condition-based-waiting.md와 부속 파일 전부
- `verification-before-completion/` — SKILL.md

`systematic-debugging/SKILL.md`가 언급하는 `superpowers:test-driven-development`는 이 프로젝트에 포함하지 않았고,
`superpowers:verification-before-completion`은 `verification-before-completion`으로 포함돼 있다.

`verify-and-stop`, `surgical-patch`, `safe-refactor`는 이 프로젝트가 한국어로 작성한 자체 스킬이다.

`.agents/skills/`는 Codex가 같은 스킬을 읽도록 `scripts/harness.py render`가 만드는 이 디렉터리의 사본이다. 같은 출처와 라이선스가 적용된다.

## GitNexus 스킬 (PolyForm Noncommercial 1.0.0)

`gitnexus-cli/`, `gitnexus-debugging/`, `gitnexus-exploring/`, `gitnexus-guide/`, `gitnexus-impact-analysis/`, `gitnexus-refactoring/`의 `SKILL.md`는 npm 패키지 `gitnexus@1.6.12`의 `skills/gitnexus-*.md`를 수정 없이 복사했다.

- 저작자: Abhigyan Patwari
- 원본: https://github.com/abhigyanpatwari/GitNexus
- 라이선스: PolyForm Noncommercial License 1.0.0, https://polyformproject.org/licenses/noncommercial/1.0.0

이 라이선스는 비상업적 목적의 사용과 배포만 허용한다. 이 파일들을 받는 사람도 위 라이선스 조건을 따라야 한다.

## shadcn_ui 스킬 (MIT License)

`shadcn-ui-flutter/`는 2026-09-25에 `npx skills add nank1ro/flutter-shadcn-ui -s shadcn-ui-flutter -a claude-code --copy -y`로 설치했고 수정하지 않았다. 설치 기록은 저장소 루트의 `skills-lock.json`에 있다.

- 저작자: Alexandru Mariuti (Copyright (c) 2023)
- 원본: https://github.com/nank1ro/flutter-shadcn-ui (`skills/shadcn-ui-flutter/`)
- 라이선스: MIT License. 전문은 아래 obra/superpowers 항목과 같은 MIT 조건이다.
- 스킬 문서는 저장소 최신판 기준이다. 이 프로젝트는 같은 날 Flutter 3.41.9로 올려 `shadcn_ui 0.57.1`(당시 최신)을 쓴다. 패키지를 올릴 때는 스킬도 `npx skills update`로 맞추고 API 차이를 확인한다.

## MIT License (obra/superpowers)

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
