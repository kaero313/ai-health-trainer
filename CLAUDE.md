@AGENTS.md

Claude Code는 위 공통 규칙과 `harness/agents.toml`의 역할·모델 배정을 사용한다.
역할은 `.claude/agents/`, 스킬은 `.claude/skills/`에서 읽는다. 생성된 역할 파일은 직접 편집하지 않는다.
사용자·조직 설정이나 실행 인자가 역할의 모델·effort를 덮어쓰면 보고하고 진행 여부를 묻는다.
인증·토큰, AI 쿼터·Gemini 호출 경로, RAG apply/reindex/archive, 마이그레이션, retrieval trace 개인정보를 건드리는 변경은 qa 독립 테스트와 reviewer 검토를 거친다.
