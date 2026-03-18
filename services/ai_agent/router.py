"""
FastAPI routes for the AI agent.
These wrap the ADK Runner to provide structured JSON endpoints for the React frontend.
"""
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from services.adk_agents.jhbridge_agent import root_agent
from services.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ClassifyRequest,
    ClassifyResponse,
    CVAnalysisRequest,
    CVAnalysisResponse,
    EstimateRequest,
    EstimateResponse,
    MatchRequest,
    MatchResponse,
    ReplyRequest,
    ReplyResponse,
    SuggestRequest,
    SuggestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Agent"])

APP_NAME = "jhbridge_ai"
_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=_session_service,
)


async def _invoke_agent(prompt: str, session_id: str = "") -> str:
    """Invoke the ADK agent and collect the final response text."""
    user_id = "admin"
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"

    # Ensure session exists
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        session = await _session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    return final_text


def _parse_json_response(text: str) -> dict:
    """Try to extract a JSON object from agent response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in markdown
    for marker in ("```json", "```"):
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Try to find { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}") + 1
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end])
        except json.JSONDecodeError:
            pass

    return {}


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/classify", response_model=ClassifyResponse)
async def classify_email(req: ClassifyRequest):
    """Classify an email into operation categories and extract structured data."""
    prompt = (
        f"Classify this email. Use the email_classifier sub-agent.\n\n"
        f"From: {req.from_name} <{req.from_email}>\n"
        f"Subject: {req.subject}\n\n"
        f"{req.body}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return ClassifyResponse(
        category=data.get("category", "OTHER"),
        priority=data.get("priority", "MEDIUM"),
        confidence=data.get("confidence", 0.5),
        extracted_data=data.get("extracted_data", {}),
        suggested_actions=data.get("suggested_actions", []),
    )


@router.post("/match", response_model=MatchResponse)
async def match_interpreter(req: MatchRequest):
    """Find the best interpreter match for given requirements."""
    prompt = (
        f"Find the best interpreter for this assignment. Use the interpreter_matcher sub-agent.\n\n"
        f"Language: {req.language}\n"
        f"Date: {req.date}\n"
        f"Time: {req.start_time} - {req.end_time}\n"
        f"Location: {req.city}, {req.state}\n"
        f"Service type: {req.service_type}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return MatchResponse(
        recommendations=data.get("recommendations", []),
        reasoning=data.get("reasoning", response),
    )


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_quote(req: EstimateRequest):
    """Estimate a quote for interpretation services."""
    prompt = (
        f"Estimate a quote for this service. Use the quote_estimator sub-agent.\n\n"
        f"Service type: {req.service_type}\n"
        f"Language: {req.language}\n"
        f"Duration: {req.duration_hours} hours\n"
        f"Date: {req.date}\n"
        f"Location: {req.location}\n"
        f"Weekend: {req.is_weekend}\n"
        f"Urgent (< 24hr): {req.is_urgent}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return EstimateResponse(
        base_rate=data.get("base_rate", 0),
        hours=data.get("hours", req.duration_hours),
        subtotal=data.get("subtotal", 0),
        premiums=data.get("premiums", {}),
        total=data.get("total", 0),
        notes=data.get("notes", response),
    )


@router.post("/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(req: CVAnalysisRequest):
    """Analyze an interpreter candidate's CV/resume."""
    prompt = (
        f"Analyze this CV/resume. Use the cv_analyzer sub-agent.\n\n"
        f"Candidate email: {req.email}\n\n"
        f"CV Content:\n{req.cv_text}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return CVAnalysisResponse(
        candidate_name=data.get("candidate_name", ""),
        email=data.get("email", req.email),
        phone=data.get("phone", ""),
        location=data.get("location", ""),
        languages=data.get("languages", []),
        certifications=data.get("certifications", []),
        years_experience=data.get("years_experience", ""),
        specialties=data.get("specialties", []),
        recommendation=data.get("recommendation", "MAYBE"),
        score=data.get("score", 0),
        reasoning=data.get("reasoning", response),
    )


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_actions(req: SuggestRequest):
    """Get AI-suggested actions for a specific email."""
    prompt = (
        f"Suggest actions for this email.\n\n"
        f"From: {req.from_email}\n"
        f"Subject: {req.subject}\n"
        f"Category: {req.category}\n\n"
        f"{req.body}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return SuggestResponse(
        suggestions=data.get("suggestions", [{"action": "review", "description": response}]),
    )


@router.post("/reply", response_model=ReplyResponse)
async def generate_reply(req: ReplyRequest):
    """Generate a professional email reply."""
    prompt = (
        f"Generate a professional reply to this email. Use the reply_generator sub-agent.\n\n"
        f"From: {req.from_name} <{req.from_email}>\n"
        f"Subject: {req.original_subject}\n"
        f"Category: {req.category}\n\n"
        f"Original email:\n{req.original_body}\n\n"
        f"Additional context: {req.context}"
    )
    response = await _invoke_agent(prompt)
    data = _parse_json_response(response)

    return ReplyResponse(
        subject=data.get("subject", f"Re: {req.original_subject}"),
        body_html=data.get("body_html", f"<p>{response}</p>"),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(req: ChatRequest):
    """General-purpose chat with the JHBridge operations agent."""
    session_id = req.session_id or f"chat_{uuid.uuid4().hex[:12]}"
    response = await _invoke_agent(req.message, session_id=session_id)

    return ChatResponse(
        response=response,
        session_id=session_id,
    )
