"""Pydantic schemas for AI agent endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ClassifyRequest(BaseModel):
    email_id: str = ""
    subject: str = ""
    from_email: str = ""
    from_name: str = ""
    body: str = ""


class ClassifyResponse(BaseModel):
    category: str
    priority: str
    confidence: float
    extracted_data: dict = {}
    suggested_actions: list[str] = []


class MatchRequest(BaseModel):
    language: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    city: str = ""
    state: str = ""
    service_type: str = ""


class MatchResponse(BaseModel):
    recommendations: list[dict] = []
    reasoning: str = ""


class EstimateRequest(BaseModel):
    service_type: str
    language: str
    duration_hours: float
    date: str = ""
    location: str = ""
    is_weekend: bool = False
    is_urgent: bool = False


class EstimateResponse(BaseModel):
    base_rate: float
    hours: float
    subtotal: float
    premiums: dict = {}
    total: float
    notes: str = ""


class CVAnalysisRequest(BaseModel):
    cv_text: str
    email: str = ""


class CVAnalysisResponse(BaseModel):
    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    languages: list[dict] = []
    certifications: list[str] = []
    years_experience: str = ""
    specialties: list[str] = []
    recommendation: str = ""  # ACCEPT, MAYBE, REJECT
    score: int = 0  # 1-10
    reasoning: str = ""


class SuggestRequest(BaseModel):
    email_id: str = ""
    subject: str = ""
    body: str = ""
    from_email: str = ""
    category: str = ""


class SuggestResponse(BaseModel):
    suggestions: list[dict] = []


class ReplyRequest(BaseModel):
    original_subject: str
    original_body: str
    from_email: str
    from_name: str = ""
    category: str = ""
    context: str = ""


class ReplyResponse(BaseModel):
    subject: str
    body_html: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    session_id: str
