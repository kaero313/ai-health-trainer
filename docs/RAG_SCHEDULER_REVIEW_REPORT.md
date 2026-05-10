# RAG Review Report

- review_run_id: 3
- review_type: scheduler_run
- target_run_id: 1
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
| Internal Nutrition Basics Summary | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| Internal Progressive Overload Summary | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| Internal Joint Pain Safety Boundary | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| Internal Recovery Sleep Hydration Protocol | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
| Synthetic Protein PDF Text Fixture | skip_refresh | SOURCE_UNCHANGED | low | no_action |  | No apply is needed because the source and metadata are unchanged. |
