"""
FastAPI microservice — AI Agent, Gmail, Calendar, WebSocket real-time.
Assembles all routers, middleware, and background tasks.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle for the FastAPI app."""
    settings = get_settings()

    # ── Logging ───────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting JHBridge services...")

    # ── Database ──────────────────────────────────────────────────
    from services.db.database import init_db, close_db
    await init_db()

    # ── WebSocket manager ─────────────────────────────────────────
    from services.realtime.manager import ConnectionManager
    ws_manager = ConnectionManager()

    from services.realtime.router import set_manager
    set_manager(ws_manager)

    # ── Redis broadcaster ─────────────────────────────────────────
    from services.realtime.broadcaster import RedisBroadcaster
    broadcaster = RedisBroadcaster(ws_manager)
    redis_task = None
    try:
        await broadcaster.connect()
        redis_task = asyncio.create_task(broadcaster.run_listener_loop())
        logger.info("Redis broadcaster started")
    except Exception as e:
        logger.warning(f"Redis not available, WS broadcast via local only: {e}")
        broadcaster = None

    # ── Tracking deps ─────────────────────────────────────────────
    from services.realtime.tracking import set_tracking_deps
    set_tracking_deps(ws_manager, broadcaster)

    # ── Gmail client ──────────────────────────────────────────────
    from services.gmail.client import GmailClient
    gmail_client = GmailClient()
    try:
        gmail_client.authenticate()
        logger.info("Gmail client ready")
    except Exception as e:
        logger.warning(f"Gmail authentication failed: {e}")

    from services.gmail.router import set_gmail_client
    set_gmail_client(gmail_client)

    # Inject into ADK gmail tools
    from services.adk_agents.tools import gmail_tools, gmail_label_tools
    gmail_tools._gmail_client = gmail_client
    gmail_label_tools._gmail_client = gmail_client

    # ── Gmail background sync ─────────────────────────────────────
    from services.gmail.sync import configure_sync, run_sync_loop
    configure_sync(gmail_client, broadcaster)
    sync_task = asyncio.create_task(run_sync_loop())

    # ── Calendar client ───────────────────────────────────────────
    from services.calendar_sync.client import CalendarClient
    calendar_client = CalendarClient()
    try:
        calendar_client.authenticate()
        logger.info("Calendar client ready")
    except Exception as e:
        logger.warning(f"Calendar authentication failed: {e}")

    from services.calendar_sync.router import set_calendar_client
    set_calendar_client(calendar_client)

    # Inject into ADK calendar tools
    from services.adk_agents.tools import calendar_tools
    calendar_tools._calendar_client = calendar_client

    logger.info("JHBridge services startup complete")

    yield  # ── App is running ─────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────
    logger.info("Shutting down JHBridge services...")
    sync_task.cancel()
    if redis_task:
        redis_task.cancel()
    if broadcaster:
        await broadcaster.disconnect()
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="JHBridge Services",
        description="AI Agent, Gmail, Calendar, and Real-time WebSocket microservice",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────
    from services.ai_agent.router import router as ai_router
    from services.ai_agent.queue_router import router as queue_router
    from services.ai_agent.queue_router import init_runner, set_db_factory as queue_set_db
    from services.gmail.router import router as gmail_router
    from services.calendar_sync.router import router as calendar_router
    from services.realtime.router import router as ws_router
    from services.realtime.tracking import router as tracking_router

    # Wire queue router: agent runner + db
    from services.adk_agents.jhbridge_agent import root_agent
    from services.db.database import async_session_factory
    init_runner(root_agent)
    queue_set_db(async_session_factory)

    app.include_router(ai_router)
    app.include_router(queue_router)
    app.include_router(gmail_router)
    app.include_router(calendar_router)
    app.include_router(ws_router)
    app.include_router(tracking_router)

    # ── Health check ──────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "service": "jhbridge-services"}

    return app


app = create_app()
