"""
FastAPI routes for the Agent Queue and Audit Log.
Exposes queue management (list/approve/reject), email processing pipeline,
and streaming chat — all backed by the Django API for persistence.
"""
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from services.config import get_settings
from services.schemas.queue import (
    AgentAuditLogOut,
    AgentQueueItemOut,
    AgentQueueListResponse,
    AgentQueueRejectRequest,
    AuditLogListResponse,
    ChatStreamRequest,
    ProcessEmailRequest,
    ProcessEmailResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/ai", tags=["AI Agent Queue"])

# ── Injected at startup ────────────────────────────────────────────────────────
_db_factory = None
_runner: Optional[Runner] = None
_session_service = InMemorySessionService()
APP_NAME = "jhbridge_ai_queue"


def set_db_factory(factory):
    global _db_factory
    _db_factory = factory


def init_runner(root_agent):
    global _runner
    _runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=_session_service,
    )


def _django_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DJANGO_ADMIN_TOKEN}",
        "Content-Type": "application/json",
    }


def _django_url(path: str) -> str:
    return f"{settings.DJANGO_API_URL}{path}"


async def _django_get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_django_url(path), params=params or {}, headers=_django_headers())
    if resp.status_code == 200:
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail=resp.text[:200])


async def _django_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_django_url(path), json=payload, headers=_django_headers())
    if resp.status_code in (200, 201):
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail=resp.text[:200])


# ── Queue endpoints ───────────────────────────────────────────────────────────

