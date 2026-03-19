"""
API URL Configuration for JHBridge Translation Platform.
All endpoints are prefixed with /api/v1/ (set in config/urls.py).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from app.api.viewsets.auth import LoginView, TokenRefreshView, MeView
from app.api.viewsets.dashboard import DashboardViewSet
from app.api.viewsets.assignments import AssignmentViewSet
from app.api.viewsets.interpreters import InterpreterViewSet
from app.api.viewsets.clients import ClientViewSet
from app.api.viewsets.quotes import QuoteRequestViewSet, QuoteViewSet, PublicQuoteRequestViewSet
from app.api.viewsets.finance import FinanceViewSet
from app.api.viewsets.payroll import PayrollViewSet
from app.api.viewsets.onboarding import OnboardingViewSet
from app.api.viewsets.notifications import NotificationViewSet
from app.api.viewsets.marketing import LeadViewSet, CampaignViewSet, MarketingAnalyticsViewSet
from app.api.viewsets.audit import AuditLogViewSet
from app.api.viewsets.settings import (
    ServiceTypeViewSet, LanguageViewSet, CompanyInfoView, APIKeyViewSet,
)

app_name = 'api'

router = DefaultRouter()

# ── Core resources ──────────────────────────────────────────────
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'interpreters', InterpreterViewSet, basename='interpreter')
router.register(r'clients', ClientViewSet, basename='client')

# ── Quotes ──────────────────────────────────────────────────────
router.register(r'quote-requests', QuoteRequestViewSet, basename='quote-request')
router.register(r'quotes', QuoteViewSet, basename='quote')
router.register(r'public-quotes', PublicQuoteRequestViewSet, basename='public-quote')

# ── Finance ─────────────────────────────────────────────────────
router.register(r'finance', FinanceViewSet, basename='finance')
router.register(r'payroll', PayrollViewSet, basename='payroll')

# ── Onboarding ──────────────────────────────────────────────────
router.register(r'onboarding', OnboardingViewSet, basename='onboarding')

# ── Communication ───────────────────────────────────────────────
router.register(r'notifications', NotificationViewSet, basename='notification')

# ── Marketing ───────────────────────────────────────────────────
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'marketing-analytics', MarketingAnalyticsViewSet, basename='marketing-analytics')

# ── Settings ────────────────────────────────────────────────────
router.register(r'service-types', ServiceTypeViewSet, basename='service-type')
router.register(r'languages', LanguageViewSet, basename='language')
router.register(r'api-keys', APIKeyViewSet, basename='api-key')

# ── Security / Audit ────────────────────────────────────────────
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    # ── Auth endpoints (non-router) ─────────────────────────────
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='me'),

    # ── Dashboard (non-router, single viewset actions) ──────────
    path('dashboard/kpis/', DashboardViewSet.as_view({'get': 'kpis'}), name='dashboard-kpis'),
    path('dashboard/alerts/', DashboardViewSet.as_view({'get': 'alerts'}), name='dashboard-alerts'),
    path('dashboard/revenue-chart/', DashboardViewSet.as_view({'get': 'revenue_chart'}), name='dashboard-revenue-chart'),
    path('dashboard/today-missions/', DashboardViewSet.as_view({'get': 'today_missions'}), name='dashboard-today-missions'),
    path('dashboard/payroll-kpis/', DashboardViewSet.as_view({'get': 'payroll_kpis'}), name='dashboard-payroll-kpis'),
    path('dashboard/quote-pipeline-summary/', DashboardViewSet.as_view({'get': 'quote_pipeline_summary'}), name='dashboard-quote-pipeline'),

    # ── Settings (non-router) ───────────────────────────────────
    path('settings/company/', CompanyInfoView.as_view(), name='settings-company'),

    # ── Router-generated URLs ───────────────────────────────────
    path('', include(router.urls)),
]
