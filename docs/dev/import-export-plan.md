# FIM One — Import / Export Feature Plan

## Design Philosophy

**"Configuration as portable data"** — all user-created configuration should be exportable as JSON, importable to any FIM One instance (SQLite or PostgreSQL), with encrypted fields decrypted on export and re-encrypted on import.

---

## Export Format

Single JSON file per scope, versioned:

```json
{
  "fim_one_export": {
    "version": "1.0",
    "exported_at": "2026-03-21T12:00:00Z",
    "instance": "https://fim.example.com",
    "scope": "full | admin | user | feature",
    "sections": { ... }
  }
}
```

---

## Import Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `merge` | Skip existing (match by name), add new only | Incremental sync |
| `replace` | Drop existing + reimport all | Fresh environment setup |
| `update` | Merge + overwrite existing by name match | Config update push |

---

## Phase Plan

### Phase 1 — Model Provider Config (Priority: P0)

**Scope:** Admin panel → Model management

| Entity | Table | Complexity | Sensitive Fields |
|--------|-------|-----------|-----------------|
| Providers | `model_providers` | Low | `api_key` (EncryptedString) |
| Provider Models | `model_provider_models` | Low | — |
| Model Groups | `model_groups` | Medium (FK refs) | — |

**Export structure:**
```json
{
  "model_config": {
    "providers": [
      {
        "name": "Uniapi",
        "base_url": "https://hk.uniapi.io/v1",
        "api_key": null,          // redacted on export; user fills on import
        "is_active": true,
        "models": [
          { "name": "gpt-5.4", "model_name": "gpt-5.4", "temperature": null, ... }
        ]
      }
    ],
    "groups": [
      {
        "name": "OpenAI",
        "description": null,
        "general_model": "gpt-5.4",           // resolved by model_name
        "fast_model": "gpt-5.4-mini",
        "reasoning_model": "o3-pro"
      }
    ]
  }
}
```

**Key design:**
- Groups reference models by `model_name` (not UUID) → portable across instances
- API keys exported as `null` with `"api_key_required": true` flag
- Import resolves group→model FK by matching `provider.name` + `model.model_name`

**API:**
- `GET  /api/admin/model-config/export`
- `POST /api/admin/model-config/import` `{ mode: "merge"|"replace", data: {...}, api_keys: { "Uniapi": "sk-xxx" } }`

**UI:** Settings → Model Management page, top-right "Export" / "Import" buttons

---

### Phase 2 — Core Feature Export (Priority: P0)

**Scope:** Agents, Skills, Connectors, MCP Servers, Knowledge Bases

These are the user's primary work product. Must support both **individual** and **bulk** export.

#### 2a. Connectors + Actions

| Entity | Table | Sensitive Fields |
|--------|-------|-----------------|
| Connectors | `connectors` | `auth_config` (JSON with keys) |
| Actions | `connector_actions` | — |
| DB Schemas | `database_schemas` + `schema_columns` | — |

**Export structure:**
```json
{
  "connectors": [
    {
      "name": "GitHub API",
      "type": "api",
      "base_url": "https://api.github.com",
      "auth_type": "bearer",
      "auth_config": null,           // redacted
      "actions": [
        { "name": "List Repos", "method": "GET", "path": "/user/repos", ... }
      ],
      "database_schemas": []         // for DB-type connectors only
    }
  ]
}
```

#### 2b. MCP Servers

| Entity | Table | Sensitive Fields |
|--------|-------|-----------------|
| MCP Servers | `mcp_servers` | `env` (EncryptedJSON), `headers` (EncryptedJSON) |

**Export:** Command, args, URL preserved; env/headers redacted with `"env_keys_required": ["API_KEY", "SECRET"]` hint.

#### 2c. Knowledge Bases (metadata only)

| Entity | Table | Notes |
|--------|-------|-------|
| Knowledge Bases | `knowledge_bases` | Config only |
| Documents | `kb_documents` | Metadata only; actual files + embeddings NOT exported |

**Export:** KB config (chunk strategy, retrieval mode) + document list (filename, file_type). Embeddings/vectors are NOT portable — user must re-upload and re-index documents after import.

#### 2d. Skills

| Entity | Table | References |
|--------|-------|-----------|
| Skills | `skills` | `resource_refs` → connectors, KBs by alias |

**Export:** Inline content/script + resource_refs. On import, resolve connector/KB references by name.

#### 2e. Agents

| Entity | Table | References |
|--------|-------|-----------|
| Agents | `agents` | `connector_ids`, `kb_ids`, `mcp_server_ids`, `skill_ids` (JSON arrays) |

