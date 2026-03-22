"""
Optimized async database queries for the FastAPI service.
Read operations go directly to MySQL; write operations use Django DRF API.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.db.models import (
    Assignment,
    AssignmentFeedback,
    Client,
    ContactMessage,
    EmailLog,
    Interpreter,
    InterpreterLanguage,
    InterpreterLocation,
    Language,
    Lead,
    Notification,
    OnboardingInvitation,
    PublicQuoteRequest,
    QuoteRequest,
    ServiceType,
    User,
)


# ── Interpreter queries ──────────────────────────────────────────

async def get_available_interpreters(
    db: AsyncSession,
    language: str,
    state: str = "",
    city: str = "",
) -> list[dict]:
    """Find active interpreters matching language and optional location."""
    stmt = (
        select(Interpreter, User, Language)
        .join(User, Interpreter.user_id == User.id)
        .join(InterpreterLanguage, InterpreterLanguage.interpreter_id == Interpreter.id)
        .join(Language, InterpreterLanguage.language_id == Language.id)
        .where(
            Interpreter.active == True,
            User.is_active == True,
            Interpreter.is_manually_blocked == False,
            func.lower(Language.name).contains(language.lower()),
        )
    )
    if state:
        stmt = stmt.where(func.upper(Interpreter.state) == state.upper())
    if city:
        stmt = stmt.where(func.lower(Interpreter.city).contains(city.lower()))

    result = await db.execute(stmt)
    rows = result.all()

    interpreters = {}
    for interp, user, lang in rows:
        if interp.id not in interpreters:
            interpreters[interp.id] = {
                "id": interp.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "city": interp.city,
                "state": interp.state,
                "radius_of_service": interp.radius_of_service,
                "hourly_rate": float(interp.hourly_rate) if interp.hourly_rate else None,
                "specialties": interp.specialties or [],
                "certifications": interp.certifications or [],
                "languages": [],
                "active": interp.active,
            }
        interpreters[interp.id]["languages"].append(lang.name)

    return list(interpreters.values())


async def get_interpreter_by_id(db: AsyncSession, interpreter_id: int) -> dict | None:
    """Get full interpreter details by ID."""
    stmt = (
        select(Interpreter, User)
        .join(User, Interpreter.user_id == User.id)
        .where(Interpreter.id == interpreter_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    interp, user = row

    # Get languages
    lang_stmt = (
        select(Language, InterpreterLanguage)
        .join(InterpreterLanguage, InterpreterLanguage.language_id == Language.id)
        .where(InterpreterLanguage.interpreter_id == interpreter_id)
    )
    lang_result = await db.execute(lang_stmt)
    languages = [
        {
            "name": lang.name,
            "proficiency": il.proficiency,
            "certified": il.certified,
            "is_primary": il.is_primary,
        }
        for lang, il in lang_result.all()
    ]

    # Get assignment stats
    stats_stmt = select(
        func.count(Assignment.id).label("total"),
        func.avg(AssignmentFeedback.rating).label("avg_rating"),
    ).select_from(Assignment).outerjoin(
        AssignmentFeedback, AssignmentFeedback.assignment_id == Assignment.id
    ).where(
        Assignment.interpreter_id == interpreter_id,
        Assignment.status == "COMPLETED",
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.first()

    return {
        "id": interp.id,
        "name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "phone": user.phone,
        "city": interp.city,
        "state": interp.state,
        "zip_code": interp.zip_code,
        "radius_of_service": interp.radius_of_service,
        "hourly_rate": float(interp.hourly_rate) if interp.hourly_rate else None,
        "specialties": interp.specialties or [],
        "certifications": interp.certifications or [],
        "languages": languages,
        "years_of_experience": interp.years_of_experience,
        "completed_missions": stats.total if stats else 0,
        "average_rating": round(float(stats.avg_rating), 2) if stats and stats.avg_rating else None,
        "active": interp.active,
        "has_accepted_contract": interp.has_accepted_contract,
    }


async def check_interpreter_availability(
    db: AsyncSession,
    interpreter_id: int,
    check_date: str,
    start_time: str,
    end_time: str,
) -> dict:
    """Check if interpreter has conflicts for the given date/time range."""
    dt = datetime.strptime(check_date, "%Y-%m-%d").date()
    st = datetime.combine(dt, time.fromisoformat(start_time))
    et = datetime.combine(dt, time.fromisoformat(end_time))

    stmt = (
        select(func.count(Assignment.id))
        .where(
            Assignment.interpreter_id == interpreter_id,
            Assignment.status.in_(["PENDING", "CONFIRMED", "IN_PROGRESS"]),
            Assignment.start_time < et,
            Assignment.end_time > st,
        )
    )
    result = await db.execute(stmt)
    conflict_count = result.scalar() or 0

    return {
        "interpreter_id": interpreter_id,
        "date": check_date,
        "start_time": start_time,
        "end_time": end_time,
        "available": conflict_count == 0,
        "conflicts": conflict_count,
    }


# ── Client queries ───────────────────────────────────────────────

async def get_client_by_email(db: AsyncSession, email: str) -> dict | None:
    """Look up a client by their user email."""
    stmt = (
        select(Client, User)
        .join(User, Client.user_id == User.id)
        .where(func.lower(User.email) == email.lower())
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    client, user = row
    return {
        "id": client.id,
        "user_id": user.id,
        "company_name": client.company_name,
        "contact_name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "phone": client.phone or user.phone,
        "city": client.city,
        "state": client.state,
        "active": client.active,
    }


# ── Assignment queries ───────────────────────────────────────────

async def get_assignment_by_id(db: AsyncSession, assignment_id: int) -> dict | None:
    """Get assignment with all related data."""
    stmt = (
        select(Assignment)
        .where(Assignment.id == assignment_id)
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()
    if not assignment:
        return None

    # Get related data
    interp_name = ""
    if assignment.interpreter_id:
        interp_stmt = (
            select(User.first_name, User.last_name)
            .join(Interpreter, Interpreter.user_id == User.id)
            .where(Interpreter.id == assignment.interpreter_id)
        )
        interp_result = await db.execute(interp_stmt)
        interp_row = interp_result.first()
        if interp_row:
            interp_name = f"{interp_row.first_name} {interp_row.last_name}"

    client_display = assignment.client_name or ""
    if assignment.client_id:
        client_stmt = select(Client.company_name).where(Client.id == assignment.client_id)
        client_result = await db.execute(client_stmt)
        client_row = client_result.scalar_one_or_none()
        if client_row:
            client_display = client_row

    stype_stmt = select(ServiceType.name).where(ServiceType.id == assignment.service_type_id)
    stype = (await db.execute(stype_stmt)).scalar_one_or_none() or ""

    src_lang_stmt = select(Language.name).where(Language.id == assignment.source_language_id)
    src_lang = (await db.execute(src_lang_stmt)).scalar_one_or_none() or ""

    tgt_lang_stmt = select(Language.name).where(Language.id == assignment.target_language_id)
    tgt_lang = (await db.execute(tgt_lang_stmt)).scalar_one_or_none() or ""

    return {
        "id": assignment.id,
        "status": assignment.status,
        "interpreter": interp_name,
        "interpreter_id": assignment.interpreter_id,
        "client": client_display,
        "client_id": assignment.client_id,
        "service_type": stype,
        "source_language": src_lang,
        "target_language": tgt_lang,
        "start_time": assignment.start_time.isoformat() if assignment.start_time else None,
        "end_time": assignment.end_time.isoformat() if assignment.end_time else None,
        "location": assignment.location,
        "city": assignment.city,
        "state": assignment.state,
        "zip_code": assignment.zip_code,
        "interpreter_rate": float(assignment.interpreter_rate) if assignment.interpreter_rate else None,
        "total_payment": float(assignment.total_interpreter_payment) if assignment.total_interpreter_payment else None,
        "notes": assignment.notes,
    }


async def get_active_assignments_today(db: AsyncSession) -> list[dict]:
    """Get all assignments for today."""
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    stmt = (
        select(Assignment, ServiceType, Language)
        .join(ServiceType, Assignment.service_type_id == ServiceType.id)
        .join(Language, Assignment.source_language_id == Language.id)
        .where(
            Assignment.start_time >= today_start,
            Assignment.start_time <= today_end,
            Assignment.status.in_(["PENDING", "CONFIRMED", "IN_PROGRESS"]),
        )
        .order_by(Assignment.start_time)
    )
    result = await db.execute(stmt)
    rows = result.all()

    assignments = []
    for a, stype, lang in rows:
        assignments.append({
            "id": a.id,
            "status": a.status,
            "service_type": stype.name,
            "language": lang.name,
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "end_time": a.end_time.isoformat() if a.end_time else None,
            "location": a.location,
            "city": a.city,
            "state": a.state,
            "client_name": a.client_name,
            "interpreter_id": a.interpreter_id,
        })

    return assignments


async def get_pending_quote_requests(db: AsyncSession) -> list[dict]:
    """Get all unprocessed quote requests (both internal and public)."""
    # Internal quote requests
    stmt = (
        select(QuoteRequest, ServiceType, Language)
        .join(ServiceType, QuoteRequest.service_type_id == ServiceType.id)
        .join(Language, QuoteRequest.source_language_id == Language.id)
        .where(QuoteRequest.status == "PENDING")
        .order_by(QuoteRequest.created_at.desc())
    )
    result = await db.execute(stmt)
    internal = [
        {
            "type": "internal",
            "id": qr.id,
            "service_type": stype.name,
            "language": lang.name,
            "requested_date": qr.requested_date.isoformat() if qr.requested_date else None,
            "duration_minutes": qr.duration,
            "location": f"{qr.city}, {qr.state}",
            "created_at": qr.created_at.isoformat() if qr.created_at else None,
        }
        for qr, stype, lang in result.all()
    ]

    # Public quote requests
    pub_stmt = (
        select(PublicQuoteRequest, ServiceType, Language)
        .join(ServiceType, PublicQuoteRequest.service_type_id == ServiceType.id)
        .join(Language, PublicQuoteRequest.source_language_id == Language.id)
        .where(PublicQuoteRequest.processed == False)
        .order_by(PublicQuoteRequest.created_at.desc())
    )
    pub_result = await db.execute(pub_stmt)
    public = [
        {
            "type": "public",
            "id": pqr.id,
            "name": pqr.full_name,
            "company": pqr.company_name,
            "email": pqr.email,
            "service_type": stype.name,
            "language": lang.name,
            "requested_date": pqr.requested_date.isoformat() if pqr.requested_date else None,
            "duration_minutes": pqr.duration,
            "location": f"{pqr.city}, {pqr.state}",
            "created_at": pqr.created_at.isoformat() if pqr.created_at else None,
        }
        for pqr, stype, lang in pub_result.all()
    ]

    return internal + public


# ── EmailLog (read/write) ────────────────────────────────────────

async def get_email_logs(
    db: AsyncSession,
    category: str | None = None,
    priority: str | None = None,
    is_read: bool | None = None,
    is_processed: bool | None = None,
    from_email: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list, int]:
    """Query EmailLog with optional filters. Returns (rows, total_count)."""
    stmt = select(EmailLog)
    count_stmt = select(func.count()).select_from(EmailLog)

    filters = []
    if category:
        filters.append(EmailLog.category == category.upper())
    if priority:
        filters.append(EmailLog.priority == priority.upper())
    if is_read is not None:
        filters.append(EmailLog.is_read == is_read)
    if is_processed is not None:
        filters.append(EmailLog.is_processed == is_processed)
    if from_email:
        filters.append(func.lower(EmailLog.from_email).contains(from_email.lower()))

    if filters:
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(EmailLog.received_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return rows, total


async def mark_email_read(db: AsyncSession, gmail_id: str, is_read: bool = True) -> bool:
    """Update is_read on an EmailLog. Returns True if record found."""
    from sqlalchemy import update
    stmt = (
        update(EmailLog)
        .where(EmailLog.gmail_id == gmail_id)
        .values(is_read=is_read)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def mark_email_processed(
    db: AsyncSession,
    gmail_id: str,
    is_processed: bool = True,
    processed_by_id: int | None = None,
) -> bool:
    """Update is_processed on an EmailLog. Returns True if record found."""
    from sqlalchemy import update
    from datetime import timezone
    values = {"is_processed": is_processed}
    if is_processed:
        values["processed_at"] = datetime.now(timezone.utc)
        if processed_by_id:
            values["processed_by_id"] = processed_by_id
    stmt = (
        update(EmailLog)
        .where(EmailLog.gmail_id == gmail_id)
        .values(**values)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_unprocessed_emails(db: AsyncSession, limit: int = 20) -> list:
    """Fetch EmailLog rows that have not been processed by the agent yet."""
    stmt = (
        select(EmailLog)
        .where(EmailLog.is_processed == False)
        .order_by(EmailLog.received_at.desc())
        .limit(min(limit, 30))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_unclassified_emails(db: AsyncSession, limit: int = 20) -> list:
    """Fetch EmailLog rows that have no category yet."""
    stmt = (
        select(EmailLog)
        .where(EmailLog.category == None)
        .order_by(EmailLog.received_at.desc())
        .limit(min(limit, 50))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_email_classification(db: AsyncSession, gmail_id: str, classification: dict) -> bool:
    """Save AI classification result back to EmailLog."""
    from sqlalchemy import update
    stmt = (
        update(EmailLog)
        .where(EmailLog.gmail_id == gmail_id)
        .values(
            category=classification.get("category"),
            priority=classification.get("priority"),
            ai_confidence=classification.get("confidence"),
            ai_extracted_data=classification.get("extracted_data", {}),
            ai_suggested_actions=classification.get("suggested_actions", []),
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def save_email_log(db: AsyncSession, data: dict) -> int:
    """Insert a new email log entry and return its ID."""
    email_log = EmailLog(**data)
    db.add(email_log)
    await db.commit()
    await db.refresh(email_log)
    return email_log.id


# ── InterpreterLocation (write) ──────────────────────────────────

async def save_interpreter_location(db: AsyncSession, data: dict) -> int:
    """Insert a new location entry and return its ID."""
    location = InterpreterLocation(**data)
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location.id


async def get_latest_interpreter_locations(db: AsyncSession) -> list[dict]:
    """Get the most recent location for each active interpreter."""
    # Subquery: latest timestamp per interpreter
    subq = (
        select(
            InterpreterLocation.interpreter_id,
            func.max(InterpreterLocation.timestamp).label("max_ts"),
        )
        .group_by(InterpreterLocation.interpreter_id)
        .subquery()
    )

    stmt = (
        select(InterpreterLocation, User.first_name, User.last_name)
        .join(subq, and_(
            InterpreterLocation.interpreter_id == subq.c.interpreter_id,
            InterpreterLocation.timestamp == subq.c.max_ts,
        ))
        .join(Interpreter, InterpreterLocation.interpreter_id == Interpreter.id)
        .join(User, Interpreter.user_id == User.id)
    )
    result = await db.execute(stmt)

    return [
        {
            "interpreter_id": loc.interpreter_id,
            "name": f"{fname} {lname}",
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "accuracy": loc.accuracy,
            "is_on_mission": loc.is_on_mission,
            "current_assignment_id": loc.current_assignment_id,
            "timestamp": loc.timestamp.isoformat() if loc.timestamp else None,
        }
        for loc, fname, lname in result.all()
    ]


# ── Onboarding ───────────────────────────────────────────────────

async def get_onboarding_by_email(db: AsyncSession, email: str) -> dict | None:
    """Look up onboarding invitation by email."""
    stmt = (
        select(OnboardingInvitation)
        .where(func.lower(OnboardingInvitation.email) == email.lower())
        .order_by(OnboardingInvitation.created_at.desc())
    )
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if not inv:
        return None

    return {
        "id": str(inv.id),
        "invitation_number": inv.invitation_number,
        "email": inv.email,
        "name": f"{inv.first_name} {inv.last_name}",
        "current_phase": inv.current_phase,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
    }
