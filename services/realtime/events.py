"""
Event type enums and channel definitions for WebSocket real-time system.
"""
from enum import Enum


class EventType(str, Enum):
    # Email events
    NEW_EMAIL = "NEW_EMAIL"
    EMAIL_CLASSIFIED = "EMAIL_CLASSIFIED"
    EMAIL_REPLY_SENT = "EMAIL_REPLY_SENT"

    # Assignment events
    ASSIGNMENT_CREATED = "ASSIGNMENT_CREATED"
    ASSIGNMENT_CONFIRMED = "ASSIGNMENT_CONFIRMED"
    ASSIGNMENT_CANCELLED = "ASSIGNMENT_CANCELLED"
    ASSIGNMENT_STATUS_CHANGED = "ASSIGNMENT_STATUS_CHANGED"
    ASSIGNMENT_COMPLETED = "ASSIGNMENT_COMPLETED"

    # Interpreter events
    INTERPRETER_LOCATION_UPDATE = "INTERPRETER_LOCATION_UPDATE"
    INTERPRETER_ACCEPTED = "INTERPRETER_ACCEPTED"
    INTERPRETER_DECLINED = "INTERPRETER_DECLINED"

    # Quote events
    QUOTE_REQUEST_RECEIVED = "QUOTE_REQUEST_RECEIVED"
    QUOTE_SENT = "QUOTE_SENT"

    # Onboarding events
    ONBOARDING_STARTED = "ONBOARDING_STARTED"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"

    # System events
    NOTIFICATION = "NOTIFICATION"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class Channel(str, Enum):
    """WebSocket channels that clients can subscribe to."""
    NOTIFICATIONS = "notifications"
    LIVE_TRACKING = "live-tracking"
    ASSIGNMENT_UPDATES = "assignment-updates"
    EMAIL_UPDATES = "email-updates"


# Redis pub/sub channel names
REDIS_CHANNELS = {
    Channel.NOTIFICATIONS: "jhbridge:notifications",
    Channel.LIVE_TRACKING: "jhbridge:tracking",
    Channel.ASSIGNMENT_UPDATES: "jhbridge:assignments",
    Channel.EMAIL_UPDATES: "jhbridge:emails",
}
