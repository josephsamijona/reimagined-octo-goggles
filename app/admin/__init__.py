from django.contrib import admin
from .users import CustomUserAdmin, ClientAdmin, InterpreterAdmin
from .languages import LanguageAdmin
from .services import ServiceTypeAdmin, QuoteRequestAdmin, QuoteAdmin, AssignmentAdmin, PublicQuoteRequestAdmin
from .finance import FinancialTransactionAdmin, ClientPaymentAdmin, InterpreterPaymentAdmin, ExpenseAdmin, PayrollDocumentAdmin, ServiceAdmin, ReimbursementAdmin, DeductionAdmin, PaymentAdmin
from .communication import NotificationAdmin, ContactMessageAdmin
from .security import AuditLogAdmin, APIKeyAdmin, PGPKeyAdmin
from .documents import InterpreterContractSignatureAdmin, DocumentAdmin
from .contracts import ContractInvitationAdmin

# =======================================================
# CONFIGURATION DU SITE ADMIN
# =======================================================
admin.site.site_header = "JHBRIDGE Administration"
admin.site.site_title = "JHBRIDGE Admin Portal"
admin.site.index_title = "Welcome to JHBRIDGE Administration"