@router.get("/queue", response_model=AgentQueueListResponse)
async def get_queue(
    status: Optional[str] = Query(None, description="PENDING|APPROVED|REJECTED|DONE|FAILED"),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List agent queue items with optional filters."""
    params = {"page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if category:
        params["category"] = category

    data = await _django_get("/agent-queue/", params)
    pending_data = await _django_get("/agent-queue/count/")

    items = [AgentQueueItemOut(**item) for item in data.get("results", [])]
    return AgentQueueListResponse(
        items=items,
        total=data.get("count", len(items)),
        pending_count=pending_data.get("pending", 0),
    )


@router.get("/queue/count")
async def get_queue_count():
    """Get count of pending items (for notification badge)."""
    data = await _django_get("/agent-queue/count/")
    return data


@router.post("/queue/{item_id}/approve", response_model=AgentQueueItemOut)
async def approve_queue_item(item_id: int):
    """Admin approves a proposed action. Triggers execution."""
    data = await _django_post(f"/agent-queue/{item_id}/approve/", {})
    item = AgentQueueItemOut(**data)

    # Trigger execution asynchronously
    try:
        await _execute_approved_item(item)
    except Exception as e:
        logger.error(f"Execution failed for queue item {item_id}: {e}")
        # Mark as failed in Django
        async with httpx.AsyncClient(timeout=15) as client:
            await client.patch(
                _django_url(f"/agent-queue/{item_id}/"),
                json={"status": "FAILED", "error_message": str(e)},
                headers=_django_headers(),
            )
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")

    return item


@router.post("/queue/{item_id}/reject")
async def reject_queue_item(item_id: int, body: AgentQueueRejectRequest):
    """Admin rejects a proposed action."""
    data = await _django_post(f"/agent-queue/{item_id}/reject/", {"reason": body.reason})
    return AgentQueueItemOut(**data)


# ── Execution engine ─────────────────────────────────────────────────────────

async def _execute_approved_item(item: AgentQueueItemOut):
    """Execute an approved queue item by calling the appropriate Django API."""
    action = item.action_type
    payload = item.action_payload

    if action == "CREATE_ASSIGNMENT":
        result = await _django_post("/assignments/", payload)
        await _update_queue_item_done(item.id, result, linked_assignment_id=result.get("id"))

    elif action == "SEND_ONBOARDING":
        result = await _django_post("/onboarding/", payload)
        await _update_queue_item_done(item.id, result)

    elif action == "CREATE_QUOTE_REQUEST":
        result = await _django_post("/quote-requests/", payload)
        await _update_queue_item_done(item.id, result)

    elif action == "CREATE_CLIENT":
        result = await _django_post("/clients/", payload)
        await _update_queue_item_done(item.id, result, linked_client_id=result.get("id"))

    elif action == "SEND_REPLY":
        # Delegate to Gmail router
        to = payload.get("to", "")
        subject = payload.get("subject", "")
        body_html = payload.get("body_html", "")
        reply_to_id = payload.get("reply_to_id", "")
        from services.adk_agents.tools.gmail_tools import send_email
        result = send_email(to=to, subject=subject, body_html=body_html, reply_to_id=reply_to_id)
        await _update_queue_item_done(item.id, result)

    elif action in ("RECORD_INVOICE", "RECORD_PAYSLIP", "MARK_INVOICE_PAID"):
        # These are manual finance actions — just mark as done for now
        # The admin processes them in the Finance module
        await _update_queue_item_done(item.id, {"message": f"Queued for finance processing: {action}"})

    else:
        # MANUAL_REVIEW — no automatic action
        await _update_queue_item_done(item.id, {"message": "Manual review completed"})


async def _update_queue_item_done(
    item_id: int,
    result: dict,
    linked_assignment_id: int = None,
    linked_client_id: int = None,
):
    from datetime import datetime, timezone
    patch_data = {
        "status": "DONE",
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    if linked_assignment_id:
        patch_data["linked_assignment_id"] = linked_assignment_id
    if linked_client_id:
        patch_data["linked_client_id"] = linked_client_id

    async with httpx.AsyncClient(timeout=15) as client:
        await client.patch(
            _django_url(f"/agent-queue/{item_id}/"),
            json=patch_data,
            headers=_django_headers(),
        )


# ── Email processing pipeline ─────────────────────────────────────────────────

@router.post("/process-email", response_model=ProcessEmailResponse)
async def process_email(req: ProcessEmailRequest):
    """Run the full AI pipeline on a single email:
    classify → extract → match → enqueue for approval.
    """
    if not _runner:
        raise HTTPException(status_code=503, detail="Agent runner not initialized")

    session_id = f"proc_{uuid.uuid4().hex[:12]}"
    user_id = "admin"

    session = await _session_service.get_session(APP_NAME, user_id, session_id)
    if not session:
        await _session_service.create_session(APP_NAME, user_id, session_id)

    # Build processing prompt routing to the right sub-agent based on quick scan
    subject_lower = req.subject.lower()
    body_lower = req.body.lower()

    if any(k in subject_lower + body_lower for k in ["invoice", "bill", "payment due", "remittance"]):
        agent_hint = "Use the invoice_processor sub-agent."
    elif any(k in subject_lower + body_lower for k in ["payslip", "paystub", "pay stub", "earnings statement"]):
        agent_hint = "Use the payslip_extractor sub-agent."
    elif any(k in subject_lower + body_lower for k in ["interpreter", "interpretation", "translation", "language"]):
        agent_hint = "Use the assignment_request_processor sub-agent."
    elif any(k in subject_lower + body_lower for k in ["cv", "resume", "applying", "application", "candidate"]):
        agent_hint = "Use the cv_analyzer sub-agent, then call enqueue_agent_action with action_type SEND_ONBOARDING."
    else:
        agent_hint = "Classify this email first with email_classifier, then route to the appropriate sub-agent."

    prompt = (
        f"{agent_hint}\n\n"
        f"Gmail ID: {req.gmail_id}\n"
        f"From: {req.from_name} <{req.from_email}>\n"
        f"Subject: {req.subject}\n"
        f"Has attachments: {req.has_attachments}\n\n"
        f"{req.body[:3000]}"
    )

    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    final_text = ""
    async for event in _runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    # Parse result
    result_data = _parse_json(final_text)
    return ProcessEmailResponse(
        gmail_id=req.gmail_id,
        category=result_data.get("category", "OTHER"),
        confidence=float(result_data.get("confidence", 0.5)),
        action_type=result_data.get("action_type", "MANUAL_REVIEW"),
        queue_item_id=result_data.get("queue_item_id"),
        message=final_text[:300],
    )


@router.post("/process-unread")
async def process_unread_emails(limit: int = Query(10, ge=1, le=30)):
    """Process all unread/unprocessed emails from the inbox."""
    if not _db_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    from services.db import queries
    async with _db_factory() as db:
        emails = await queries.get_unprocessed_emails(db, limit=limit)

    processed = 0
    failed = 0
    queue_items = []

    for email in emails:
        try:
            req = ProcessEmailRequest(
                gmail_id=email.gmail_id,
                subject=email.subject,
                from_email=email.from_email,
                from_name=email.from_name,
                body=email.body_preview,
                has_attachments=email.has_attachments,
            )
            result = await process_email(req)
            if result.queue_item_id:
                queue_items.append(result.queue_item_id)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process email {email.gmail_id}: {e}")
            failed += 1

    return {
        "processed": processed,
        "failed": failed,
        "queue_items_created": len(queue_items),
        "queue_item_ids": queue_items,
    }


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
):
    """Get the agent audit trail."""
    params = {"page": page, "page_size": page_size}
    if action:
        params["action"] = action
    if success is not None:
        params["success"] = str(success).lower()

    data = await _django_get("/agent-audit/", params)
    items = [AgentAuditLogOut(**item) for item in data.get("results", [])]
    return AuditLogListResponse(items=items, total=data.get("count", len(items)))


# ── Streaming chat ─────────────────────────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    """Stream a chat response from the JHBridge agent using SSE."""
    if not _runner:
        raise HTTPException(status_code=503, detail="Agent runner not initialized")

    session_id = req.session_id or f"chat_{uuid.uuid4().hex[:12]}"
    user_id = "admin"

    session = await _session_service.get_session(APP_NAME, user_id, session_id)
    if not session:
        await _session_service.create_session(APP_NAME, user_id, session_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        content = types.Content(role="user", parts=[types.Part(text=req.message)])
        tool_calls_log = []
        full_text = ""

        try:
            async for event in _runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                # Emit tool call events so frontend can show "thinking" state
                if hasattr(event, "content") and event.content:
                    for part in (event.content.parts or []):
                        if hasattr(part, "function_call") and part.function_call:
                            tool_name = part.function_call.name
                            tool_calls_log.append(tool_name)
                            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name})}\n\n"

                        if hasattr(part, "function_response") and part.function_response:
                            yield f"data: {json.dumps({'type': 'tool_result', 'tool': part.function_response.name})}\n\n"

                if event.is_final_response() and event.content and event.content.parts:
                    text = event.content.parts[0].text or ""
                    full_text += text
                    # Stream in chunks
                    chunk_size = 80
                    for i in range(0, len(text), chunk_size):
                        chunk = text[i:i + chunk_size]
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk, 'session_id': session_id})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'tool_calls': tool_calls_log})}\n\n"

        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    import re as _re
    try:
        return json.loads(text)
    except Exception:
        pass
    for marker in ("```json", "```"):
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            try:
                return json.loads(text[start:end].strip())
            except Exception:
                pass
    m = _re.search(r"\{.*\}", text, _re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}
