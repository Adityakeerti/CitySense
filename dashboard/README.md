# CitySense Operations Dashboard (React + Vite)

Operator dashboard for everything happening in the CitySense digital twin city, built from
`docs/dashboard.jpeg`. It replaces the single-file `UI.html` pages (now in `../residuals/`).

```bash
cd dashboard
npm install
npm run dev          # http://localhost:5173  (or ../run_backends.sh start)
npm run build        # static bundle in dist/
```

## Pages

| Page | What it shows | Source |
|---|---|---|
| **Dashboard** | 3D city (MapLibre + deck.gl) on real streets: the corridor is drawn along Rajpur-Mussoorie Road from OpenStreetMap; road paint shows cell speed; individual 3D cars come from CTM densities (flowing at cell speed, queuing at red stop lines); agent **car clusters** are coloured cars with fading trails tracing the path they drove; **people** walk real footpaths from their neighbourhood tower to their cars; red/green stop bars and signal poles per approach. Camera: Overview, Street level, Follow a car cluster (chase cam with a card listing each junction wait and the RL decision that released it). Notch tabs: 3D City / Satellite / Time-space. Deep links: `?cam=street`, `?cam=follow`. KPI row, 4 query tiles, City Activity timeline. | twin WS `/api/twin/stream`, `/api/city/*` |
| **Policy Lab** | RL exploration made visible: ε now and its per-episode schedule, observed random-action rate, replay size, updates, TD loss; learning curves per episode vs the 3 baselines; live per-policy table; decision stream (explore / exploit / shield) with Q-values, gradient×input attributions and **Explain with Gemma**; time-space diagram; car clusters with the decision id that released them at each junction; episode history. | twin |
| **Residents** | Each people-cluster LangGraph agent: persona, latest plan and reason, memory with realised delays, LLM-vs-fallback counts, and the node-by-node trace (prompt and raw model output). | `/api/city/*` |
| **TownHall** | Complaint feed and SLA escalation state. | complaint module |
| **Tickets** | Emergency missions and CCTV incidents. | emergency routing |
| **Messages** | Voice-agent event log (needs agent `DEMO_MODE=1` for the admin dev token). | agent service |

## Routing

All requests use relative URLs that match the production Caddy routes; `vite.config.js` proxies them in
development (override targets with `TWIN_URL`, `CITY_SIM_URL`, `AGENT_URL`, `COMPLAINT_URL`, `EMERGENCY_URL`).

| Prefix | Service | Port |
|---|---|---|
| `/api/twin/*` (incl. WebSocket `/api/twin/stream`) | live digital twin (CITY SENSE RL repo) | 8003 |
| `/api/city/*` | population simulator (`../city_sim`) | 8004 |
| `/api/complaint-flow/*` → `/api/*` | complaint module | 8001 |
| `/api/emergency/*` → `/api/*` | emergency routing | 8002 |
| `/api/agent/*`, `/agent/*` (prefix stripped) | agent service | 8000 |

The Caddyfile does not yet route `/api/twin/*` or `/api/city/*`, and docker-compose has no twin or
population service (the twin lives in a separate repo). Add those before deploying the dashboard
behind Caddy.

## Map data

* Basemap and 3D buildings: [OpenFreeMap](https://openfreemap.org) vector tiles (OpenMapTiles schema, © OpenStreetMap contributors); satellite mode uses Esri World Imagery. No API key needed; tiles load from the internet.
* Corridor geometry is cached in the RL repo (`config/street_geometry.json`, built by `scripts/build_street_geometry.py`); walking paths are cached in `city_sim/data/walk_paths.json`. Both come from the public OSRM routers once, then work offline.
* The CTM is 1-D: each link is drawn along the real segment between two real intersections, so drawn length differs from simulated length (0.8–1.9×, shown on the map). Car positions are exact along the link; visual speeds scale with that factor.
* Background cars are a visual rendering of CTM cell densities (no identities); only agent car clusters are tracked vehicles.

## Colour and accessibility notes

Policy series use the validated 4-slot categorical palette (dataviz reference: blue, orange, aqua, yellow;
adjacent CVD ΔE ≥ 9). Aqua and yellow sit below 3:1 contrast on the light surface, so lines carry direct
end labels and every chart has a table view (episode history, per-policy table). Traffic state on the
map uses the status colours, always with a legend. The heatmap uses a single-hue sequential ramp.
