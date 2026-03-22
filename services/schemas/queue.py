"""Pydantic schemas for agent queue and audit log endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentQueueItemOut(BaseModel):
    id: int
    gmail_id: str
    email_subject: str
    email_from: str
    category: str
    confidence: float
    extracted_data: dict = {}
    action_type: str
    action_payload: dict = {}
    ai_reasoning: str = ""
    status: str
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: str = ""
    executed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error_message: str = ""
    linked_assignment_id: Optional[int] = None
    linked_client_id: Optional[int] = None
    linked_onboarding_id: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentQueueListResponse(BaseModel):
    items: list[AgentQueueItemOut]
    total: int
    pending_count: int


class AgentQueueApproveRequest(BaseModel):
    pass  # no body needed


class AgentQueueRejectRequest(BaseModel):
    reason: str = ""


class AgentAuditLogOut(BaseModel):
    id: int
    queue_item_id: Optional[int] = None
    action: str
    entity_type: str = ""
    entity_id: str = ""
    success: bool
    details: dict = {}
    performed_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AgentAuditLogOut]
    total: int


class ProcessEmailRequest(BaseModel):
    gmail_id: str
    subject: str = ""
    from_email: str = ""
    from_name: str = ""
    body: str = ""
    has_attachments: bool = False


class ProcessEmailResponse(BaseModel):
    gmail_id: str
    category: str
    confidence: float
    action_type: str
    queue_item_id: Optional[int] = None
    message: str = ""


class ChatStreamRequest(BaseModel):
    message: str
    session_id: str = ""
