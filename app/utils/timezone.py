"""
Timezone utilities for JHBridge.

Interpreters operate across all US states.  This module provides a single
source of truth for state → timezone mapping so that every part of the
codebase (admin, API, services) formats datetimes in the interpreter's
local time rather than always defaulting to Boston / America/New_York.
"""
import pytz
from django.utils import timezone as dj_timezone

# ---------------------------------------------------------------------------
# State → IANA timezone mapping (all 50 states + DC)
# ---------------------------------------------------------------------------
STATE_TIMEZONES: dict[str, str] = {
    # Eastern
    'CT': 'America/New_York',
    'DC': 'America/New_York',
    'DE': 'America/New_York',
    'FL': 'America/New_York',
    'GA': 'America/New_York',
    'IN': 'America/New_York',
    'KY': 'America/New_York',  # most of KY is Eastern
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
    'TN': 'America/New_York',  # most of TN is Eastern
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
    'AZ': 'America/Phoenix',   # Arizona observes no DST
    # Pacific
    'CA': 'America/Los_Angeles',
    'NV': 'America/Los_Angeles',
    'OR': 'America/Los_Angeles',
    'WA': 'America/Los_Angeles',
    # Other
    'AK': 'America/Anchorage',
    'HI': 'Pacific/Honolulu',
}

DEFAULT_TZ_NAME = 'America/New_York'  # fallback (Boston / Eastern)

# Pre-built objects for the two most common aliases so callers can import them
# and stay backward-compatible.
BOSTON_TZ = pytz.timezone(DEFAULT_TZ_NAME)
DEFAULT_TZ = BOSTON_TZ


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_timezone_for_state(state: str) -> pytz.BaseTzInfo:
    """Return the pytz timezone object for a US state abbreviation.

    Falls back to Eastern time when the state is unknown or empty.

    Args:
        state: Two-letter US state abbreviation (case-insensitive), e.g. 'CA'.

    Returns:
        A pytz timezone object.
    """
    tz_name = STATE_TIMEZONES.get((state or '').upper().strip(), DEFAULT_TZ_NAME)
    return pytz.timezone(tz_name)


def get_interpreter_timezone(interpreter) -> pytz.BaseTzInfo:
    """Return the local timezone for an Interpreter model instance.

    Reads ``interpreter.state``; falls back to Eastern time when absent.

    Args:
        interpreter: An ``app.models.Interpreter`` instance (or any object
            with a ``state`` string attribute).

    Returns:
        A pytz timezone object.
    """
    state = getattr(interpreter, 'state', None) or ''
    return get_timezone_for_state(state)


def format_local_datetime(dt, tz: pytz.BaseTzInfo) -> str:
    """Convert a UTC-stored datetime to a local string.

    Args:
        dt: An aware ``datetime`` (stored in UTC by Django).
        tz: Target pytz timezone.

    Returns:
        Formatted string like ``"03/25/2025 02:30 PM EDT"`` or ``""`` if *dt*
        is falsy.
    """
    if not dt:
        return ''
    local_dt = dj_timezone.localtime(dt, tz)
    return local_dt.strftime('%m/%d/%Y %I:%M %p %Z')


def format_datetime_for_state(dt, state: str) -> str:
    """Convenience wrapper: format *dt* in the timezone of *state*.

    Args:
        dt: An aware datetime (UTC).
        state: Two-letter US state abbreviation.

    Returns:
        Formatted local datetime string.
    """
    return format_local_datetime(dt, get_timezone_for_state(state))


def format_datetime_for_interpreter(dt, interpreter) -> str:
    """Convenience wrapper: format *dt* in the interpreter's local timezone.

    Args:
        dt: An aware datetime (UTC).
        interpreter: An ``app.models.Interpreter`` instance.

    Returns:
        Formatted local datetime string.
    """
    return format_local_datetime(dt, get_interpreter_timezone(interpreter))


# ---------------------------------------------------------------------------
# Backward-compatibility alias (used by app/admin/utils.py and the mixin)
# ---------------------------------------------------------------------------

def format_boston_datetime(dt) -> str:
    """Format *dt* in Eastern time (America/New_York).

    Kept for backward compatibility.  New code should prefer
    :func:`format_datetime_for_state` or :func:`format_datetime_for_interpreter`.
    """
    return format_local_datetime(dt, BOSTON_TZ)


