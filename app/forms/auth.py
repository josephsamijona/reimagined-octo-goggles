from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm, 
    PasswordResetForm, 
    PasswordChangeForm,
    UserCreationForm, 
    UserChangeForm
)
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from app.models import User, Client, Interpreter, Language

class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password'
    }))

    def clean(self):
        # Récupère l'email entré par l'utilisateur
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            # Cherche l'utilisateur par email
            try:
                user = User.objects.get(email=email)
                # Met à jour le username avec celui trouvé
                self.cleaned_data['username'] = user.username
                # Authentifie avec le username réel
                self.user_cache = authenticate(self.request, username=user.username, password=password)
                if self.user_cache is None:
                    raise forms.ValidationError("Invalid email or password.")
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")

        return self.cleaned_data

class ClientRegistrationForm1(forms.ModelForm):
    """First step: Basic user information"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose your username'
        })
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            })
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken")
        
        # Vérifier le format du username
        if not username.isalnum():
            raise forms.ValidationError("Username can only contain letters and numbers")
        
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long")
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

class ClientRegistrationForm2(forms.ModelForm):
    """Second step: Company information"""
    class Meta:
        model = Client
        fields = ['company_name', 'address', 'city', 'state', 'zip_code', 'preferred_language']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
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
            'preferred_language': forms.Select(attrs={
                'class': 'form-control language-select',
                'aria-label': 'Select your preferred language',
                'data-placeholder': 'Select language'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les langues actives
        self.fields['preferred_language'].queryset = Language.objects.filter(is_active=True)
        # Ajouter un placeholder vide au début de la liste
        self.fields['preferred_language'].empty_label = "Select your preferred language"

class InterpreterRegistrationForm1(forms.ModelForm):
   """Formulaire étape 1: Informations de base"""
   username = forms.CharField(widget=forms.TextInput(attrs={
       'class': 'form-control',
       'placeholder': 'Enter your username'
   }))
   email = forms.EmailField(widget=forms.EmailInput(attrs={
       'class': 'form-control', 
       'placeholder': 'Enter your email'
   }))
   password1 = forms.CharField(
       label='Password',
       widget=forms.PasswordInput(attrs={
           'class': 'form-control',
           'placeholder': 'Enter your password'
       })
   )
   password2 = forms.CharField(
       label='Confirm Password',
       widget=forms.PasswordInput(attrs={
           'class': 'form-control',
           'placeholder': 'Confirm your password'
       })
   )

   class Meta:
       model = User
       fields = ['username', 'email', 'first_name', 'last_name', 'phone']
       widgets = {
           'first_name': forms.TextInput(attrs={
               'class': 'form-control',
               'placeholder': 'Enter your first name'
           }),
           'last_name': forms.TextInput(attrs={
               'class': 'form-control',
               'placeholder': 'Enter your last name'
           }),
           'phone': forms.TextInput(attrs={
               'class': 'form-control',
               'placeholder': 'Enter your phone number'
           })
       }

   def clean_password2(self):
       password1 = self.cleaned_data.get('password1')
       password2 = self.cleaned_data.get('password2')
       if password1 and password2:
           if password1 != password2:
               raise ValidationError("Passwords don't match")
           validate_password(password1)
       return password2

   def clean_email(self):
       email = self.cleaned_data.get('email')
       if User.objects.filter(email=email).exists():
           raise ValidationError("This email is already registered")
       return email

   def clean_username(self):
       username = self.cleaned_data.get('username')
       if User.objects.filter(username=username).exists():
           raise ValidationError("This username is already taken")
       return username

class InterpreterRegistrationForm2(forms.ModelForm):
    """Formulaire étape 2: Qualifications professionnelles"""
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '5'
        }),
        help_text="Select all languages you can interpret"
    )

    class Meta:
        model = Interpreter
        fields = ['languages']

class InterpreterRegistrationForm3(forms.ModelForm):
    """Formulaire étape 3: Adresse et documents"""
    class Meta:
        model = Interpreter
        fields = ['address', 'city', 'state', 'zip_code', 'w9_on_file']
        widgets = {
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your complete address'
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
            'w9_on_file': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['w9_on_file'].label = "I confirm I will provide a 1099 form"
        self.fields['w9_on_file'].required = True

    def clean_zip_code(self):
        zip_code = self.cleaned_data.get('zip_code')
        if zip_code and not zip_code.isdigit():
            raise ValidationError("ZIP code must contain only numbers")
        return zip_code

class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form with styling"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class CustomPasswordtradChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
