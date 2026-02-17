# app/forms/__init__.py

# Auth
from .auth import (
    LoginForm,
    ClientRegistrationForm1,
    ClientRegistrationForm2,
    InterpreterRegistrationForm1,
    InterpreterRegistrationForm2,
    InterpreterRegistrationForm3,
    CustomPasswordResetForm,
    CustomPasswordChangeForm,
    CustomPasswordtradChangeForm
)

# Profiles
from .profiles import (
    UserProfileForm,
    ClientProfileForm,
    ClientProfileUpdateForm,
    InterpreterProfileForm,
    NotificationPreferencesForm,
    NotificationPreferenceForm
)

# Assignments
from .assignments import (
    PublicQuoteRequestForm,
    QuoteRequestForm,
    QuoteRequestUpdateForm,
    AssignmentFeedbackForm,
    QuoteFilterForm
)

# Finance
from .finance import (
    PayrollDocumentForm,
    ServiceForm,
    ServiceFormSet,
    ReimbursementForm,
    DeductionForm,
    ReimbursementFormSet,
    DeductionFormSet
)

# Communication
from .communication import (
    ContactForm
)
