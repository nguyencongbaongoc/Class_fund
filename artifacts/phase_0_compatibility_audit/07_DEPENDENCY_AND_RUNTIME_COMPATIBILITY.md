# PHASE 0 — DEPENDENCY AND RUNTIME COMPATIBILITY

## Executive Summary
**Status: COMPATIBLE** — Both projects use modern, maintained dependencies with compatible version ranges. No direct conflicts. Python 3.11+ and Node 18+ (via Bun) are compatible runtime baselines.

---

## 1. BACKEND DEPENDENCIES (`class-fund-backend-v0.1/class-fund-backend/pyproject.toml`)

### Runtime Dependencies
| Package | Version | Purpose | Compatibility |
|---------|---------|---------|---------------|
| `fastapi` | `>=0.116,<1.0` | Web framework | ✅ Current 0.116+ |
| `uvicorn[standard]` | `>=0.35,<1.0` | ASGI server | ✅ |
| `sqlalchemy` | `>=2.0,<3.0` | ORM 2.x | ✅ Modern |
| `psycopg[binary]` | `>=3.2,<4.0` | PostgreSQL driver | ✅ psycopg3 |
| `alembic` | `>=1.16,<2.0` | Migrations | ✅ |
| `pydantic-settings` | `>=2.10,<3.0` | Config management | ✅ Pydantic v2 |
| `PyJWT` | `>=2.10,<3.0` | JWT tokens | ✅ |
| `argon2-cffi` | `>=25.1,<26.0` | Password hashing | ✅ Modern |
| `python-multipart` | `>=0.0.20,<1.0` | Form data parsing | ✅ |
| `email-validator` | `>=2.2,<3.0` | Email validation | ✅ |

### Dev Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `httpx` | `>=0.28,<1.0` | Async HTTP client (testing) |
| `pytest` | `>=8.4,<9.0` | Testing framework |
| `pytest-asyncio` | `>=1.1,<2.0` | Async test support |

### Python Version
- **Requires**: `>=3.11` (from `pyproject.toml`)
- **Features Used**: `StrEnum` (3.11+), `tomllib` (3.11+), pattern matching not used

---

## 2. FRONTEND DEPENDENCIES (`classfund/classfund/package.json`)

### Runtime Dependencies
| Package | Version | Purpose | Compatibility |
|---------|---------|---------|---------------|
| `react` | `^19.0.1` | UI framework | ✅ React 19 |
| `react-dom` | `^19.0.1` | DOM renderer | ✅ |
| `vite` | `^8.3.0` | Build tool | ✅ Vite 8 |
| `@vitejs/plugin-react` | `^6.1.1` | React plugin | ✅ |
| `tailwindcss` | `^4.3.3` | CSS framework | ⚠️ v4 (beta) |
| `@tailwindcss/vite` | `^4.3.3` | Vite integration | ⚠️ v4 |
| `typescript` | `^7.0.2` | Type checking | ✅ TS 7 |
| `lucide-react` | `^0.546.0` | Icons | ✅ |
| `motion` | `^12.23.24` | Animations | ✅ Framer Motion |
| `@ybouane/liquidglass` | `^1.0.3` | Glass morphism | ✅ |
| `@google/genai` | `^2.4.0` | Gemini AI | ✅ (unused in current code) |
| `dotenv` | `^17.2.3` | Env loading | ✅ |
| `express` | `^4.21.2` | Server (dev only?) | ✅ |
| `html-to-image` | `^1.11.13` | Export | ✅ |
| `three` | `^0.186.1` | 3D (unused?) | ✅ |
| `@types/three` | `^0.186.0` | Types | ✅ |

### Dev Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `@types/node` | `^22.14.0` | Node types |
| `@types/react` | `^19.3.0` | React types |
| `@types/react-dom` | `^19.3.0` | React DOM types |
| `autoprefixer` | `^10.4.21` | CSS prefixes |
| `esbuild` | `^0.25.0` | Bundler |
| `tsx` | `^4.21.0` | TypeScript executor |
| `@types/express` | `^4.17.21` | Express types |

### Package Manager
- **Bun** (evidenced by `bun.lock`)
- **Node Version**: Implied `>=18` (Bun requirement)

---

## 3. AI DEPENDENCIES (`pyproject.toml` at project root)

### Runtime Dependencies
| Package | Version | Purpose | Compatibility |
|---------|---------|---------|---------------|
| `pydantic` | `>=2.8.0` | Data validation | ✅ v2 |
| `pydantic-settings` | `>=2.4.0` | Config | ✅ |
| `opencv-python` | `>=4.10.0` | Image processing | ✅ |
| `pillow` | `>=10.4.0` | Image I/O | ✅ |
| `numpy` | `>=2.0.0` | Numerical | ✅ |
| `pytesseract` | `>=0.3.10` | OCR wrapper | ✅ |
| `rapidfuzz` | `>=3.10.0` | Fuzzy matching | ✅ |
| `imagehash` | `>=4.3.1` | Perceptual hash | ✅ |
| `structlog` | `>=25.1.0` | Structured logging | ✅ |
| `redis` | `>=5.0.0` | Redis client | ✅ |
| `celery` | `>=5.4.0` | Task queue | ✅ |
| `python-dotenv` | `>=1.0.0` | Env loading | ✅ |
| `httpx` | `>=0.27.0` | HTTP client | ✅ |
| `tenacity` | `>=8.4.0` | Retry logic | ✅ |

