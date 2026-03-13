from django import forms
from app.models import (
    User,
    Client,
    Interpreter,
    NotificationPreference,
    Language
)

class UserProfileForm(forms.ModelForm):
    """Form for updating user's basic information"""
    first_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your first name'
    }))
    last_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your last name'
    }))
    phone = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your phone number'
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone']

class ClientProfileForm(forms.ModelForm):
    """Form for updating client's company information"""
    class Meta:
        model = Client
        exclude = ['user', 'credit_limit', 'active']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter city'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter state'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ZIP code'
            }),
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter billing address'
            }),
            'billing_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter billing city'
            }),
            'billing_state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter billing state'
            }),
            'billing_zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter billing ZIP code'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tax ID'
            }),
            'preferred_language': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes'
            })
        }

class ClientProfileUpdateForm(forms.ModelForm):
    """Form for updating client profile"""
    class Meta:
        model = Client
        exclude = ['user', 'created_at', 'active']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_address': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_city': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_state': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_language': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class InterpreterProfileForm(forms.ModelForm):
    # Champs de base (liés au User ou au profil Interprète)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=15)

    # Champs bancaires
    bank_name = forms.CharField(max_length=100)
    account_holder = forms.CharField(max_length=100)
    account_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'type': 'password',
            'class': 'sensitive-field'
        })
    )
    routing_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'type': 'password',
            'class': 'sensitive-field'
        })
    )

    class Meta:
        model = Interpreter
        fields = [
            'profile_image',
            'address',
            'city',
            'state',
            'zip_code',
            'bio'
        ]

    def __init__(self, *args, **kwargs):
        # Récupérer l'utilisateur passé en paramètre (dans la view)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Préremplir certains champs si on a un user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['phone_number'].initial = user.phone

            interpreter = getattr(user, 'interpreter_profile', None)
            if interpreter:
                self.fields['bank_name'].initial = interpreter.bank_name
                self.fields['account_holder'].initial = interpreter.account_holder_name
                self.fields['account_number'].initial = interpreter.account_number
                self.fields['routing_number'].initial = interpreter.routing_number

class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user']
        widgets = {
            'email_quote_updates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_assignment_updates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_payment_updates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'quote_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'assignment_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'payment_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'system_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notification_frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'preferred_language': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['preferred_language'].queryset = Language.objects.filter(is_active=True)

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user']
        widgets = {
            'preferred_language': forms.Select(attrs={'class': 'form-control'}),
            'notification_frequency': forms.Select(attrs={'class': 'form-control'}),
        }
