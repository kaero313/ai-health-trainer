# Review Gate Checklist

이 문서는 **HITL Gate 2** 용이다. 구현이 끝난 뒤 diff, 검증 결과, 릴리스 위험을 확인하고 merge 가능 여부를 결정한다.

## Change Summary

- Task ID:
- Branch or session:
- Changed files:
- Reviewer agent used:

## Diff Review

- [ ] 변경 범위가 Gate 1의 write scope 안에 있다.
- [ ] 의도하지 않은 파일 변경이 없다.
- [ ] 기존 사용자 변경을 revert 하지 않았다.

## Validation

- [ ] 필수 테스트/검증 명령 결과를 확인했다.
- [ ] 실패하거나 미실행한 검증이 있으면 이유가 기록돼 있다.
- [ ] reviewer findings가 있으면 처리 여부가 기록돼 있다.

## High-Risk Areas

- [ ] DB schema / migration 영향 검토
- [ ] auth / security 영향 검토
- [ ] public API contract 영향 검토
- [ ] Gemini 사용량 / 비용 / rate limit 영향 검토
- [ ] deploy / infra / secrets 영향 검토

## Decision

- Merge decision:
- Approved by:
- Approval timestamp:
- Follow-up tasks:
