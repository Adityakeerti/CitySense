# CitySense Core — Platform module (Member A)

Spring Boot 3 / Java 21 gateway. The `platform` package is the spine the other modules plug into.

## Run

```bash
docker compose up -d postgres-postgis          # DB only (PostGIS + pgvector)
docker compose --profile app up -d --build     # DB + core on :8080
```

No local JDK needed (the image builds with Maven + Temurin 21). Tests: 

```bash
docker run --rm -v "$PWD/core":/app -v citysense-m2:/root/.m2 -w /app maven:3.9-eclipse-temurin-21 mvn -B test
```

Swagger UI: http://localhost:8080/swagger-ui.html · contract: `contracts/openapi-public.yaml`

Dev users (seeded at startup when `SEED_USERS=true`, password `citysense123`):
`admin@citysense.dev` (ADMIN), `crew@citysense.dev` (CREW), `citizen@citysense.dev` (CITIZEN).

## Endpoints

| Endpoint | Who | Purpose |
|---|---|---|
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | public / any | JWT auth; self-registration is always CITIZEN |
| `POST /api/events`, `GET /api/events` | ADMIN, CREW / any | Inject or list observations |
| `POST /internal/observations`, `POST /internal/actions` | ai-service (`X-Internal-Key`) | Python pushes observations / proposes actions |
| `GET /api/incidents`, `GET /api/incidents/{id}`, `PATCH /api/incidents/{id}/status` | any / any / ADMIN | Ranked incidents, drawer detail, OPEN→ACKNOWLEDGED→RESOLVED |
| `GET /api/actions?status=PENDING`, `POST /api/actions`, `POST /api/actions/{id}/approve`, `.../reject` | ADMIN | Approval queue (reject requires a reason) |
| `GET /api/audit?entityType&entityId` | ADMIN | Append-only audit log |
| `GET /api/scenarios`, `POST /api/scenarios/{rain\|flood\|crash\|congestion}` | ADMIN | Demo injection, all labelled `SIMULATED` |
| `GET /api/map/features` | any | GeoJSON for live map |
| STOMP `/ws` (SockJS: `/ws-sockjs`), topic `/topic/city-events` | — | `{type, entityId, data, timestamp}`; types: `OBSERVATION_CREATED`, `INCIDENT_CREATED/UPDATED`, `ACTION_PENDING/AUTO_EXECUTED/APPROVED/REJECTED` |

## How the pieces fit

`ObservationService.ingest` → `CorrelationEngine` (PostGIS `ST_DWithin` within `CORRELATION_RADIUS_METERS`, incident touched within `CORRELATION_WINDOW_MINUTES`) → score severity/urgency → `CoordinatorRules` propose `AgentAction`s → audit + broadcast **after commit**.

- `event` observations and `cv_density` below 0.7 are stored but never raise incidents.
- Each `ActionType` has a minimum risk; proposers can raise, never lower it. Only LOW risk auto-executes; everything else stays `PENDING` until an admin decides. Decisions are terminal and guarded by optimistic locking.
- `audit_log` rejects UPDATE/DELETE/TRUNCATE at the DB level (trigger).

## For teammates (B, C, D)

- Add your tables as `V2__agent.sql`, `V3__civic.sql`, `V4__mobility.sql` in `src/main/resources/db/migration/`. Never edit V1. The `ai` schema and `vector` extension already exist.
- Propose high-impact actions (e.g. green corridor) by injecting `AgentActionService` and calling `propose(...)`; don't build a separate approval flow.
- Audit from your services with `AuditService.record(...)` inside a `@Transactional` method (it requires one).
- Broadcast with `ApplicationEventPublisher.publishEvent(CityEventMessage.of(type, id, data))`.

## Known limits

- STOMP handshake is unauthenticated (fine for demo; add a JWT `ChannelInterceptor` before any real deployment).
- No Testcontainers integration tests yet; the end-to-end flow was verified manually against the compose stack.
- The `postgis/postgis:16-3.4` base image is amd64-only, so it runs under emulation on Apple Silicon (works, slightly slower).
