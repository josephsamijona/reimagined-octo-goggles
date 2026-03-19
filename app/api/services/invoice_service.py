"""Invoice generation utilities."""
from app.api.services.reference_service import generate_unique_reference
from app.models import Invoice


def generate_invoice_number():
    """Generate unique invoice number like INV-2026-XXXXX."""
    return generate_unique_reference('INV', Invoice, 'invoice_number')
