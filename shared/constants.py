"""
Shared constants importable by both the Django app and the FastAPI microservice.
No Django or FastAPI dependency — pure Python only.
"""

# ---------------------------------------------------------------------------
# US state → IANA timezone mapping (all 50 states + DC)
# ---------------------------------------------------------------------------
# Kept in sync with app/utils/timezone.py STATE_TIMEZONES.
# FastAPI services import this directly; Django app wraps it with helpers.

STATE_TIMEZONES: dict[str, str] = {
    # Eastern
    'CT': 'America/New_York',
    'DC': 'America/New_York',
    'DE': 'America/New_York',
    'FL': 'America/New_York',
    'GA': 'America/New_York',
    'IN': 'America/New_York',
    'KY': 'America/New_York',
    'MA': 'America/New_York',
    'MD': 'America/New_York',
    'ME': 'America/New_York',
    'MI': 'America/New_York',
    'NC': 'America/New_York',
    'NH': 'America/New_York',
    'NJ': 'America/New_York',
    'NY': 'America/New_York',
    'OH': 'America/New_York',
    'PA': 'America/New_York',
    'RI': 'America/New_York',
    'SC': 'America/New_York',
    'TN': 'America/New_York',
    'VA': 'America/New_York',
    'VT': 'America/New_York',
    'WV': 'America/New_York',
    # Central
    'AL': 'America/Chicago',
    'AR': 'America/Chicago',
    'IA': 'America/Chicago',
    'IL': 'America/Chicago',
    'KS': 'America/Chicago',
    'LA': 'America/Chicago',
    'MN': 'America/Chicago',
    'MO': 'America/Chicago',
    'MS': 'America/Chicago',
    'ND': 'America/Chicago',
    'NE': 'America/Chicago',
    'OK': 'America/Chicago',
    'SD': 'America/Chicago',
    'TX': 'America/Chicago',
    'WI': 'America/Chicago',
    # Mountain
    'CO': 'America/Denver',
    'ID': 'America/Denver',
    'MT': 'America/Denver',
    'NM': 'America/Denver',
    'UT': 'America/Denver',
    'WY': 'America/Denver',
    'AZ': 'America/Phoenix',   # No DST
    # Pacific
    'CA': 'America/Los_Angeles',
    'NV': 'America/Los_Angeles',
    'OR': 'America/Los_Angeles',
    'WA': 'America/Los_Angeles',
    # Other
    'AK': 'America/Anchorage',
    'HI': 'Pacific/Honolulu',
}

DEFAULT_TZ_NAME = 'America/New_York'


def tz_for_state(state: str) -> str:
    """Return IANA timezone name for a US state abbreviation (case-insensitive).

    Falls back to Eastern time for unknown/empty states.
    """
    return STATE_TIMEZONES.get((state or '').upper().strip(), DEFAULT_TZ_NAME)
