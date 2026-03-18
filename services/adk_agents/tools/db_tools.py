"""
Database query tools for the ADK agent.
Each function is a tool that Gemini can call — type hints + docstrings are mandatory.
These run synchronously (ADK handles the async wrapper internally).
"""
import asyncio
from services.db.database import async_session_factory
from services.db import queries


def _run_async(coro):
    """Helper to run an async coroutine from a sync ADK tool."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


async def _search_interpreters(language: str, state: str, city: str) -> list[dict]:
    async with async_session_factory() as db:
        return await queries.get_available_interpreters(db, language, state, city)


async def _get_interpreter_details(interpreter_id: int) -> dict | None:
    async with async_session_factory() as db:
        return await queries.get_interpreter_by_id(db, interpreter_id)


async def _check_availability(interpreter_id: int, date: str, start_time: str, end_time: str) -> dict:
    async with async_session_factory() as db:
        return await queries.check_interpreter_availability(db, interpreter_id, date, start_time, end_time)


async def _get_client_info(client_email: str) -> dict | None:
    async with async_session_factory() as db:
        return await queries.get_client_by_email(db, client_email)


async def _get_today_assignments() -> list[dict]:
    async with async_session_factory() as db:
        return await queries.get_active_assignments_today(db)


async def _get_pending_requests() -> list[dict]:
    async with async_session_factory() as db:
        return await queries.get_pending_quote_requests(db)


# ── ADK Tool Functions ───────────────────────────────────────────

def search_interpreters(language: str, state: str = "", city: str = "") -> dict:
    """Search for available interpreters by language and location.

    Args:
        language: The language needed (e.g., 'Portuguese', 'Spanish', 'Mandarin')
        state: US state code (e.g., 'MA', 'NY') — optional
        city: City name — optional

    Returns:
        dict with list of matching interpreters including name, languages,
        city, state, radius, rate, and availability status
    """
    results = _run_async(_search_interpreters(language, state, city))
    return {"status": "success", "count": len(results), "interpreters": results}


def get_interpreter_details(interpreter_id: int) -> dict:
    """Get full details about a specific interpreter including their
    languages, certifications, availability, performance stats and contact info.

    Args:
        interpreter_id: The database ID of the interpreter
    """
    result = _run_async(_get_interpreter_details(interpreter_id))
    if result:
        return {"status": "success", "interpreter": result}
    return {"status": "error", "error_message": f"Interpreter {interpreter_id} not found"}


def check_interpreter_availability(interpreter_id: int, date: str, start_time: str, end_time: str) -> dict:
    """Check if a specific interpreter is available for a given date and time range.
    Checks against existing confirmed assignments to detect scheduling conflicts.

    Args:
        interpreter_id: The interpreter's ID
        date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
    """
    return _run_async(_check_availability(interpreter_id, date, start_time, end_time))


def get_client_info(client_email: str) -> dict:
    """Look up a client by their email address. Returns company name,
    contact info, and account status.

    Args:
        client_email: The client's email address
    """
    result = _run_async(_get_client_info(client_email))
    if result:
        return {"status": "success", "client": result}
    return {"status": "error", "error_message": f"No client found with email {client_email}"}


def get_today_assignments() -> dict:
    """Get all assignments scheduled for today with their status,
    interpreter, client, and location details."""
    results = _run_async(_get_today_assignments())
    return {"status": "success", "count": len(results), "assignments": results}


def get_pending_requests() -> dict:
    """Get all pending quote requests and public quote requests
    that haven't been processed yet."""
    results = _run_async(_get_pending_requests())
    return {"status": "success", "count": len(results), "requests": results}