# ---------------------------------------------------------------------------
# Legacy Massachusetts classes (kept so existing imports don't break)
# ---------------------------------------------------------------------------
from django import forms
from django.forms.widgets import DateTimeInput, DateInput, TimeInput


class MassachusettsTimezoneMixin:
    """Mixin that exposes Massachusetts timezone helpers (legacy)."""

    MASSACHUSETTS_TIMEZONE = DEFAULT_TZ_NAME

    @classmethod
    def get_current_ma_time(cls):
        ma_tz = pytz.timezone(cls.MASSACHUSETTS_TIMEZONE)
        return dj_timezone.now().astimezone(ma_tz)

    @classmethod
    def get_timezone_suffix(cls):
        ma_time = cls.get_current_ma_time()
        return 'EDT' if ma_time.dst() else 'EST'

    @classmethod
    def to_ma_time(cls, dt):
        if dt is None:
            return None
        ma_tz = pytz.timezone(cls.MASSACHUSETTS_TIMEZONE)
        if dj_timezone.is_naive(dt):
            dt = ma_tz.localize(dt)
        return dt.astimezone(ma_tz)

    @classmethod
    def from_ma_time(cls, dt):
        if dt is None:
            return None
        ma_tz = pytz.timezone(cls.MASSACHUSETTS_TIMEZONE)
        if dj_timezone.is_naive(dt):
            dt = ma_tz.localize(dt)
        return dt.astimezone(pytz.UTC)


class MassachusettsDateTimeWidget(DateTimeInput):
    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.update({
            'class': 'massachusetts-datetime',
            'pattern': r'\d{2}/\d{2}/\d{4} \d{1,2}:\d{2} [AaPp][Mm]',
            'placeholder': 'MM/DD/YYYY HH:MM AM/PM',
        })
        super().__init__(attrs, format='%m/%d/%Y %I:%M %p')


class MassachusettsDateWidget(DateInput):
    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.update({
            'class': 'massachusetts-date',
            'pattern': r'\d{2}/\d{2}/\d{4}',
            'placeholder': 'MM/DD/YYYY',
        })
        super().__init__(attrs, format='%m/%d/%Y')


class MassachusettsTimeWidget(TimeInput):
    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.update({
            'class': 'massachusetts-time',
            'pattern': r'\d{1,2}:\d{2} [AaPp][Mm]',
            'placeholder': 'HH:MM AM/PM',
        })
        super().__init__(attrs, format='%I:%M %p')


class MassachusettsFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _name, field in self.fields.items():
            if isinstance(field, forms.DateTimeField):
                field.widget = MassachusettsDateTimeWidget()
            elif isinstance(field, forms.DateField):
                field.widget = MassachusettsDateWidget()
            elif isinstance(field, forms.TimeField):
                field.widget = MassachusettsTimeWidget()


class MassachusettsModelFormMixin(MassachusettsFormMixin):
    def clean(self):
        cleaned_data = super().clean()
        ma_tz = pytz.timezone(MassachusettsTimezoneMixin.MASSACHUSETTS_TIMEZONE)
        for field_name, value in cleaned_data.items():
            field = self.fields.get(field_name)
            if isinstance(field, forms.DateTimeField) and value is not None:
                if dj_timezone.is_naive(value):
                    cleaned_data[field_name] = ma_tz.localize(value)
                else:
                    cleaned_data[field_name] = value.astimezone(ma_tz)
        return cleaned_data


def format_ma_datetime(dt):
    if dt is None:
        return ''
    ma_time = MassachusettsTimezoneMixin.to_ma_time(dt)
    tz_suffix = 'EDT' if ma_time.dst() else 'EST'
    return ma_time.strftime(f'%m/%d/%Y %I:%M %p {tz_suffix}')


def format_ma_date(dt):
    if dt is None:
        return ''
    ma_time = MassachusettsTimezoneMixin.to_ma_time(dt)
    return ma_time.strftime('%m/%d/%Y')


def format_ma_time(dt):
    if dt is None:
        return ''
    ma_time = MassachusettsTimezoneMixin.to_ma_time(dt)
    tz_suffix = 'EDT' if ma_time.dst() else 'EST'
    return ma_time.strftime(f'%I:%M %p {tz_suffix}')
