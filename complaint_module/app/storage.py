import json
import os
import uuid
from typing import List, Dict, Any, Optional
from .models import Complaint, AuthorityModel, CitizenModel, WorkerModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
AUTHORITIES_FILE = os.path.join(DATA_DIR, "authorities.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
WORKERS_FILE = os.path.join(DATA_DIR, "workers.json")
COMPLAINTS_FILE = os.path.join(DATA_DIR, "complaints.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)


class DataStore:
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(COMPLAINTS_FILE):
            with open(COMPLAINTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def load_authorities(self) -> List[AuthorityModel]:
        with open(AUTHORITIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [AuthorityModel(**a) for a in data]

    def load_user(self) -> CitizenModel:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return CitizenModel(
                user_id=data.get("user_id", "CIT-2026-8921"),
                name=data.get("full_name", "Aditya Sharma"),
                email=data.get("email", "aditya.sharma@city.gov.in"),
                phone=data.get("phone", "+91 98765 43210"),
                ward=data.get("ward", "Ward 14 - Rajpur Road")
            )

    def load_user_raw(self) -> Dict[str, Any]:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_workers(self) -> List[Dict[str, Any]]:
        with open(WORKERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_complaints(self) -> List[Complaint]:
        if not os.path.exists(COMPLAINTS_FILE):
            return []
        try:
            with open(COMPLAINTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Complaint(**c) for c in data]
        except Exception:
            return []

    def save_complaints(self, complaints: List[Complaint]):
        with open(COMPLAINTS_FILE, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in complaints], f, indent=2)

    def get_complaint(self, tracking_id: str) -> Optional[Complaint]:
        for c in self.load_complaints():
            if c.tracking_id.lower() == tracking_id.lower():
                return c
        return None

    def upsert_complaint(self, complaint: Complaint):
        complaints = self.load_complaints()
        found = False
        for idx, item in enumerate(complaints):
            if item.tracking_id == complaint.tracking_id:
                complaints[idx] = complaint
                found = True
                break
        if not found:
            complaints.insert(0, complaint)
        self.save_complaints(complaints)

    def reset_complaints(self):
        with open(COMPLAINTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


store = DataStore()
