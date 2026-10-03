# 01_CONFIGURATION_CONTRACT.md

## Phase 1 Configuration Contract

### Source Evidence (Phase 0)
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: Vite config missing `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md: `SERVICE_ROLE_KEY` never in frontend; `OLLAMA_BASE_URL` localhost only
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: Engine needs `pool_size=5`, `max_overflow=0`, `prepare_threshold=0` for PgBouncer

### Frontend Environment (Public-Safe Only)
```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=
```
- Only these three values may appear in frontend `.env` / Vite config.
- `SUPABASE_SERVICE_ROLE_KEY` is explicitly excluded from frontend bundles.

### Local Worker / Backend Environment (Private — Never Committed)
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5vl:3b
DATABASE_URL=postgresql+psycopg://...
```
- `SERVICE_ROLE_KEY` stored securely (Windows Credential Manager / `.env` gitignored).
- `OLLAMA_BASE_URL` remains localhost; no tunnels, no external exposure.

### Default Local Ollama Endpoint
```
http://127.0.0.1:11434
```
- Confirmed installed models (`ollama list`): `qwen2.5vl:3b`, `qwen3.5:4b`.
- Primary vision model for Phase 1: `qwen2.5vl:3b`.
- Fallback text-only: `qwen3.5:4b`.

### Engine Config (Supabase / PgBouncer)
```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
    connect_args={"prepare_threshold": 0},
    future=True,
)
```
- Matches 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md recommendation.

### Security Rules
- No `SERVICE_ROLE_KEY` in `src/lib/supabase/client.ts` or any frontend file.
- `.env.template` includes only public-safe variables; `.env` remains gitignored.
- No hard-coded secrets in any adapter, worker, or frontend component.
