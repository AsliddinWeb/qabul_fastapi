# Xalqaro Innovatsion Universiteti — Qabul Tizimi

University admission (qabul) platform: phone+OTP auth, applicant onboarding, dynamic programs, contract generation, role-based dashboards.

**Stack:** FastAPI · PostgreSQL · Redis · Vue 3 SPA · Nuxt 3 (landing SSR) · Tailwind · Nginx · Docker.

> 🔗 **CRM is a separate system.** This service only **sends** lead/applicant events to an external CRM via HTTP — it does **not** implement CRM features internally. See `backend/app/integrations/crm/`.

---

## Quick start

```bash
# 1. Configure environment
make init                  # creates .env from .env.example
$EDITOR .env               # set Eskiz creds, DB password, secret key

# 2. Build & run
make up                    # production stack on http://localhost:8031

# 3. Initialize database
make migrate               # apply migrations
make seed                  # seed dictionaries (regions, doc types, ...)
make seed-templates        # seed 2-party + 3-party contract templates
make superadmin            # create initial SuperAdmin user
```

URLs (production stack):

| Path | Served by |
|---|---|
| `http://localhost:8031/` | **Nuxt landing** (SSR, SEO) |
| `http://localhost:8031/app/` | **Vue SPA** (auth + dashboards) |
| `http://localhost:8031/api/v1/docs` | FastAPI Swagger |
| `http://localhost:8031/healthz` | Backend health check |

## Development (hot reload)

```bash
make dev                   # backend + Vite + Nuxt dev servers
```

- Backend:     http://localhost:8031/api/v1
- Vue SPA dev: http://localhost:5173/app/
- Nuxt dev:    http://localhost:3000
- Postgres:    localhost:5433
- Redis:       localhost:6380

## Project layout

```
admission_system/
├── backend/        # FastAPI (modular monolith, clean architecture)
│   └── app/integrations/crm/   # CRM client (no CRM logic — only API calls)
├── frontend/       # Vue 3 SPA — mounted at /app/
├── landing/        # Nuxt 3 SSR — served at /
├── deploy/         # nginx, postgres init
├── docker-compose.yml
├── docker-compose.dev.yml
└── Makefile
```

See `backend/` and `frontend/` READMEs for module-level details.

## Roles

SuperAdmin · Admin · Operator · Director · Accountant · Applicant

## Common tasks

| Task | Command |
|---|---|
| Start prod | `make up` |
| Stop | `make down` |
| Logs | `make logs` |
| New migration | `make makemigration m="add_x"` |
| Apply migrations | `make migrate` |
| Backend shell | `make backend-shell` |
| DB shell | `make db-shell` |
| Reset everything | `make clean` |

## CRM integration ops

CRM events go through a Redis-backed retry queue. The backend launches a
worker on startup that drains the queue with exponential backoff.

| Concern | Behavior |
|---|---|
| Initial delivery | Enqueued during request, drained by worker (poll: 5s) |
| Retry policy | 1m → 2m → 4m → 8m → 16m → 30m (6 retries) |
| Terminal failure | Moved to DLQ for manual recovery |
| CRM disabled (no creds) | Entries park in pending; worker reschedules without sending |

Inspect & manage (requires `integrations.admin` permission — SuperAdmin/Admin):

```bash
GET    /api/v1/integrations/crm/stats              # {pending, dlq}
GET    /api/v1/integrations/crm/pending?limit=50
GET    /api/v1/integrations/crm/dlq?limit=100
POST   /api/v1/integrations/crm/dlq/{id}/retry
DELETE /api/v1/integrations/crm/dlq/{id}
```

Configure via `.env`:

```
CRM_BASE_URL=https://crm.example.com/api
CRM_API_KEY=...
CRM_TIMEOUT_SECONDS=10
CRM_WORKER_POLL_SECONDS=5
```
