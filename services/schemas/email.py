"""Pydantic schemas for email-related endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class EmailPreview(BaseModel):
    gmail_id: str
    from_email: str
    from_name: str = ""
    subject: str
    snippet: str = ""
    received_at: datetime
    labels: list[str] = []
    has_attachments: bool = False


class EmailFull(EmailPreview):
    body_html: str = ""
    body_text: str = ""
    to: list[str] = []
    cc: list[str] = []
    thread_id: str = ""
    attachments: list[dict] = []


class EmailSendRequest(BaseModel):
    to: EmailStr
    subject: str
    body_html: str
    reply_to_id: str = ""


class EmailReplyRequest(BaseModel):
    body_html: str


class EmailSearchRequest(BaseModel):
    query: str
    max_results: int = 10


class EmailClassification(BaseModel):
    category: str  # INTERPRETATION, QUOTE, HIRING, CONFIRMATION, PAYMENT, OTHER
    priority: str  # URGENT, HIGH, MEDIUM, LOW
    confidence: float
    extracted_data: dict = {}
    suggested_actions: list[str] = []


class EmailLogOut(BaseModel):
    id: int
    gmail_id: str
    from_email: str
    from_name: str
    subject: str
    body_preview: str
    received_at: datetime
    category: Optional[str] = None
    priority: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_extracted_data: dict = {}
    ai_suggested_actions: list = []
    is_read: bool = False
    is_processed: bool = False

    class Config:
        from_attributes = True


class InboxResponse(BaseModel):
    emails: list[EmailLogOut]
    total: int
    page: int = 1
    page_size: int = 20
