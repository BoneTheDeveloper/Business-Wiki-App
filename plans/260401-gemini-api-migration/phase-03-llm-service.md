---
title: "Phase 3: LLM Service Rewrite"
description: "Replace AsyncOpenAI with google-genai for chat completions"
status: pending
priority: P1
effort: 30m
phase: 3
---

## Context Links
- [Plan Overview](plan.md)
- [Phase 1: Config & Dependencies](phase-01-config-and-dependencies.md)
- Current file: `backend/app/services/llm_service.py`

## Overview

Rewrite `LLMService` to use `google.genai.Client` for chat completions. Convert OpenAI message format (role/content dicts) to Gemini `contents` format with `systemInstruction` config.

## Key Insights

1. **Message format conversion.** OpenAI uses `messages=[{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]`. Gemini uses `systemInstruction` in config + `contents` as a flat list of `Content` parts with `role="user"` / `role="model"`.
2. **Role mapping:** `assistant` -> `model`, `user` -> `user`. System message extracted to `systemInstruction`.
3. **Usage metadata.** Gemini returns `response.usage_metadata.prompt_token_count` and `response.usage_metadata.candidates_token_count` (different field names from OpenAI).

## Requirements

### Functional
- `chat()` method signature unchanged -- same inputs, same output dict shape
- Conversation history support preserved (last 4 messages)
- System prompt extracted to `GenerateContentConfig.systemInstruction`
- Error state when `GOOGLE_API_KEY` not configured

### Non-Functional
- Async generation via `client.aio.models.generate_content()`
- Response format identical to current: `{answer, sources, model, usage}`
- Singleton pattern preserved

## Architecture

```python
# Before (OpenAI)
response = await self.client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": sys}, {"role": "user", "content": msg}],
    max_tokens=1000, temperature=0.7
)
# response.choices[0].message.content
# response.usage.prompt_tokens / response.usage.completion_tokens

# After (Gemini)
response = await self.client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=[{"role": "user", "parts": [{"text": msg}]}],
    config=types.GenerateContentConfig(
        systemInstruction=sys_prompt,
        maxOutputTokens=1000,
        temperature=0.7
    )
)
# response.text
# response.usage_metadata.prompt_token_count
# response.usage_metadata.candidates_token_count
```

## Related Code Files

### Modify
- `backend/app/services/llm_service.py` -- full rewrite of chat logic

## Implementation Steps

1. **Update imports**
   - Remove: `from openai import AsyncOpenAI`
   - Add: `from google import genai`, `from google.genai import types`

2. **Update `__init__`**
   ```python
   self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
   self.model = "gemini-2.0-flash"
   ```

3. **Rewrite `chat()` method**

   a. **API key guard** -- change `settings.OPENAI_API_KEY` to `settings.GOOGLE_API_KEY`, update error message text.

   b. **Build Gemini contents from history** -- convert OpenAI-style `{"role": ..., "content": ...}` to Gemini format:
   ```python
   # Map conversation history to Gemini format
   gemini_history = []
   if conversation_history:
       for msg in conversation_history[-4:]:
           role = "model" if msg["role"] == "assistant" else "user"
           gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})

   # Add current query with context
   current_content = f"Context from documents:\n{context_text}\n\nQuestion: {query}"
   gemini_history.append({"role": "user", "parts": [{"text": current_content}]})
   ```

   c. **Call Gemini API**:
   ```python
   response = await self.client.aio.models.generate_content(
       model=self.model,
       contents=gemini_history,
       config=types.GenerateContentConfig(
           systemInstruction=system_prompt,
           maxOutputTokens=1000,
           temperature=0.7
       )
   )
   ```

   d. **Extract response** -- `response.text` instead of `response.choices[0].message.content`

   e. **Extract usage** -- map `usage_metadata` fields:
   ```python
   "usage": {
       "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
       "completion_tokens": response.usage_metadata.candidates_token_count or 0
   }
   ```

   f. **Sources list** -- unchanged logic

4. **Return dict shape unchanged** -- `{answer, sources, model, usage}`

## Todo List
- [ ] Replace imports in llm_service.py
- [ ] Update `__init__` with genai.Client + gemini-2.0-flash
- [ ] Update API key guard to check `GOOGLE_API_KEY`
- [ ] Rewrite message building to Gemini contents format
- [ ] Rewrite API call to `client.aio.models.generate_content()`
- [ ] Map response.text and usage_metadata
- [ ] Verify return dict shape matches current contract
- [ ] Run `uv run python -c "from app.services.llm_service import llm_service; print('OK')"`

## Success Criteria
- `llm_service.py` imports without error
- No `openai` or `AsyncOpenAI` references remain
- `chat()` return dict has identical shape: `{answer: str, sources: list, model: str, usage: dict}`
- Conversation history correctly mapped (assistant -> model, user -> user)
- System prompt sent via `systemInstruction` not in contents

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| `response.text` is None when blocked by safety | Medium | Add fallback: `response.text or "I couldn't generate a response."` |
| `usage_metadata` fields are None | Low | Default to 0 with `or 0` |
| Gemini rejects multi-turn with system instruction | Low | Tested pattern from official docs -- works correctly |

## Next Steps
- Phase 4 updates celery_tasks.py and docker-compose.yml
