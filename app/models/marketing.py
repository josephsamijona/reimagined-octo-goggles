from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import decimal
from decimal import Decimal




# app/models/marketing.py — NOUVEAU FICHIER

class Lead(models.Model):
    class Source(models.TextChoices):
        WEBSITE = 'WEBSITE'
        REFERRAL = 'REFERRAL'
        GOOGLE_ADS = 'GOOGLE_ADS'
        LINKEDIN = 'LINKEDIN'
        EMAIL_CAMPAIGN = 'EMAIL_CAMPAIGN'
        COLD_CALL = 'COLD_CALL'
        OTHER = 'OTHER'

    class Stage(models.TextChoices):
        NEW = 'NEW'
        CONTACTED = 'CONTACTED'
        QUOTE_SENT = 'QUOTE_SENT'
        NEGOTIATING = 'NEGOTIATING'
        CONVERTED = 'CONVERTED'
        LOST = 'LOST'

    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    source = models.CharField(max_length=20, choices=Source.choices)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    
    languages_needed = models.ManyToManyField('Language', blank=True)
    estimated_monthly_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    # Conversion
    converted_client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    # Linked sources
    public_quote_request = models.ForeignKey('PublicQuoteRequest', on_delete=models.SET_NULL, null=True, blank=True)
    contact_message = models.ForeignKey('ContactMessage', on_delete=models.SET_NULL, null=True, blank=True)
    
    assigned_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
# app/models/marketing.py — AJOUTER

class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT'
        ACTIVE = 'ACTIVE'
        PAUSED = 'PAUSED'
        COMPLETED = 'COMPLETED'

    class Channel(models.TextChoices):
        GOOGLE_ADS = 'GOOGLE_ADS'
        LINKEDIN = 'LINKEDIN'
        EMAIL = 'EMAIL'
        SOCIAL_MEDIA = 'SOCIAL_MEDIA'
        REFERRAL_PROGRAM = 'REFERRAL_PROGRAM'
        OTHER = 'OTHER'

    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    leads_generated = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)