### Dev Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=8.3.0` | Testing |
| `pytest-asyncio` | `>=0.23.0` | Async tests |
| `pytest-cov` | `>=5.0.0` | Coverage |
| `pytest-mock` | `>=3.14.0` | Mocking |
| `ruff` | `>=0.6.0` | Linting |
| `mypy` | `>=1.11.0` | Type checking |
| `types-requests` | `>=2.32.0` | Requests types |

### Python Version
- **Requires**: `>=3.11` (from `pyproject.toml`)

---

## 4. RUNTIME COMPATIBILITY MATRIX

| Aspect | Backend | AI | Frontend | Compatible |
|--------|---------|-----|----------|------------|
| **Python Version** | 3.11+ | 3.11+ | N/A | ✅ |
| **Node/Bun Version** | N/A | N/A | Bun (Node 18+) | ✅ |
| **PostgreSQL** | 15+ (docker) | N/A | Supabase 15+ | ✅ |
| **Redis** | N/A | 7+ (Celery) | N/A | ✅ |
| **Ollama** | N/A | 0.35+ | N/A | ✅ |
| **Tesseract** | N/A | 5.x (system) | N/A | ✅ |

### Version Conflicts: **NONE FOUND**

All version ranges are compatible and non-overlapping.

---

## 5. SYSTEM DEPENDENCIES (External)

### Backend
- **PostgreSQL 15+** — Docker image `postgres:17-alpine` in docker-compose
- **No other system deps** — psycopg[binary] includes libpq

### AI/OCR
- **Tesseract OCR** — System package `tesseract-ocr` + `tesseract-ocr-vie` (Vietnamese)
- **OpenCV** — `opencv-python` wheels include binaries
- **Ollama** — Local service `http://127.0.0.1:11434`

### Frontend
- **Bun** — JavaScript runtime + package manager
- **No system deps** — All npm packages

---

## 6. DEPLOYMENT COMPATIBILITY

### Backend Deployment Options
| Target | Compatible | Notes |
|--------|------------|-------|
| Docker (docker-compose) | ✅ | Provided |
| Bare metal (uvicorn) | ✅ | Standard |
| Kubernetes | ✅ | Stateless |
| Cloud Run / Fly.io | ✅ | Container-based |

### Frontend Deployment Options
| Target | Compatible | Notes |
|--------|------------|-------|
| Vercel | ✅ | SPA, static build |
| Netlify | ✅ | SPA |
| Cloudflare Pages | ✅ | SPA |
| Docker (nginx) | ✅ | Multi-stage build |

### AI Worker Deployment
| Target | Compatible | Notes |
|--------|------------|-------|
| Windows (local) | ✅ | Target platform |
| Linux (Docker) | ✅ | If Redis available |
| systemd/NSSM service | ✅ | Auto-restart |

---

## 6. LOCK FILES

| Project | Lock File | Manager |
|---------|-----------|---------|
| Backend | None (pyproject.toml only) | pip/uv |
| AI | None (pyproject.toml only) | pip/uv |
| Frontend | `bun.lock` | Bun |

**Note**: Backend and AI use `pyproject.toml` without lock files — recommend `pip-tools` or `uv lock` for reproducible builds.

---

## 7. SECURITY SCANNING (Potential)

### High-Profile Dependencies
| Package | CVE Risk | Mitigation |
|---------|----------|------------|
| `PyJWT` | Low | Keep updated |
| `argon2-cffi` | Low | Keep updated |
| `celery` | Medium (historical) | Use latest 5.4+ |
| `redis` | Low | Keep updated |
| `opencv-python` | Low | Binary wheels |
| `react` | Low | Auto-updates via Vercel |

### Recommendation
Run `pip-audit` / `bun audit` before production deployment.

---

## 8. BUILD & TEST COMMANDS

### Backend
```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest

# Lint (if ruff added)
ruff check .

# Type check (if mypy added)
mypy app/

# Run server
uvicorn app.main:app --reload

# Migrations
alembic upgrade head
```

### AI
```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest ai/tests/

# Lint
ruff check ai/

# Type check
mypy ai/
```

### Frontend
```bash
# Install
bun install

# Dev server
bun run dev

# Build
bun run build

# Lint (TypeScript only)
bun run lint

# Preview
bun run preview
```

---

## 9. COMPATIBILITY VERDICT

| Check | Result |
|-------|--------|
| Python version alignment | ✅ Both 3.11+ |
| Dependency version conflicts | ✅ None |
| PostgreSQL driver compatibility | ✅ psycopg3 |
| Redis client compatibility | ✅ redis-py 5.x |
| Celery compatibility | ✅ 5.4+ |
| Tesseract system dependency | ✅ Documented |
| Ollama API compatibility | ✅ Standard /api/chat |
| Frontend build tool | ✅ Vite 8 |
| Package manager | ✅ Bun |
| TypeScript version | ✅ 7.x |

**Overall: FULLY COMPATIBLE**

---

## 10. CONFIDENCE ASSESSMENT

- **Verified**: All `pyproject.toml` and `package.json` files read directly
- **Verified**: `ollama --version` and `ollama list` executed
- **Partially Verified**: Tesseract system installation (assumed available)
- **Assumed**: Bun version compatibility with React 19
- **Not Verified**: Actual `pip install` / `bun install` execution, test runs