**Export:** Full agent config. References exported as names (not UUIDs). On import, resolve by name match.

```json
{
  "agents": [
    {
      "name": "Research Assistant",
      "instructions": "...",
      "execution_mode": "react_json",
      "model_config": { ... },
      "connectors": ["GitHub API", "Jira"],     // by name
      "knowledge_bases": ["Company Wiki"],
      "mcp_servers": ["Filesystem"],
      "skills": ["Web Search SOP"],
      "suggested_prompts": ["..."],
      "grounding_config": { ... }
    }
  ]
}
```

**API (per-entity):**
- `GET  /api/{entity}/export?ids=a,b,c` — export selected items
- `GET  /api/{entity}/export` — export all
- `POST /api/{entity}/import` — import with mode

**API (bulk):**
- `GET  /api/export/bundle` — export ALL features together
- `POST /api/import/bundle` — import bundle

**UI:**
- Each list page: checkbox select → "Export Selected" button
- Top-level: Settings → "Export All / Import All" for full migration

---

### Phase 3 — Workflows (Priority: P1)

**Scope:** Most complex entity — deep nested blueprint with cross-references

| Entity | Table | Notes |
|--------|-------|-------|
| Workflows | `workflows` | Blueprint JSON references agents, skills, connectors, KBs, MCP servers by ID |
| Templates | `workflow_templates` | Admin-managed, blueprint JSON |

**Export structure:**
```json
{
  "workflows": [
    {
      "name": "Customer Onboarding",
      "blueprint": {
        "nodes": [
          {
            "type": "agent",
            "agent_ref": "Research Assistant",    // resolved by name
            "config": { ... }
          },
          {
            "type": "connector",
            "connector_ref": "Salesforce API",
            "action_ref": "Create Contact",
            ...
          }
        ],
        "edges": [ ... ]
      },
      "input_schema": { ... },
      "output_schema": { ... },
      "env_vars": null,              // redacted, key list provided
      "env_var_keys_required": ["SF_TOKEN", "SLACK_WEBHOOK"],
      "schedule_cron": "0 9 * * 1-5",
      "schedule_enabled": false      // always disabled on import
    }
  ]
}
```

**Key design:**
- Blueprint node references resolved by entity name, not UUID
- `env_vars_blob` decrypted → key names listed, values redacted
- `schedule_enabled` forced to `false` on import (safety — user must manually enable)
- `api_key` regenerated on import (new webhook endpoint)
- Workflow versions NOT exported (clean start)
- Workflow runs NOT exported (transactional)

---

### Phase 4 — Evaluation Center (Priority: P2)

| Entity | Table | Export? |
|--------|-------|--------|
| Eval Datasets | `eval_datasets` | YES — config |
| Eval Cases | `eval_cases` | YES — config (prompt + expected + assertions) |
| Eval Runs | `eval_runs` | NO — transactional |
| Eval Case Results | `eval_case_results` | NO — transactional |

**Export:**
```json
{
  "eval_datasets": [
    {
      "name": "Agent QA Benchmark",
      "cases": [
        { "prompt": "...", "expected_behavior": "...", "assertions": [...] }
      ]
    }
  ]
}
```

---

### Phase 5 — Admin System Config (Priority: P2)

**Scope:** System-wide settings that an admin would want to replicate across instances

| Entity | Table | Export? |
|--------|-------|--------|
| System Settings | `system_settings` | YES |
| IP Rules | `ip_rules` | YES |
| Sensitive Words | `sensitive_words` | YES |
| Announcements | `announcements` | OPTIONAL |
| Invite Codes | `announce_code` | NO (instance-specific) |
| Workflow Templates | `workflow_templates` | YES |

**API:**
- `GET  /api/admin/system-config/export`
- `POST /api/admin/system-config/import`

---

### Phase 6 — User Settings Portability (Priority: P3)

**Scope:** User-level preferences and personal config

| Entity | Export? | Notes |
|--------|---------|-------|
| User profile (timezone, language, system_instructions) | YES | |
| User model_configs | YES | API keys redacted |
| Notification preferences | YES | |
| API keys | NO | Hashed, cannot recover. Must regenerate. |
| OAuth bindings | NO | Instance-specific |

**API:**
- `GET  /api/user/settings/export`
- `POST /api/user/settings/import`

---

## Dependency Resolution Order

Import MUST process entities in this order to resolve FK references:

