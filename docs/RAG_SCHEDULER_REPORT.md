# RAG Scheduler Report

- run_id: 1
- status: approval_required
- mode: plan_only
- force_plan: True
- catalog_count: 2
- due_catalog_count: 2
- plan_run_ids: 10, 11
- approval_required_count: 1
- no_change_count: 1
- error_count: 0

## Catalogs

| Catalog | Due | Status | Plan Run | Approval | Create | Skip | Partial | Full | Manual | Defer | Reason |
|---------|-----|--------|----------|----------|--------|------|---------|------|--------|-------|--------|
| rag_sources/catalog.json | forced | approval_required | 10 | True | 0 | 2 | 0 | 0 | 1 | 0 | APPROVAL_REQUIRED |
| rag_sources/document_catalog.json | forced | no_change | 11 | False | 0 | 5 | 0 | 0 | 0 | 0 | PLAN_NO_CHANGE |
