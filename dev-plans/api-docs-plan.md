# API Documentation Multi-Language Plan

> Created: 2026-03-22
> Status: Proposal — pending review

## Background

FIM One uses Mintlify for documentation with 6 languages (EN, ZH, JA, KO, DE, FR). The EN API Reference tab works well with auto-generated endpoints from `openapi.json`. However, locale API Reference tabs only show placeholder overview/authentication pages — no endpoint documentation.

### Current Architecture

```
docs/
├── openapi.json          # Manually curated, 16 public endpoints (5 tags)
├── docs.json             # Navigation config
├── api/
│   ├── overview.mdx      # EN API Overview (full content)
│   └── authentication.mdx # EN Authentication guide (full content)
├── zh/api/
│   ├── overview.mdx      # ZH placeholder → "see English version"
│   └── authentication.mdx # ZH placeholder → "see English version"
├── ja/api/ ...           # Same pattern for JA, KO, DE, FR
```

**EN docs.json API Reference tab:**
```json
{
  "tab": "API Reference",
  "groups": [
    { "group": "Overview", "pages": ["api/overview", "api/authentication"] },
    { "group": "Endpoints", "openapi": { "source": "openapi.json" } }
  ]
}
```

**Locale docs.json API Reference tabs (current):**
```json
{
  "tab": "API 参考",
  "groups": [
    { "group": "入门指南", "pages": ["zh/api/overview", "zh/api/authentication"] }
  ]
}
```
No endpoint pages — only the 2 overview/auth placeholder pages.

### Key Discovery: openapi.json Is Manually Curated

The `docs/openapi.json` is NOT auto-generated from FastAPI. It was written once and manually maintained. The live FastAPI server has 324 endpoints across 33 tags, but only 16 endpoints (5 tags) are in the public spec:

| Tag | Endpoints |
|-----|-----------|
| Chat | POST /api/react, POST /api/dag, POST /api/chat/inject |
| Conversations | GET/POST/PATCH/DELETE /api/conversations[/{id}] |
| Knowledge Bases | GET /api/knowledge-bases, POST /api/knowledge-bases/{id}/retrieve |
| Agents | GET /api/agents, GET /api/agents/{id} |
| API Keys | GET/POST/PATCH/DELETE /api/me/api-keys[/{id}] |

---

## Problem Statement

1. **Locale users see no API endpoints** — only 2 placeholder pages
2. **No auto-sync** — openapi.json is manually maintained, drifts from actual API
3. **MDX syntax landmines** — bare `<` before digits crashes Mintlify builds
4. **Mintlify limitation** — `"openapi": {"source": "..."}` in locale navigation blocks causes build failures

---

## Solution: Stay on Mintlify + Extend

### Why Not Migrate?

Evaluated 8 alternative platforms (ReadMe, Stoplight, Redocly, GitBook, Scalar, SwaggerHub, Bump.sh, Fern). None justified migration:

| Platform | Multi-Language | Migration Cost | Verdict |
|----------|:---:|:---:|---------|
| **Redocly** | Good (native l10n) | High (MDX→Markdoc rewrite) | Best alternative IF starting fresh |
| **GitBook** | Excellent (AI auto-translate) | High (WYSIWYG, not MDX) | Interesting but different paradigm |
| **ReadMe** | Partial (third-party) | High | Weak i18n, manual upload |
| **Scalar** | None | - | Dealbreaker |
| **Stoplight** | None | - | Dealbreaker |
| **SwaggerHub** | None | - | Wrong tool category |
| **Bump.sh** | None | - | API-only, no prose docs |
| **Fern** | None documented | - | $400/mo, acquired by Postman |

**Bottom line:** 100+ translated MDX files across 6 languages make migration impractical. Solve the gaps within Mintlify.

---

## Implementation Plan

### Phase 1: Fix MDX Safety (DONE)

- [x] Escape all bare `<digit` patterns in MDX files (wrap in backticks)
- [x] Remove `openapi` groups from locale navigation blocks
- [x] Create locale API placeholder pages (overview + authentication)
- [x] Build passing on Mintlify