```
1. Model Providers → Models → Groups
2. Connectors → Actions → DB Schemas
3. MCP Servers
4. Knowledge Bases (metadata)
5. Skills (references connectors, KBs)
6. Agents (references connectors, KBs, MCP servers, skills)
7. Workflows (references agents, skills, connectors, KBs, MCP servers)
8. Eval Datasets → Cases
9. User Settings
10. Admin System Config
```

---

## Encrypted Field Strategy

| Export | Import |
|-------|--------|
| Decrypt using source instance's `ENCRYPTION_KEY` | Re-encrypt using destination instance's `ENCRYPTION_KEY` |
| Redact sensitive values (`api_key → null`) | User provides values during import (via JSON or UI form) |
| Provide `*_keys_required` hints | UI shows "fill required secrets" step before final import |

**Import UI flow:**
1. Upload JSON → parse & validate
2. Show preview (entity counts, conflict detection)
3. Show "Required Secrets" form (API keys, env vars, credentials)
4. User fills secrets → confirm
5. Import executes with progress bar

---

## Conflict Resolution (merge mode)

| Scenario | Default Behavior |
|----------|-----------------|
| Same name exists | Skip (keep existing) |
| Same name, different config | Skip + report as conflict |
| Referenced entity missing | Create placeholder + warn |
| Circular reference | Break cycle, import in phases |

---

## NOT Exported (by design)

| Data | Reason |
|------|--------|
| Conversations & Messages | Already have per-conversation export (MD/DOCX/PDF) |
| Artifacts | User explicitly excluded |
| Workflow Runs | Transactional execution logs |
| Eval Results | Transactional test results |
| Audit Logs | Instance-specific security records |
| Login History | Instance-specific |
| Connector Call Logs | Transactional API call records |
| Review Logs | Instance-specific approval history |

---

## API Summary

### Admin APIs
| Method | Endpoint | Phase |
|--------|----------|-------|
| GET | `/api/admin/model-config/export` | P0 |
| POST | `/api/admin/model-config/import` | P0 |
| GET | `/api/admin/system-config/export` | P2 |
| POST | `/api/admin/system-config/import` | P2 |

### Feature APIs (per entity)
| Method | Endpoint | Phase |
|--------|----------|-------|
| GET | `/api/connectors/export?ids=...` | P0 |
| POST | `/api/connectors/import` | P0 |
| GET | `/api/mcp-servers/export?ids=...` | P0 |
| POST | `/api/mcp-servers/import` | P0 |
| GET | `/api/knowledge-bases/export?ids=...` | P0 |
| POST | `/api/knowledge-bases/import` | P0 |
| GET | `/api/skills/export?ids=...` | P0 |
| POST | `/api/skills/import` | P0 |
| GET | `/api/agents/export?ids=...` | P0 |
| POST | `/api/agents/import` | P0 |
| GET | `/api/workflows/export?ids=...` | P1 |
| POST | `/api/workflows/import` | P1 |
| GET | `/api/eval/datasets/export?ids=...` | P2 |
| POST | `/api/eval/datasets/import` | P2 |

### Bundle APIs (full migration)
| Method | Endpoint | Phase |
|--------|----------|-------|
| GET | `/api/export/bundle?sections=agents,skills,...` | P0 |
| POST | `/api/import/bundle` | P0 |

### User APIs
| Method | Endpoint | Phase |
|--------|----------|-------|
| GET | `/api/user/settings/export` | P3 |
| POST | `/api/user/settings/import` | P3 |

---

## Frontend UI Plan

### Per-entity list pages
- Add checkbox column to data tables
- Add "Export Selected" button (top toolbar, beside existing buttons)
- Add "Import" button → opens import dialog

### Import Dialog (shared component)
1. **Upload step** — drag-and-drop JSON file
2. **Preview step** — show entity counts, conflicts, warnings
3. **Secrets step** — form for required API keys / env vars / credentials
4. **Confirm step** — mode selector (merge/replace/update) + execute
5. **Result step** — success/failure summary with details

### Settings page
- Add "Data Management" section
- "Export Everything" / "Import from Backup" buttons
- Last export timestamp display

---

## Implementation Estimate

| Phase | Scope | Backend | Frontend |
|-------|-------|---------|----------|
| P0 | Model Config + Core Features | ~800 lines | ~400 lines |
| P1 | Workflows | ~300 lines | reuse P0 components |
| P2 | Eval + Admin Config | ~200 lines | reuse P0 components |
| P3 | User Settings | ~150 lines | reuse P0 components |

**Shared infra (one-time):**
- Export/import service layer with dependency resolver: ~500 lines
- Shared ImportDialog component: ~300 lines
- Name-based reference resolution utility: ~200 lines
