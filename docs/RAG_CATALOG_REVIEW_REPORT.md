# RAG Review Report

- review_run_id: 4
- review_type: catalog_plan
- target_run_id: 10
- status: completed
- requires_approval: True
- recommended_action: do_not_apply_until_resolved
- risk_level: high

## Items

| Source | Plan | Reason | Risk | Review Decision | Blocking | Recommendation |
|--------|------|--------|------|-----------------|----------|----------------|
| ODPHP Physical Activity Guidelines Questions and Answers | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| CDC Nutrition Guidelines and Recommendations | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| NIH ODS Dietary Supplements for Exercise and Athletic Performance Fact Sheet | manual_review_required | FETCH_OR_PARSE_FAILED | high | fix_source_acquisition | FETCH_OR_PARSE_FAILED | Fix the source acquisition path before apply: verify URL access, source replacement, or adapter behavior. |
