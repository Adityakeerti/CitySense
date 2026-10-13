# CitySense (CityOS)

> **One app for everything happening in the city, from fun to fixes.**  
> A coordinated smart-city operating system combining an Expo mobile app (citizens & emergency crews), a React + Vite operations dashboard, a robust Spring Boot 3 core backend, and a specialized Python AI/ML simulation engine.

Repository: [https://github.com/Adityakeerti/CitySense](https://github.com/Adityakeerti/CitySense)  
Complete Implementation Plan: [plan.md](plan.md)

---

## 🏛️ High-Level Architecture

```text
       Mobile (Expo Router)              Admin Dashboard (React + Vite)
             \                                      /
              \             REST + STOMP           /
               v                                  v
    +-------------------------------------------------------------+
    |            SPRING BOOT 3 CORE (Public Gateway)              |  Java 21, Maven
    |  • M1: Platform & Governance  • M2: Multilingual Agent     |  PostgreSQL 16 + PostGIS
    |  • M3: Civic & Escalation     • M4: Intelligent Mobility   |  Spring Security (JWT)
    +-------------------------------------------------------------+
               |  REST (Internal)       ^ POST /internal/observations
               v                        |
    +-------------------------------------------------------------+
    |             PYTHON AI SERVICE (Internal Engine)             |  FastAPI, Python 3.11+
    |  • M2: pgvector RAG + Sarvam STT/TTS + Abstain Policy       |  NetworkX, YOLOv8,
    |  • M4: YOLOv8 Lane Density, SUMO + DQN Reinforcement Learn  |  SUMO + TraCI, PyTorch
    +-------------------------------------------------------------+
```

---

## 👥 Team Breakdown — 4 Feature Modules

Each of the 4 team members has full-stack ownership of their designated domain: a **Spring Boot module**, a **frontend vertical (Mobile + Dashboard)**, and the corresponding **algorithmic/AI engine**.

```
+-------------------------------------------------------------------------------------------------------+
|                                    CITYSENSE FULL-STACK WORKSPACE                                     |
+------------------------------------+------------------------------------+-----------------------------+
| Feature Module                     | Spring Boot Core (`core/`)         | Clients & AI Services       |
+------------------------------------+------------------------------------+-----------------------------+
| M1: Platform & Governance Lead     | com.citysense.platform             | Vite Map, Scenario, Approvals|
| M2: Multilingual Agent & RAG Lead  | com.citysense.agent                | Mobile Ask Tab, Python RAG  |
| M3: Civic Services & Escalation    | com.citysense.civic                | Mobile Explore/Report/Track |
| M4: Mobility & Traffic AI Lead     | com.citysense.mobility             | Mobile Alerts, YOLOv8, SUMO |
+------------------------------------+------------------------------------+-----------------------------+
```

---

### 🛡️ Member A: Platform & Governance Lead
*Lead architect for core reliability, real-time event streaming, and human-in-the-loop governance.*

- **Spring Boot Core:** `core/src/main/java/com/citysense/platform/`
  - JWT Authentication & RBAC (`User`: Citizen, Admin, Emergency Crew).
  - Ingestion engine for universal `Observation` data model (`POST /api/events`, `POST /internal/observations`).
  - Correlation engine: clusters observations into `Incident` objects and ranks urgency.
  - Human oversight: `AgentAction` approval/rejection state machine (`/api/actions`).
  - Append-only `AuditLog` persistence (`/api/audit`).
  - Real-time WebSocket/STOMP infrastructure (`/ws`, `/topic/city-events`).
- **Dashboard UI:** `dashboard/src/features/platform/`
  - Operations live map & active incident drawer.
  - High-impact action **Approval Queue** & audit history inspector.
  - **Scenario Control Panel** (one-click demo injection: rain, flood, crash).
- **Mobile UI:** Global Expo navigation shell, WebSocket listener, global alert toast.
- **Resume Highlight:** *Spring Boot Core Platform + Distributed Event Correlation Engine + Human-in-the-Loop Governance + Real-time WebSocket STOMP.*

---

### 🎙️ Member B: Multilingual City Agent & RAG Lead
*Lead engineer for the citizen-facing hero feature: conversational AI with verified citations and speech.*

- **Spring Boot Core:** `core/src/main/java/com/citysense/agent/`
  - Agent gateway controller (`POST /api/agent/chat`, `POST /api/agent/voice`).
  - Chat session management & tool-execution bridge (executing read-only queries for complaints/events).
  - Knowledge docs CRUD (`POST /api/knowledge/docs`).
  - Circuit breakers & cached fallbacks via **Resilience4j**.
- **Python AI Service:** `ai-service/app/agent/`
  - RAG engine on PostgreSQL `pgvector` (`ai` schema).
  - Strict **Abstain Policy**: triggers clear fallback when similarity < threshold.
  - Multilingual voice pipeline: Sarvam AI STT, TTS, and translation (Hindi, English, etc.).
  - Specialist personas (Civic, Traffic, Emergency, Transit).
- **Mobile UI:** `mobile/app/(tabs)/ask.tsx`
  - **Ask Tab (Hero feature):** voice recording waveform, text chat, live streaming, source citation pills (`sources[]`), abstain CTA modal.
- **Dashboard UI:** `dashboard/src/features/agent/`
  - Knowledge Base Manager (upload documents, vector indexing, verification badges).
  - Agent live activity & confidence metrics panel.
- **Resume Highlight:** *Enterprise RAG Architecture (pgvector) + Strict Abstain Guardrails + Multilingual Voice Agent (Sarvam AI) + Spring Resilience4j Gateway.*

---

### 📋 Member C: Civic Services & Automated Escalation Lead
*Lead engineer for citizen issue resolution, spatial awareness, and automated departmental escalation.*

- **Spring Boot Core:** `core/src/main/java/com/citysense/civic/`
  - Complaints workflow (`POST /api/complaints`, `GET /api/complaints/{trackingId}`).
  - Image storage adapter & unique tracking ID generator.
  - Automated multi-tier **Escalation Scheduler** (Spring `@Scheduled` state machine with `ESCALATION_TICK_SECONDS` demo acceleration):
    `Filed -> Worker Assigned -> Warnings 1-5 -> Ward Officer -> Municipal Commissioner -> CM Portal`.
  - City Events CRUD (`/api/city-events`).
  - Geofence calculation service via PostGIS spatial distance queries (`ST_DWithin`).
- **Mobile UI:** `mobile/app/(tabs)/`
  - `index.tsx` (**Explore Tab**): live map and events feed, category filters, "Near Me" geofence cards.
  - `report.tsx` (**Report Tab**): complaint form with photo capture/upload, category selector, GPS picker.
  - `track.tsx` (**Track Tab**): interactive complaint escalation ladder visualizer with milestone markers.
- **Dashboard UI:** `dashboard/src/features/civic/`
  - Complaints Board (Kanban & tabular views, assignment, SLA countdowns, fast-forward demo trigger).
  - City Events CRUD publisher.
- **Resume Highlight:** *Automated State Machine & Escalation Scheduler (Spring Scheduler) + Spatial PostGIS Geofencing + Citizen Civic Workflow.*

---

### 🚦 Member D: Intelligent Mobility & Emergency Routing Lead
*Lead engineer for computer vision traffic telemetry, adaptive signal control, and emergency transit.*

- **Spring Boot Core:** `core/src/main/java/com/citysense/mobility/`
  - Emergency route API (`POST /api/emergency/routes`, `POST /api/emergency/reassess`).
  - Green corridor proposal generator (signal timing windows sent to approval queue).
  - Traffic telemetry & junction status API (`/api/traffic/junctions`, `/api/traffic/rl-report`).
- **Python AI Service:**
  - `ai-service/app/cv/`: YOLOv8 lane grid-occupancy density from video frames, pushing to Spring Boot `/internal/observations`.
  - `ai-service/app/routing/`: NetworkX time-dependent road graph (arrival-time estimation, committed route hysteresis, minimum dwell time to eliminate route flutter).
  - `ai-service/app/rl/`: SUMO traffic simulator with TraCI interface; DQN signal control policy training and replay vs. fixed-time baseline.
- **Mobile UI:** `mobile/app/(tabs)/alerts.tsx`
  - **Alerts / Crew Mode Tab**: emergency vehicle crew view (active route polyline, predicted segment ETAs, reroute rationale badges), citizen "Clear the Lane" green corridor alerts.
- **Dashboard UI:** `dashboard/src/features/mobility/`
  - Traffic & Mobility panel (YOLO camera feeds with density grid overlay, junction signal states, DQN vs. fixed-time delay charts).
- **Resume Highlight:** *Computer Vision Traffic Telemetry (YOLOv8) + Reinforcement Learning Traffic Optimization (SUMO + DQN) + Hysteresis-Stabilized Emergency Routing.*

---

## 📂 Repository Layout

```text
CitySense/
├── README.md                           # Team onboarding & project architecture
├── plan.md                             # 14-day master engineering plan
├── docker-compose.yml                  # Local development orchestration
├── .env.example                        # Required environment variables
│
├── contracts/                          # Contract-first OpenAPI specs & schemas
│   ├── openapi-public.yaml             # Spring Boot public API spec
│   ├── openapi-internal.yaml           # FastAPI internal AI service spec
│   └── event.schema.json               # Canonical Observation JSON schema
│
├── core/                               # [M1-M4] Spring Boot 3 Core Backend (Java 21)
│   ├── pom.xml                         # Maven dependencies & plugins
│   ├── src/main/java/com/citysense/
│   │   ├── platform/                   # [M1: Member A] Core platform, auth, coordinator, audit, WS
│   │   ├── agent/                      # [M2: Member B] Agent gateway, knowledge CRUD, tool bridge
│   │   ├── civic/                      # [M3: Member C] Events, complaints, escalation, geofence
│   │   ├── mobility/                   # [M4: Member D] Routes API, traffic telemetry, green corridor
│   │   └── common/                     # Cross-cutting: security, errors, fallback cache adapters
│   └── src/main/resources/
│       ├── application.yml
│       └── db/migration/               # Flyway SQL migrations (V1-V4)
│
├── ai-service/                         # [M2, M4] Python FastAPI Microservice (Python 3.11+)
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                     # Internal FastAPI server
│   │   ├── agent/                      # [M2: Member B] RAG, pgvector, Sarvam STT/TTS, abstain policy
│   │   ├── cv/                         # [M4: Member D] YOLOv8 lane occupancy detection
│   │   ├── routing/                    # [M4: Member D] NetworkX road graph & hysteresis engine
│   │   └── rl/                         # [M4: Member D] SUMO + TraCI DQN reinforcement learning
│   └── tests/
│
├── mobile/                             # [M1-M4] Citizen & Crew Mobile App (React Native + Expo)
│   ├── package.json
│   ├── app/
│   │   ├── _layout.tsx                 # [M1] Root shell & navigation
│   │   └── (tabs)/
│   │       ├── index.tsx               # [M3] Explore Tab (Map & Feed)
│   │       ├── ask.tsx                 # [M2] Ask Tab (Hero Multilingual Agent)
│   │       ├── report.tsx              # [M3] Report Tab (Complaints with Photo)
│   │       ├── track.tsx               # [M3] Track Tab (Escalation Timeline)
│   │       └── alerts.tsx              # [M4] Alerts Tab (Crew Route & Green Corridor)
│
└── dashboard/                          # [M1-M4] Municipal Operations Dashboard (React + Vite)
    ├── package.json
    └── src/
        ├── features/
        │   ├── platform/               # [M1] Live map, Scenario Injector, Approval Queue, Audit Log
        │   ├── agent/                  # [M2] Knowledge Base Manager, Agent Monitor
        │   ├── civic/                  # [M3] Complaints Board, Events Publisher
        │   └── mobility/               # [M4] Traffic Telemetry, YOLO Feed, RL Signal Chart
```

---

## ⚡ Ground Rules & Collaboration Protocol

1. **Contracts Before Code:** Spring Boot is the single public gateway. All frontend clients use types generated from `openapi-public.yaml`. Spring calls Python via types from `openapi-internal.yaml`.
2. **Flyway Migrations:** Member A owns `V1__platform.sql`. Each teammate adds their modular migration (`V2__agent.sql`, `V3__civic.sql`, `V4__mobility.sql`).
3. **Hard Gate (Day 4):** Member A delivers the Spring Boot spine with database, auth, and STOMP event bus. Teammates must connect their stubs and UI to this spine by Day 4.
4. **Resilience & Demo Mode:** Every external dependency (Sarvam, LLM, YOLO video, SUMO) must have a cached/fallback adapter. `DEMO_MODE=1` must execute the entire 5-minute demo cleanly without internet access.

---

## 🚀 Quick Start (Development)

### 1. Prerequisites
- **Java 21 (JDK)** & **Maven 3.9+**
- **Python 3.11+** & `pip`
- **Node.js 20+** & `npm` / `pnpm`
- **Docker & Docker Compose**

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your database credentials and optional API keys (SARVAM_KEY, LLM_KEY)
```

### 3. Launch Services with Docker Compose
```bash
docker compose up -d postgres-postgis
# Start the full stack or individual components as documented in plan.md
```

For complete technical specifications, API contracts, entity schemas, and day-by-day schedules, refer to [plan.md](plan.md).