### Phase 2: Auto-Generate Filtered openapi.json (Priority)

**Goal:** Replace manual openapi.json with a script that extracts the public subset from FastAPI's live spec.

```
scripts/generate_public_openapi.py
```

**How it works:**
1. Import the FastAPI app and call `app.openapi()` to get the full 324-endpoint spec
2. Filter to only include endpoints with public tags: `Chat`, `Conversations`, `Knowledge Bases`, `Agents`, `API Keys`
3. Clean up unused schemas from `components`
4. Write to `docs/openapi.json`

**Tag mapping** (FastAPI router tags → public doc tags):

| FastAPI Tag | Public Tag | Router File |
|-------------|-----------|-------------|
| `chat` | Chat | `api/chat.py` |
| `conversations` | Conversations | `api/conversations.py` |
| `knowledge-bases` | Knowledge Bases | `api/knowledge_bases.py` |
| `agents` | Agents | `api/agents.py` |
| `api-keys` | API Keys | `api/user_settings.py` |

**Script pseudocode:**
```python
from fim_one.web.app import create_app

PUBLIC_TAGS = {"Chat", "Conversations", "Knowledge Bases", "Agents", "API Keys"}

app = create_app()
spec = app.openapi()

# Filter paths by tag
filtered_paths = {}
for path, methods in spec["paths"].items():
    for method, operation in methods.items():
        if set(operation.get("tags", [])) & PUBLIC_TAGS:
            filtered_paths.setdefault(path, {})[method] = operation

# Clean unused schemas
used_refs = collect_refs(filtered_paths)
spec["paths"] = filtered_paths
spec["components"]["schemas"] = {k: v for k, v in spec["components"]["schemas"].items() if k in used_refs}

write_json("docs/openapi.json", spec)
```

**Integration:**
- Add to pre-commit hook or as a standalone `uv run scripts/generate_public_openapi.py`
- Run on every commit that touches `src/fim_one/web/api/` files

### Phase 3: Translated OpenAPI Specs for Locales

**Goal:** Generate locale-specific openapi.json files with translated `summary` and `description` fields.

**How it works:**
1. After Phase 2 generates `docs/openapi.json`, extend `translate.py` to handle OpenAPI JSON
2. Extract all `summary` and `description` strings from the spec
3. Translate them using the existing LLM translation pipeline
4. Write to `docs/zh/openapi.json`, `docs/ja/openapi.json`, etc.
5. Add `openapi` groups back to locale navigation in docs.json

**docs.json after Phase 3:**
```json
{
  "tab": "API 参考",
  "groups": [
    {
      "group": "入门指南",
      "pages": ["zh/api/overview", "zh/api/authentication"]
    },
    {
      "group": "API 端点",
      "openapi": { "source": "zh/openapi.json" }
    }
  ]
}
```

**Important:** This needs validation that Mintlify supports `openapi` in locale blocks when pointing to a locale-specific spec file. If not, fall back to Phase 3b.

### Phase 3b: Fallback — Explicit Endpoint Listing

If Mintlify doesn't support `openapi` in locale blocks at all, use explicit endpoint references:

```json
{
  "tab": "API 参考",
  "groups": [
    {
      "group": "入门指南",
      "pages": ["zh/api/overview", "zh/api/authentication"]
    },
    {
      "group": "Chat",
      "icon": "message-bot",
      "pages": [
        { "openapi": "POST /api/react" },
        { "openapi": "POST /api/dag" },
        { "openapi": "POST /api/chat/inject" }
      ]
    },
    {
      "group": "Conversations",
      "icon": "messages",
      "pages": [
        { "openapi": "GET /api/conversations" },
        { "openapi": "GET /api/conversations/{conversation_id}" },
        { "openapi": "POST /api/conversations" },
        { "openapi": "PATCH /api/conversations/{conversation_id}" },
        { "openapi": "DELETE /api/conversations/{conversation_id}" }
      ]
    }
  ]
}
```

