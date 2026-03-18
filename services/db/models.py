"""
Read-only SQLAlchemy ORM mirrors of the Django tables.
These map to the EXISTING MySQL tables — no migrations, no table creation.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Users ────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "app_user"

    id: int = Column(BigInteger, primary_key=True)
    password = Column(String(128))
    last_login = Column(DateTime, nullable=True)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True)
    first_name = Column(String(150))
    last_name = Column(String(150))
    email = Column(String(254), unique=True)
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime)
    phone = Column(String(20), nullable=True)
    role = Column(String(20))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_login_ip = Column(String(39), nullable=True)
    registration_complete = Column(Boolean, default=False)
    contract_acceptance_date = Column(DateTime, nullable=True)
    is_dashboard_enabled = Column(Boolean, default=False)

    client_profile = relationship("Client", back_populates="user", uselist=False)
    interpreter_profile = relationship("Interpreter", back_populates="user", uselist=False)


class Client(Base):
    __tablename__ = "app_client"

    id: int = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("app_user.id"))
    company_name = Column(String(100))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    phone = Column(String(20), nullable=True)
    email = Column(String(254), nullable=True)
    billing_address = Column(Text, nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(50), nullable=True)
    billing_zip_code = Column(String(20), nullable=True)
    tax_id = Column(String(50), nullable=True)
    preferred_language_id = Column(BigInteger, ForeignKey("app_language.id"), nullable=True)
    notes = Column(Text, nullable=True)
    credit_limit = Column(Numeric(10, 2), default=0)
    active = Column(Boolean, default=True)

    user = relationship("User", back_populates="client_profile")
    assignments = relationship("Assignment", back_populates="client")


class Interpreter(Base):
    __tablename__ = "app_interpreter"

    id: int = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("app_user.id"))
    profile_image = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    certifications = Column(MySQLJSON, nullable=True)
    specialties = Column(MySQLJSON, nullable=True)
    availability = Column(MySQLJSON, nullable=True)
    radius_of_service = Column(Integer, nullable=True)
    hourly_rate = Column(Numeric(10, 2), nullable=True)
    bank_name = Column(String(100), nullable=True)
    account_holder_name = Column(String(100), nullable=True)
    routing_number = Column(String(255), nullable=True)
    account_number = Column(String(255), nullable=True)
    account_type = Column(String(10), nullable=True)
    background_check_date = Column(Date, nullable=True)
    background_check_status = Column(Boolean, default=False)
    w9_on_file = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    date_of_birth = Column(Date, nullable=True)
    years_of_experience = Column(String(20), nullable=True)
    assignment_types = Column(MySQLJSON, nullable=True)
    preferred_assignment_type = Column(String(20), nullable=True)
    cities_willing_to_cover = Column(MySQLJSON, nullable=True)
    contract_acceptance_date = Column(DateTime, nullable=True)
    contract_rejection_reason = Column(Text, nullable=True)
    has_accepted_contract = Column(Boolean, default=False)
    is_dashboard_enabled = Column(Boolean, default=False)
    contract_invite_token = Column(String(64), nullable=True)
    contract_invite_expires_at = Column(DateTime, nullable=True)
    signature_ip = Column(String(45), nullable=True)
    is_manually_blocked = Column(Boolean, default=False)
    blocked_reason = Column(Text, nullable=True)
    blocked_at = Column(DateTime, nullable=True)
    blocked_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)

    user = relationship("User", back_populates="interpreter_profile", foreign_keys=[user_id])
    interpreter_languages = relationship("InterpreterLanguage", back_populates="interpreter")
    assignments = relationship("Assignment", back_populates="interpreter")


class InterpreterLocation(Base):
    __tablename__ = "app_interpreter_location"

    id: int = Column(BigInteger, primary_key=True)
    interpreter_id = Column(BigInteger, ForeignKey("app_interpreter.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    accuracy = Column(Float, nullable=True)
    is_on_mission = Column(Boolean, default=False)
    current_assignment_id = Column(BigInteger, ForeignKey("app_assignment.id"), nullable=True)
    timestamp = Column(DateTime)

    __table_args__ = (
        Index("idx_interp_loc_ts", "interpreter_id", "timestamp"),
    )


# ── Languages ────────────────────────────────────────────────────

class Language(Base):
    __tablename__ = "app_language"

    id: int = Column(BigInteger, primary_key=True)
    name = Column(String(100), unique=True)
    code = Column(String(10), unique=True)
    is_active = Column(Boolean, default=True)


class InterpreterLanguage(Base):
    __tablename__ = "app_interpreterlanguage"

    id: int = Column(BigInteger, primary_key=True)
    interpreter_id = Column(BigInteger, ForeignKey("app_interpreter.id"))
    language_id = Column(BigInteger, ForeignKey("app_language.id"))
    proficiency = Column(String(20))
    is_primary = Column(Boolean, default=False)
    certified = Column(Boolean, default=False)
    certification_details = Column(Text, nullable=True)

    interpreter = relationship("Interpreter", back_populates="interpreter_languages")
    language = relationship("Language")


# ── Services & Assignments ───────────────────────────────────────

class ServiceType(Base):
    __tablename__ = "app_servicetype"

    id: int = Column(BigInteger, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    base_rate = Column(Numeric(10, 2))
    minimum_hours = Column(Integer, default=1)
    cancellation_policy = Column(Text)
    requires_certification = Column(Boolean, default=False)
    active = Column(Boolean, default=True)


class QuoteRequest(Base):
    __tablename__ = "app_quoterequest"

    id: int = Column(BigInteger, primary_key=True)
    client_id = Column(BigInteger, ForeignKey("app_client.id"))
    service_type_id = Column(BigInteger, ForeignKey("app_servicetype.id"))
    requested_date = Column(DateTime)
    duration = Column(Integer)
    location = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    source_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    target_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    special_requirements = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    client = relationship("Client")
    service_type = relationship("ServiceType")
    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])


class Quote(Base):
    __tablename__ = "app_quote"

    id: int = Column(BigInteger, primary_key=True)
    quote_request_id = Column(BigInteger, ForeignKey("app_quoterequest.id"))
    reference_number = Column(String(20), unique=True)
    amount = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2), default=0)
    valid_until = Column(Date)
    terms = Column(Text)
    status = Column(String(20), default="DRAFT")
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Assignment(Base):
    __tablename__ = "app_assignment"

    id: int = Column(BigInteger, primary_key=True)
    quote_id = Column(BigInteger, ForeignKey("app_quote.id"), nullable=True)
    interpreter_id = Column(BigInteger, ForeignKey("app_interpreter.id"), nullable=True)
    client_id = Column(BigInteger, ForeignKey("app_client.id"), nullable=True)
    client_name = Column(String(255), nullable=True)
    client_email = Column(String(254), nullable=True)
    client_phone = Column(String(20), nullable=True)
    service_type_id = Column(BigInteger, ForeignKey("app_servicetype.id"))
    source_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    target_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    status = Column(String(20))
    is_paid = Column(Boolean, nullable=True)
    interpreter_rate = Column(Numeric(10, 2))
    minimum_hours = Column(Integer, default=2)
    total_interpreter_payment = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text, nullable=True)
    special_requirements = Column(Text, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)

    interpreter = relationship("Interpreter", back_populates="assignments")
    client = relationship("Client", back_populates="assignments")
    service_type = relationship("ServiceType")
    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])


class PublicQuoteRequest(Base):
    __tablename__ = "app_publicquoterequest"

    id: int = Column(BigInteger, primary_key=True)
    full_name = Column(String(100))
    email = Column(String(254))
    phone = Column(String(20))
    company_name = Column(String(100))
    source_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    target_language_id = Column(BigInteger, ForeignKey("app_language.id"))
    service_type_id = Column(BigInteger, ForeignKey("app_servicetype.id"))
    requested_date = Column(DateTime)
    duration = Column(Integer)
    location = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    special_requirements = Column(Text, nullable=True)
    created_at = Column(DateTime)
    processed = Column(Boolean, default=False)
    processed_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)

    source_language = relationship("Language", foreign_keys=[source_language_id])
    target_language = relationship("Language", foreign_keys=[target_language_id])
    service_type = relationship("ServiceType")


# ── Communication ────────────────────────────────────────────────

class ContactMessage(Base):
    __tablename__ = "app_contactmessage"

    id: int = Column(BigInteger, primary_key=True)
    name = Column(String(100))
    email = Column(String(254))
    subject = Column(String(200))
    message = Column(Text)
    created_at = Column(DateTime)
    processed = Column(Boolean, default=False)
    processed_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class Notification(Base):
    __tablename__ = "app_notification"

    id: int = Column(BigInteger, primary_key=True)
    recipient_id = Column(BigInteger, ForeignKey("app_user.id"))
    type = Column(String(20))
    title = Column(String(200))
    content = Column(Text)
    read = Column(Boolean, default=False)
    link = Column(String(200), nullable=True)
    created_at = Column(DateTime)


class EmailLog(Base):
    __tablename__ = "app_emaillog"

    id: int = Column(BigInteger, primary_key=True)
    gmail_id = Column(String(100), unique=True)
    gmail_thread_id = Column(String(100))
    from_email = Column(String(254))
    from_name = Column(String(200))
    subject = Column(String(500))
    body_preview = Column(Text)
    received_at = Column(DateTime)
    category = Column(String(20), nullable=True)
    priority = Column(String(10), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_extracted_data = Column(MySQLJSON, default=dict)
    ai_suggested_actions = Column(MySQLJSON, default=list)
    is_read = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    processed_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    linked_client_id = Column(BigInteger, ForeignKey("app_client.id"), nullable=True)
    linked_assignment_id = Column(BigInteger, ForeignKey("app_assignment.id"), nullable=True)
    linked_quote_request_id = Column(BigInteger, ForeignKey("app_quoterequest.id"), nullable=True)
    linked_onboarding_id = Column(BigInteger, nullable=True)
    has_attachments = Column(Boolean, default=False)
    created_at = Column(DateTime)


class AssignmentFeedback(Base):
    __tablename__ = "app_assignmentfeedback"

    id: int = Column(BigInteger, primary_key=True)
    assignment_id = Column(BigInteger, ForeignKey("app_assignment.id"))
    rating = Column(Integer)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"))


# ── Onboarding ───────────────────────────────────────────────────

class OnboardingInvitation(Base):
    __tablename__ = "app_onboarding_invitation"

    id = Column(String(36), primary_key=True)  # UUID
    invitation_number = Column(String(50), unique=True)
    email = Column(String(254))
    first_name = Column(String(150))
    last_name = Column(String(150))
    phone = Column(String(20))
    user_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    interpreter_id = Column(BigInteger, ForeignKey("app_interpreter.id"), nullable=True)
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    current_phase = Column(String(20), default="INVITED")
    version = Column(Integer, default=1)
    token = Column(String(100), unique=True)
    created_at = Column(DateTime)
    email_sent_at = Column(DateTime, nullable=True)
    email_opened_at = Column(DateTime, nullable=True)
    welcome_viewed_at = Column(DateTime, nullable=True)
    account_created_at = Column(DateTime, nullable=True)
    profile_completed_at = Column(DateTime, nullable=True)
    contract_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime)
    void_reason = Column(Text, nullable=True)


# ── Finance ──────────────────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "app_invoice"

    id: int = Column(BigInteger, primary_key=True)
    invoice_number = Column(String(50), unique=True)
    client_id = Column(BigInteger, ForeignKey("app_client.id"))
    subtotal = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2))
    status = Column(String(20), default="DRAFT")
    issued_date = Column(Date, nullable=True)
    due_date = Column(Date)
    paid_date = Column(Date, nullable=True)
    payment_method = Column(String(50))
    notes = Column(Text)
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_reminder_sent = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)

    client = relationship("Client")


# ── Marketing ────────────────────────────────────────────────────

class Lead(Base):
    __tablename__ = "app_lead"

    id: int = Column(BigInteger, primary_key=True)
    company_name = Column(String(200))
    contact_name = Column(String(200))
    email = Column(String(254))
    phone = Column(String(20))
    source = Column(String(20))
    stage = Column(String(20), default="NEW")
    estimated_monthly_value = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text)
    converted_client_id = Column(BigInteger, ForeignKey("app_client.id"), nullable=True)
    converted_at = Column(DateTime, nullable=True)
    public_quote_request_id = Column(BigInteger, ForeignKey("app_publicquoterequest.id"), nullable=True)
    contact_message_id = Column(BigInteger, ForeignKey("app_contactmessage.id"), nullable=True)
    assigned_to_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Campaign(Base):
    __tablename__ = "app_campaign"

    id: int = Column(BigInteger, primary_key=True)
    name = Column(String(200))
    channel = Column(String(20))
    status = Column(String(20), default="DRAFT")
    budget = Column(Numeric(10, 2), default=0)
    spent = Column(Numeric(10, 2), default=0)
    leads_generated = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    notes = Column(Text)
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
