"""Invoice generation utilities."""
import random
from django.utils import timezone
from app.models import Invoice


def generate_invoice_number():
    """Generate unique invoice number like INV-2026-XXXXX."""
    year = timezone.now().year
    while True:
        random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        inv_num = f"INV-{year}-{random_part}"
        if not Invoice.objects.filter(invoice_number=inv_num).exists():
            return inv_num
