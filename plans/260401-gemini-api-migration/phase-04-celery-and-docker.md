---
title: "Phase 4: Celery Tasks & Docker Config"
description: "Update API key references in celery tasks and docker-compose"
status: pending
priority: P1
effort: 20m
phase: 4
---

## Context Links
- [Plan Overview](plan.md)
- [Phase 1: Config & Dependencies](phase-01-config-and-dependencies.md)
- Current files: `backend/app/services/celery_tasks.py`, `docker/docker-compose.yml`

## Overview

Two types of changes: (1) swap `settings.OPENAI_API_KEY` guards in celery tasks to `settings.GOOGLE_API_KEY`, (2) update docker-compose environment variable passthrough.

## Requirements

### Functional
- Celery tasks gate embedding on `GOOGLE_API_KEY` instead of `OPENAI_API_KEY`
- Docker containers receive `GOOGLE_API_KEY` env var

## Related Code Files

### Modify
- `backend/app/services/celery_tasks.py` -- 2 occurrences of `settings.OPENAI_API_KEY`
- `docker/docker-compose.yml` -- 2 occurrences of `OPENAI_API_KEY`

## Implementation Steps

### celery_tasks.py

1. **Line 85** -- `process_document_task`: change `if chunks and settings.OPENAI_API_KEY:` to `if chunks and settings.GOOGLE_API_KEY:`

2. **Line 182** -- `reindex_document_task`: change `if chunks and settings.OPENAI_API_KEY:` to `if chunks and settings.GOOGLE_API_KEY:`

No other changes needed. The celery tasks import `rag_service` singleton which will already use Gemini after Phase 2.

### docker-compose.yml

3. **Backend service** (line 36): change `OPENAI_API_KEY: ${OPENAI_API_KEY:-}` to `GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}`

4. **Celery worker service** (line 72): change `OPENAI_API_KEY: ${OPENAI_API_KEY:-}` to `GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}`

## Todo List
- [ ] Update `celery_tasks.py` line 85 -- `OPENAI_API_KEY` -> `GOOGLE_API_KEY`
- [ ] Update `celery_tasks.py` line 182 -- `OPENAI_API_KEY` -> `GOOGLE_API_KEY`
- [ ] Update `docker-compose.yml` backend service env var
- [ ] Update `docker-compose.yml` celery_worker service env var
- [ ] Grep for any remaining `OPENAI` references in backend source

## Success Criteria
- Zero `OPENAI` references in `backend/app/` source code
- Zero `OPENAI` references in `docker/docker-compose.yml`
- Celery tasks still import and call `rag_service` methods correctly (no API change needed)

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missed OPENAI reference somewhere | High | Final grep sweep in Phase 5 |
| Docker env var name mismatch | Medium | Verify with `docker compose config` |

## Next Steps
- Phase 5 runs tests and final verification
