"""FastAPI Backend Server bridging UI Dashboard to LangGraph Emergency Agent."""

import os
import base64
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from services.hospital_service import HospitalService
from routing.predictive_router import PredictiveRouter
from agents.ambulance_agent import AmbulanceAgent
from agents.feud_tracker import FeudTracker
from agents.police_interface import MockPoliceAgent
from agents.emergency_agent import EmergencyAgent
from models.llm_classifier import LLMClassifier
from models.vision_llm import VisionLLM
from models.vision_pipeline import VisionPipeline, CameraMetadata
from simulation.synthetic_scenarios import (
    build_demo_city_network,
    get_scenario_accident_clearing_jam,
    get_scenario_accident_persistent_jam,
    get_scenario_feud_timeline,
)

app = FastAPI(title="Emergency Agent OS Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core Component Initialization ─────────────────────────────────────────────
graph, history = build_demo_city_network()
hospital_service = HospitalService()
router = PredictiveRouter(graph=graph, history_db=history)
ambulance_agent = AmbulanceAgent(hospital_service=hospital_service, predictive_router=router)
police_agent = MockPoliceAgent()
feud_tracker = FeudTracker(min_duration_sec=settings.FEUD_MIN_DURATION_SECONDS)
llm_classifier = LLMClassifier()
vision_llm = VisionLLM()
vision_pipeline = VisionPipeline()

emergency_agent = EmergencyAgent(
    ambulance_agent=ambulance_agent,
    police_agent=police_agent,
    feud_tracker=feud_tracker,
    llm_classifier=llm_classifier,
    vision_llm=vision_llm,
)

BASE_DIR = Path(__file__).parent.resolve()
SAMPLE_VIDEOS_DIR = BASE_DIR / "data" / "sample_videos"
SAMPLE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/videos", StaticFiles(directory=str(SAMPLE_VIDEOS_DIR)), name="videos")


# ── UI ─────────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    ui_path = BASE_DIR / "ui.html"
    if ui_path.exists():
        return ui_path.read_text(encoding="utf-8")
    return "<h1>ui.html not found</h1>"


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "version": "2.0.0",
        "orchestrator": "LangGraph StateGraph",
        "active_hospitals": len(hospital_service.hospitals),
        "tracked_cameras": len(feud_tracker.tracked_cameras),
        "llm_enabled": True,
        "vision_enabled": True,
        "llm_primary_model": settings.LLM_CLASSIFIER_PRIMARY,
        "vision_primary_model": settings.VISION_PRIMARY_MODEL,
        "vision_primary_provider": settings.VISION_PRIMARY_PROVIDER,
    }


# ── Model Status ───────────────────────────────────────────────────────────────
@app.get("/api/model-status")
def model_status():
    """Returns the confirmed-working free model lineup from live checks."""
    return {
        "vision_models": [
            {
                "model": "gemma4:31b",
                "provider": "Ollama Cloud",
                "status": "FREE + VISION",
                "priority": 1,
                "confirmed": True,
            },
            {
                "model": "gemma4:31b-cloud",
                "provider": "Ollama Cloud",
                "status": "FREE + VISION",
                "priority": 2,
                "confirmed": True,
            },
            {
                "model": "qwen/qwen3.8-27b",
                "provider": "Groq",
                "status": "FREE + VISION",
                "priority": 3,
                "confirmed": True,
            },
        ],
        "text_models": [
            {"model": "openai/gpt-oss-120b", "provider": "Groq", "status": "FREE", "priority": 1},
            {"model": "openai/gpt-oss-20b", "provider": "Groq", "status": "FREE", "priority": 2},
            {"model": "nemotron-3-ultra", "provider": "Ollama Cloud", "status": "FREE", "priority": 3},
            {"model": "nemotron-3-super", "provider": "Ollama Cloud", "status": "FREE", "priority": 4},
            {"model": "gpt-oss:120b", "provider": "Ollama Cloud", "status": "FREE", "priority": 5},
        ],
        "last_checked": "2026-10-30T21:34:00+05:30",
    }


# ── Scenario Runner ────────────────────────────────────────────────────────────
@app.get("/api/run-scenario/{scenario_name}")
def run_scenario(scenario_name: str):
    """Triggers full LangGraph + LLM orchestration on selected scenario."""
    if scenario_name == "accident-clearing-jam":
        incident, g, h = get_scenario_accident_clearing_jam()
        temp_router = PredictiveRouter(graph=g, history_db=h)
        temp_amb = AmbulanceAgent(hospital_service=hospital_service, predictive_router=temp_router)
        agent = EmergencyAgent(
            ambulance_agent=temp_amb, police_agent=police_agent,
            llm_classifier=llm_classifier, vision_llm=vision_llm,
        )
        state = agent.process_incident(incident)
        return state.model_dump()

    elif scenario_name == "accident-persistent-jam":
        incident, g, h = get_scenario_accident_persistent_jam()
        temp_router = PredictiveRouter(graph=g, history_db=h)
        temp_amb = AmbulanceAgent(hospital_service=hospital_service, predictive_router=temp_router)
        agent = EmergencyAgent(
            ambulance_agent=temp_amb, police_agent=police_agent,
            llm_classifier=llm_classifier, vision_llm=vision_llm,
        )
        state = agent.process_incident(incident)
        return state.model_dump()

    elif scenario_name == "feud":
        events = get_scenario_feud_timeline()
        results = []
        tracker = FeudTracker(min_duration_sec=settings.FEUD_MIN_DURATION_SECONDS)
        agent = EmergencyAgent(
            ambulance_agent=ambulance_agent,
            police_agent=police_agent,
            feud_tracker=tracker,
            llm_classifier=llm_classifier,
            vision_llm=vision_llm,
        )
        for ev in events:
            st = agent.process_incident(ev)
            results.append(st.model_dump())
        return {"timeline_results": results}

    raise HTTPException(status_code=404, detail="Scenario not found. Valid: accident-clearing-jam, accident-persistent-jam, feud")


