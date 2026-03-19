"""Shared unique reference/document number generator."""
import random

from django.utils import timezone


def generate_unique_reference(prefix, model_class, field_name='reference_number'):
    """Generate a unique reference like PREFIX-YYYY-XXXXX.

    Loops until a non-colliding value is found by checking the DB.

    Args:
        prefix: Short string prefix (e.g. 'QT', 'INV', 'PS').
        model_class: Django model class to check uniqueness against.
        field_name: The model field that must be unique.

    Returns:
        A unique reference string.
    """
    year = timezone.now().year
    while True:
        random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        ref = f"{prefix}-{year}-{random_part}"
        if not model_class.objects.filter(**{field_name: ref}).exists():
            return ref
