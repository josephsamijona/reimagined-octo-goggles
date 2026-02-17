from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from app.models import (
    QuoteRequest, 
    PublicQuoteRequest, 
    ServiceType, 
    Language,
    AssignmentFeedback
)

class PublicQuoteRequestForm(forms.ModelForm):
    class Meta:
        model = PublicQuoteRequest
        fields = [
            'full_name', 'email', 'phone', 'company_name',
            'source_language', 'target_language', 'service_type',
            'requested_date', 'duration', 'location', 'city', 
            'state', 'zip_code', 'special_requirements'
        ]
        widgets = {
            'requested_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'special_requirements': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Please provide any additional details or special requirements...'
                }
            ),
            'full_name': forms.TextInput(
                attrs={'placeholder': 'Enter your full name'}
            ),
            'email': forms.EmailInput(
                attrs={'placeholder': 'Enter your email address'}
            ),
            'phone': forms.TextInput(
                attrs={'placeholder': '(123) 456-7890'}
            ),
            'company_name': forms.TextInput(
                attrs={'placeholder': 'Enter your company name'}
            ),
            'location': forms.TextInput(
                attrs={'placeholder': 'Enter the service location'}
            ),
            'duration': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter duration in minutes',
                    'min': '30',
                    'step': '15'
                }
            ),
            'service_type': forms.Select(
                attrs={'class': 'form-control'}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required except special_requirements
        for field_name, field in self.fields.items():
            if field_name != 'special_requirements':
                field.required = True
        
        # Only show active services in the dropdown
        self.fields['service_type'].queryset = ServiceType.objects.filter(active=True)
        
        # Optional: Customize the empty label
        self.fields['service_type'].empty_label = "Select a service type"

class QuoteRequestForm(forms.ModelForm):
    """
    Form for creating a new quote request
    """
    requested_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'min': datetime.now().strftime('%Y-%m-%dT%H:%M'),
        }),
        help_text="Select your preferred date and time for interpretation"
    )

    duration = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '30',
            'step': '30',
            'placeholder': '120'
        }),
        help_text="Minimum duration is 30 minutes, in 30-minute increments"
    )

    class Meta:
        model = QuoteRequest
        fields = [
            'service_type',
            'requested_date',
            'duration',
            'location',
            'city',
            'state',
            'zip_code',
            'source_language',
            'target_language',
            'special_requirements'
        ]
        widgets = {
            'service_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the complete address for interpretation'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP Code'
            }),
            'source_language': forms.Select(attrs={
                'class': 'form-control'
            }),
            'target_language': forms.Select(attrs={
                'class': 'form-control'
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please specify any special requirements or notes...'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter active service types
        self.fields['service_type'].queryset = ServiceType.objects.filter(active=True)
        
        # Filter active languages
        active_languages = Language.objects.filter(is_active=True)
        self.fields['source_language'].queryset = active_languages
        self.fields['target_language'].queryset = active_languages

        # Set preferred language if available
        if user and hasattr(user, 'client_profile'):
            preferred_language = user.client_profile.preferred_language
            if preferred_language:
                self.fields['source_language'].initial = preferred_language

    def clean(self):
        cleaned_data = super().clean()
        requested_date = cleaned_data.get('requested_date')
        duration = cleaned_data.get('duration')
        source_language = cleaned_data.get('source_language')
        target_language = cleaned_data.get('target_language')

        # Date validation
        if requested_date:
            min_notice = timezone.now() + timedelta(hours=24)
            if requested_date < min_notice:
                raise ValidationError(
                    "Requests must be made at least 24 hours in advance"
                )

        # Duration validation
        if duration:
            if duration < 30:
                raise ValidationError(
                    "Minimum duration is 30 minutes"
                )
            if duration % 30 != 0:
                raise ValidationError(
                    "Duration must be in 30-minute increments"
                )

        # Language validation
        if source_language and target_language and source_language == target_language:
            raise ValidationError(
                "Source and target languages must be different"
            )

        return cleaned_data

class QuoteRequestUpdateForm(forms.ModelForm):
    """
    Form for updating an existing quote request (limited fields)
    """
    class Meta:
        model = QuoteRequest
        fields = ['special_requirements']
        widgets = {
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Update your special requirements or notes...'
            })
        }

class AssignmentFeedbackForm(forms.ModelForm):
    """
    Form for providing feedback on completed assignments
    """
    class Meta:
        model = AssignmentFeedback
        fields = ['rating', 'comments']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '1'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with the interpretation service...'
            })
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5 stars")
        return rating

class QuoteFilterForm(forms.Form):
    """Formulaire pour filtrer les quotes"""
    STATUS_CHOICES = [('', 'All Status')] + list(QuoteRequest.Status.choices)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(active=True),
        required=False,
        empty_label="All Services",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
