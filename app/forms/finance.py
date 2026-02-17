from django import forms
from django.forms import modelformset_factory
from app.models import (
    PayrollDocument, 
    Service, 
    Reimbursement, 
    Deduction
)

class PayrollDocumentForm(forms.ModelForm):
    class Meta:
        model = PayrollDocument
        fields = [
            'company_address', 
            'company_phone', 
            'company_email',
            'interpreter_name', 
            'interpreter_address', 
            'interpreter_phone', 
            'interpreter_email'
        ]
        widgets = {
            'company_address': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': '500 GROSSMAN DR, BRAINTREE, MA, 02184'
            }),
            'company_phone': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': '+1 (774) 223 8771'
            }),
            'company_email': forms.EmailInput(attrs={
                'class': 'form-input', 
                'placeholder': 'jhbridgetranslation@gmail.com'
            }),
            'interpreter_name': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': "Interpreter's name"
            }),
            'interpreter_address': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': "Interpreter's address"
            }),
            'interpreter_phone': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': "Interpreter's phone"
            }),
            'interpreter_email': forms.EmailInput(attrs={
                'class': 'form-input', 
                'placeholder': "Interpreter's email"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Set default company information if not provided
        if not cleaned_data.get('company_address'):
            cleaned_data['company_address'] = '500 GROSSMAN DR, BRAINTREE, MA, 02184'
        if not cleaned_data.get('company_phone'):
            cleaned_data['company_phone'] = '+1 (774) 223 8771'
        if not cleaned_data.get('company_email'):
            cleaned_data['company_email'] = 'jhbridgetranslation@gmail.com'
        return cleaned_data

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['date', 'client', 'source_language', 'target_language', 'duration', 'rate']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-input'
            }),
            'client': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Client name'
            }),
            'source_language': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Source language'
            }),
            'target_language': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Target language'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.5',
                'placeholder': 'Duration in hours'
            }),
            'rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Hourly rate'
            }),
        }

ServiceFormSet = modelformset_factory(
    Service,
    form=ServiceForm,
    extra=1,
    can_delete=True
)

class ReimbursementForm(forms.ModelForm):
    class Meta:
        model = Reimbursement
        fields = ['date', 'reimbursement_type', 'description', 'amount', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-input'
            }),
            'reimbursement_type': forms.Select(attrs={
                'class': 'form-input',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Description'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': 'Amount'
            }),
            'receipt': forms.ClearableFileInput(attrs={
                'class': 'form-input'
            }),
        }

class DeductionForm(forms.ModelForm):
    class Meta:
        model = Deduction
        fields = ['date', 'deduction_type', 'description', 'amount']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-input'
            }),
            'deduction_type': forms.Select(attrs={
                'class': 'form-input',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Description'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': 'Amount'
            }),
        }

# Créer des formsets pour les remboursements et déductions
ReimbursementFormSet = modelformset_factory(
    Reimbursement,
    form=ReimbursementForm,
    extra=1,
    can_delete=True
)

DeductionFormSet = modelformset_factory(
    Deduction,
    form=DeductionForm,
    extra=1,
    can_delete=True
)
