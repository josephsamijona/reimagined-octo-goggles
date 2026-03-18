"""
GPS tracking HTTP endpoints — interpreters POST location updates,
dispatchers GET live positions.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from services.db.database import async_session_factory
from services.db import queries
from services.realtime.events import Channel, EventType
from services.schemas.tracking import LocationUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["GPS Tracking"])

# References set at startup
_manager = None
_broadcaster = None


def set_tracking_deps(manager, broadcaster=None):
    global _manager, _broadcaster
    _manager = manager
    _broadcaster = broadcaster


@router.post("/update")
async def update_location(loc: LocationUpdate):
    """Receive a GPS update from an interpreter's device, save to DB,
    and broadcast to the live-tracking WebSocket channel."""

    async with async_session_factory() as db:
        loc_id = await queries.save_interpreter_location(db, {
            "interpreter_id": loc.interpreter_id,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "accuracy": loc.accuracy,
            "is_on_mission": loc.is_on_mission,
            "current_assignment_id": loc.current_assignment_id,
            "timestamp": datetime.now(timezone.utc),
        })

    # Broadcast to WS live-tracking channel
    if _manager:
        await _manager.broadcast(Channel.LIVE_TRACKING, {
            "type": EventType.INTERPRETER_LOCATION_UPDATE,
            "payload": {
                "id": loc_id,
                "interpreter_id": loc.interpreter_id,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "accuracy": loc.accuracy,
                "is_on_mission": loc.is_on_mission,
                "current_assignment_id": loc.current_assignment_id,
            },
        })

    # Also publish to Redis for cross-service consumption
    if _broadcaster:
        await _broadcaster.publish_event(Channel.LIVE_TRACKING, {
            "type": EventType.INTERPRETER_LOCATION_UPDATE,
            "interpreter_id": loc.interpreter_id,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
        })

    return {"status": "ok", "id": loc_id}


@router.get("/live")
async def get_live_positions():
    """Get the latest position of every active interpreter."""
    async with async_session_factory() as db:
        positions = await queries.get_latest_interpreter_locations(db)
    return {"count": len(positions), "positions": positions}
