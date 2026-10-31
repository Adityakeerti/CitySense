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
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | public / any | JWT auth; self-registration is always an **unverified** CITIZEN and emails a code |
| `POST /api/auth/otp/send`, `POST /api/auth/otp/verify` | public | 4-digit email code → verified token (JWT claim `ev=true`) |
| `POST /api/auth/password/forgot`, `POST /api/auth/password/reset` | public | Reset password with an emailed code |
| `GET /api/geo/config`, `GET /api/geo/style.json`, `GET /api/geo/tiles/{z}/{x}/{y}.png` | public | Map defaults + MapLibre style whose raster tiles are proxied (and cached) by core |
| `GET /api/geo/geocode?q`, `GET /api/geo/reverse?lat&lng`, `GET /api/geo/route?from…&to…` | any | Nominatim search / reverse and OSRM routing, proxied |
| `GET /api/avatars?lat&lng&radiusMeters&q`, `GET /api/avatars/{id}`, `GET /api/avatars/saved` | verified | City-service avatars on the Explore map (PostGIS radius search) |
| `PUT/DELETE /api/avatars/{id}/save`, `PUT/DELETE /api/avatars/{id}/like`, `POST /api/avatars/{id}/chat` | verified | Saves, likes, chat (`intent` INTRO/PRICING/WEBSITE answered from the avatar record; free text → persona) |
| `GET /api/complaints/mine`, `GET /api/complaints/meta` | any / public | The caller's complaints; priorities + escalation ladder labels (config) |
| `POST /api/events`, `GET /api/events` | ADMIN, CREW / any | Inject or list observations |
| `POST /internal/observations`, `POST /internal/actions` | ai-service (`X-Internal-Key`) | Python pushes observations / proposes actions |
| `GET /api/incidents`, `GET /api/incidents/{id}`, `PATCH /api/incidents/{id}/status` | any / any / ADMIN | Ranked incidents, drawer detail, OPEN→ACKNOWLEDGED→RESOLVED |
| `GET /api/actions?status=PENDING`, `POST /api/actions`, `POST /api/actions/{id}/approve`, `.../reject` | ADMIN | Approval queue (reject requires a reason) |
| `GET /api/audit?entityType&entityId` | ADMIN | Append-only audit log |
| `GET /api/scenarios`, `POST /api/scenarios/{rain\|flood\|crash\|congestion}` | ADMIN | Demo injection, all labelled `SIMULATED` |
| `GET /api/map/features` | any | GeoJSON for live map |
| STOMP `/ws` (SockJS: `/ws-sockjs`), topic `/topic/city-events` | — | `{type, entityId, data, timestamp}`; types: `OBSERVATION_CREATED`, `INCIDENT_CREATED/UPDATED`, `ACTION_PENDING/AUTO_EXECUTED/APPROVED/REJECTED` |

## Mobile support (maps, OTP, avatars)

- **Maps never leave the backend.** `GeoService` proxies tiles (`GEO_TILE_URL_TEMPLATE`), geocoding (`GEO_NOMINATIM_URL`) and routing (`GEO_OSRM_URL`) with an LRU cache, an identifying `GEO_USER_AGENT`, and a ≥1.1 s gap between Nominatim calls. Defaults are the public OpenStreetMap servers, which are fine for a demo but have [usage policies](https://operations.osmfoundation.org/policies/) (attribution, no heavy use); point the URLs at self-hosted or paid endpoints for real traffic. Tiles are public because native map SDKs fetch them without a JWT.
- **OTP email** uses Spring's `SPRING_MAIL_HOST/PORT/USERNAME/PASSWORD`. With no host set and `OTP_LOG_FALLBACK=true` (default), codes are printed to the core log for local development. Codes are BCrypt-hashed, single-use, purpose-bound, expire after `OTP_TTL_SECONDS` and lock after `OTP_MAX_ATTEMPTS`; send endpoints answer identically for unknown emails.
- **Avatars** are seeded (upsert by `handle`) from `AVATAR_SEED_LOCATION` (default `classpath:seed/avatars.json`, demo data) when `SEED_AVATARS=true`; images are served from `static/avatars/`. Chat free text goes through `AgentResponder`, the single seam for wiring in `agent_service`.

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

- Avatar chat free text still uses core's keyword `AgentResponder`, not the Python `agent_service` RAG pipeline.
- Tile/geocode caches are in-memory per instance.
- STOMP handshake is unauthenticated (fine for demo; add a JWT `ChannelInterceptor` before any real deployment).
- No Testcontainers integration tests yet; the end-to-end flow was verified manually against the compose stack.
- The `postgis/postgis:16-3.4` base image is amd64-only, so it runs under emulation on Apple Silicon (works, slightly slower).