# ── Video Stream Ingestion & Processing ────────────────────────────────────────
@app.get("/api/process-video/{video_name}")
@app.post("/api/process-video/{video_name}")
def process_video_feed(video_name: str):
    """Processes a CCTV sample video from data/sample_videos.
    Extracts frames via OpenCV, passes key frame to Vision LLM (Ollama Gemma / Groq Qwen),
    and executes the full LangGraph Emergency Agent pipeline.
    """
    video_path = SAMPLE_VIDEOS_DIR / video_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample video '{video_name}' not found in {SAMPLE_VIDEOS_DIR}")

    incident, frame_b64, video_meta = vision_pipeline.process_video_file(str(video_path))
    state = emergency_agent.process_incident(incident)

    return {
        "video_name": video_name,
        "video_url": f"/videos/{video_name}",
        "video_meta": video_meta,
        "frame_b64": frame_b64,
        "state": state.model_dump(),
    }


# ── Image Analysis Endpoint ────────────────────────────────────────────────────
class ImageAnalysisRequest(BaseModel):
    image_b64: Optional[str] = None
    cv_context: Optional[str] = None   # For text-only mode
    incident_type: str = "UNKNOWN"
    confidence: float = 0.5
    severity: float = 0.5
    address: str = "Unknown Location"
    camera_id: str = "CAM-UPLOAD"


@app.post("/api/analyze-image")
async def analyze_image(request: ImageAnalysisRequest):
    """Runs vision LLM analysis on an uploaded base64 image or CV context string."""
    vision_result = None

    if request.image_b64:
        vision_result = vision_llm.analyze_image(
            request.image_b64,
            cv_context=f"Type={request.incident_type}, Conf={request.confidence}, Sev={request.severity}",
        )
    elif request.cv_context:
        vision_result = vision_llm.analyze_cv_outputs(request.cv_context)
    else:
        raise HTTPException(status_code=400, detail="Provide either image_b64 or cv_context")

    # Also run LLM classifier
    llm_result = llm_classifier.classify_incident(
        incident_type=request.incident_type or (vision_result.detected_type if vision_result else "UNKNOWN"),
        confidence=request.confidence,
        severity=request.severity,
        address=request.address,
        camera_id=request.camera_id,
        image_description=vision_result.description if vision_result else None,
    )

    return {
        "vision_analysis": vision_result.model_dump() if vision_result else None,
        "llm_classification": llm_result.model_dump(),
    }


@app.post("/api/upload-image-analyze")
async def upload_image_analyze(
    file: UploadFile = File(...),
    incident_type: str = Form("UNKNOWN"),
    confidence: float = Form(0.5),
    severity: float = Form(0.5),
    address: str = Form("Unknown Location"),
    camera_id: str = Form("CAM-UPLOAD"),
):
    """Accepts a multipart file upload, runs vision + LLM analysis."""
    contents = await file.read()
    image_b64 = base64.b64encode(contents).decode("utf-8")

    vision_result = vision_llm.analyze_image(
        image_b64,
        cv_context=f"Type={incident_type}, Conf={confidence}, Sev={severity}",
    )
    llm_result = llm_classifier.classify_incident(
        incident_type=incident_type or vision_result.detected_type,
        confidence=confidence,
        severity=severity,
        address=address,
        camera_id=camera_id,
        image_description=vision_result.description,
    )

    return {
        "filename": file.filename,
        "vision_analysis": vision_result.model_dump(),
        "llm_classification": llm_result.model_dump(),
    }


# ── Videos List ───────────────────────────────────────────────────────────────
@app.get("/api/videos-list")
def list_sample_videos():
    videos = []
    if SAMPLE_VIDEOS_DIR.exists():
        for f in SAMPLE_VIDEOS_DIR.glob("*.mp4"):
            videos.append({
                "name": f.name,
                "url": f"/videos/{f.name}",
                "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
            })
    return {"videos": videos}


# ── Hospitals ─────────────────────────────────────────────────────────────────
@app.get("/api/hospitals")
def get_hospitals():
    return {
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "road_node_id": h.road_node_id,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "er_beds_available": h.er_beds_available,
                "trauma_level": h.trauma_level,
                "ambulances": [
                    {"id": a.id, "status": a.status} for a in h.ambulances
                ],
            }
            for h in hospital_service.hospitals.values()
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