**Tradeoff:** Endpoint descriptions stay in English (from openapi.json). This is actually standard practice — most multilingual API docs keep endpoints in English. Even Stripe, Twilio, and AWS only translate prose guides, not API reference.

### Phase 4: Translate API Prose Pages

**Goal:** Properly translate `api/overview.mdx` and `api/authentication.mdx` into all locales (currently just placeholders).

**Approach:**
1. Add these files to the normal `translate.py` pipeline
2. They contain `<Note>` and `<Warning>` Mintlify components — ensure the translate script preserves these tags
3. Code blocks (curl examples, JSON) should NOT be translated

**MDX Safety Rule:** Add to `translate.py` a post-processing step that escapes any bare `<digit` patterns in translated output. This prevents future build failures.

```python
import re

def escape_mdx_angles(text: str) -> str:
    """Wrap bare <digit patterns in backticks to prevent MDX JSX parse errors."""
    # Match < followed by digit NOT already inside backticks
    return re.sub(r'(?<!`)(<\s*\d)', r'`\1`', text)
```

---

## MDX Safety Guardrail

### Problem

MDX (used by Mintlify) parses `<` as JSX tag opener. When followed by a digit (like `<32K`, `< 6`, `<100ms`), the parser crashes with:

```
Unexpected character 3 (U+0033) before name, expected a character
that can start a name, such as a letter, $, or _
```

### Characters That Need Escaping in MDX Prose

| Pattern | Problem | Fix |
|---------|---------|-----|
| `<32K` | Parsed as JSX tag `<32K>` | `` `<32K` `` |
| `< 0.5` | Parsed as JSX tag | `` `< 0.5` `` |
| `{key: value}` | Parsed as JSX expression | `` `{key: value}` `` |
| `<!-- comment -->` | Invalid in MDX v2+ | `{/* comment */}` |

### Prevention

Add a CI check or pre-commit hook step:

```python
def check_mdx_safety(filepath: str) -> list[str]:
    """Check for bare angle brackets before digits outside code spans."""
    issues = []
    backtick_re = re.compile(r'`[^`]*`')
    angle_re = re.compile(r'<\s*\d')

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            cleaned = backtick_re.sub('', line)
            if angle_re.search(cleaned):
                issues.append(f"{filepath}:{i}: bare '<digit' pattern — wrap in backticks")
    return issues
```

---

## Mintlify OpenAPI Reference

### Filtering Options

Mintlify provides 3 ways to control endpoint visibility:

1. **`x-hidden`** — Hidden from nav, still accessible by URL
   ```json
   { "get": { "x-hidden": true, "summary": "Internal endpoint" } }
   ```

2. **`x-excluded`** — Completely removed from docs
   ```json
   { "get": { "x-excluded": true, "summary": "Not for public" } }
   ```

3. **Explicit listing** — Only referenced endpoints appear (whitelist approach)
   ```json
   { "pages": ["POST /api/react", "GET /api/conversations"] }
   ```

### Our Strategy

Since `docs/openapi.json` is already a curated subset (16 endpoints), we use **auto-generation for EN** + **explicit listing for locales** (Phase 3b). If Phase 3 (translated specs) works, we use auto-generation everywhere.

---

## Timeline Estimate

| Phase | Scope | When |
|-------|-------|------|
| Phase 1 | MDX safety fixes | DONE |
| Phase 2 | Auto-generate filtered openapi.json | Next sprint |
| Phase 3/3b | Locale endpoint pages | After Phase 2 validation |
| Phase 4 | Translate API prose pages | Can run in parallel with Phase 3 |

---

## Decision Points for Review

1. **Phase 2 priority** — Is auto-generating openapi.json important now, or is manual maintenance acceptable for the current 16 endpoints?
2. **Phase 3 vs 3b** — Need to test if Mintlify supports `openapi` in locale nav blocks with locale-specific spec files. If not, Phase 3b (explicit listing) is the fallback.
3. **Endpoint descriptions language** — Is English-only for API endpoints acceptable? (Industry standard: yes. Most developers read API docs in English.)
4. **translate.py scope** — Should the MDX safety check be added to the pre-commit hook?
