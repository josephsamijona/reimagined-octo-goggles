from django.contrib import admin
from django import forms
from django.utils.html import mark_safe
import pytz
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime

# =======================================================
# 1. UTILITAIRES POUR LE FUSEAU HORAIRE
# =======================================================
# On force ici l'heure du Massachusetts (America/New_York)
BOSTON_TZ = pytz.timezone('America/New_York')

def format_boston_datetime(dt):
    """
    Convertit une datetime (stockée en UTC) en heure locale de Boston
    et la formate au format US : MM/DD/YYYY HH:MM AM/PM TZ.
    Exemple : "03/25/2025 02:30 PM EDT"
    """
    if not dt:
        return ""
    local_dt = timezone.localtime(dt, BOSTON_TZ)
    return local_dt.strftime("%m/%d/%Y %I:%M %p %Z")

# =======================================================
# 2. WIDGET PERSONNALISÉ POUR LA SAISIE DE DATE/HEURE AVEC FLATPICKR
# =======================================================
class USDateTimePickerWidget(forms.MultiWidget):
    """
    Widget combinant deux champs de saisie (un pour la date et un pour l'heure)
    avec Flatpickr pour offrir un date picker et un time picker.
    """
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(attrs={'class': 'us-date-picker', 'placeholder': 'MM/DD/YYYY'}),
            forms.TextInput(attrs={'class': 'us-time-picker', 'placeholder': 'hh:mm AM/PM'}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """
        Décompose une datetime en date et heure
        Convertit de UTC vers Boston pour l'affichage dans le formulaire
        """
        if value:
            # Convertir de UTC vers Boston pour l'affichage
            boston_time = value.astimezone(BOSTON_TZ)
            return [
                boston_time.strftime('%m/%d/%Y'),
                boston_time.strftime('%I:%M %p')
            ]
        return [None, None]

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = [None, None]
        elif not isinstance(value, list):
            value = self.decompress(value)
        rendered = super().render(name, value, attrs, renderer)
        
        js = """
        <script type="text/javascript">
        (function($) {
            $(document).ready(function(){
                $('.us-date-picker').flatpickr({
                    dateFormat: "m/d/Y",
                    allowInput: true
                });
                $('.us-time-picker').flatpickr({
                    enableTime: true,
                    noCalendar: true,
                    dateFormat: "h:i K",
                    time_24hr: false,
                    allowInput: true
                });
            });
        })(django.jQuery);
        </script>
        """
        return mark_safe(rendered + js)

    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/flatpickr',)

# =======================================================
# 2.1. CHAMP PERSONNALISÉ : USDateTimeField
# =======================================================
class USDateTimeField(forms.MultiValueField):
    widget = USDateTimePickerWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DateField(input_formats=['%m/%d/%Y']),
            forms.TimeField(input_formats=['%I:%M %p']),
        )
        super().__init__(fields, require_all_fields=True, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
            
        if data_list[0] is None or data_list[1] is None:
            raise ValidationError("Enter a valid date and time.")

        try:
            # 1. Créer la datetime naïve
            naive_dt = datetime.combine(data_list[0], data_list[1])
            
            # 2. La localiser explicitement dans le fuseau Boston
            boston_dt = BOSTON_TZ.localize(naive_dt)
            
            # 3. La convertir en UTC pour le stockage
            utc_dt = boston_dt.astimezone(pytz.UTC)
            
            return utc_dt
            
        except (AttributeError, ValueError) as e:
            raise ValidationError("Enter a valid date and time.")

# =======================================================
# 4. ACTIONS PERSONNALISÉES
# =======================================================
def mark_as_active(modeladmin, request, queryset):
    queryset.update(active=True)
mark_as_active.short_description = "Mark as active"

def mark_as_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
mark_as_inactive.short_description = "Mark as inactive"

def reset_password(modeladmin, request, queryset):
    for user in queryset:
        # Implémenter ici la logique de réinitialisation de mot de passe
        pass
reset_password.short_description = "Reset password"
