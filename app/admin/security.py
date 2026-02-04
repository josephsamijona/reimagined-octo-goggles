from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from app import models

class ExpiresFilter(admin.SimpleListFilter):
    """Filtre personnalisé pour les clés expirées/non expirées"""
    title = _('statut d\'expiration')
    parameter_name = 'expiration'

    def lookups(self, request, model_admin):
        return (
            ('expired', _('Expirées')),
            ('valid', _('Valides')),
            ('never', _('Sans expiration')),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'expired':
            return queryset.filter(expires_at__lt=now)
        if self.value() == 'valid':
            return queryset.filter(expires_at__gt=now)
        if self.value() == 'never':
            return queryset.filter(expires_at__isnull=True)


@admin.register(models.APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name_with_badge', 'app_badge', 'user_display', 
                   'masked_key', 'status_badge', 'created_at_formatted', 
                   'expires_formatted', 'last_used_formatted')
    list_filter = (ExpiresFilter, 'is_active', 'created_at', 'app_name')
    search_fields = ('name', 'app_name', 'user__username', 'user__email')
    readonly_fields = ('id', 'key', 'created_at', 'last_used')
    actions = ['activate_keys', 'deactivate_keys', 'extend_expiration']
    save_as = True  # Permet de dupliquer une clé existante
    
    def get_fieldsets(self, request, obj=None):
        """Définit des fieldsets différents selon qu'on crée ou modifie une clé"""
        if obj:  # Modification d'un objet existant
            return (
                (_('Informations de base'), {
                    'fields': ('name', 'app_name', 'user')
                }),
                (_('Détails de la clé'), {
                    'fields': ('key', 'is_active'),
                }),
                (_('Dates'), {
                    'fields': ('created_at', 'expires_at', 'last_used'),
                    'description': '<div style="color: #666; padding: 5px 0;">Laissez le champ "Expire le" vide pour créer une clé qui n\'expire jamais.</div>'
                }),
            )
        else:  # Création d'un nouvel objet
            return (
                (_('Informations de base'), {
                    'fields': ('name', 'app_name', 'user')
                }),
                (_('Options'), {
                    'fields': ('is_active', 'expires_at'),
                    'description': '<div style="color: #666; padding: 5px 0;">Laissez le champ "Expire le" vide pour créer une clé qui n\'expire jamais.</div>'
                }),
            )
    
    def get_readonly_fields(self, request, obj=None):
        """Rend certains champs en lecture seule une fois l'objet créé"""
        if obj:  # Modification d'un objet existant
            return self.readonly_fields
        # Lors de la création, permettre l'édition de tous les champs sauf ceux en lecture seule
        return ('id', 'created_at', 'last_used')
    
    def save_model(self, request, obj, form, change):
        """Génère automatiquement une nouvelle clé API lors de la création"""
        if not change:  # Création d'un nouvel objet
            obj.key = models.APIKey.generate_key()
            
            # Afficher un message à l'utilisateur avec la clé générée
            self.message_user(
                request,
                format_html(
                    '<strong>Clé API générée :</strong> <code style="background-color: #f8f9fa; '
                    'padding: 4px 8px; border-radius: 4px; font-family: monospace;">{}</code><br>'
                    '<small style="color: #dc3545;">⚠️ Copiez cette clé maintenant car elle ne sera plus visible '
                    'entièrement par la suite.</small>',
                    obj.key
                ),
                level='SUCCESS'
            )
        super().save_model(request, obj, form, change)
    
    def masked_key(self, obj):
        """Affiche seulement les premiers caractères de la clé pour des raisons de sécurité"""
        return format_html(
            '<span style="font-family: monospace; background: #f8f9fa; padding: 3px 8px; '
            'border-radius: 3px; border: 1px solid #dee2e6;">{}</span>',
            f"{obj.key[:8]}...{obj.key[-4:]}"
        )
    masked_key.short_description = _('Clé API')
    
    def name_with_badge(self, obj):
        """Affiche le nom avec un badge stylisé"""
        return format_html(
            '<span style="font-weight: 500;">{}</span> {}',
            obj.name,
            self._get_app_count_badge(obj.user)
        )
    name_with_badge.short_description = _('Nom')
    name_with_badge.admin_order_field = 'name'
    
    def _get_app_count_badge(self, user):
        """Génère un badge indiquant le nombre de clés pour cet utilisateur"""
        count = models.APIKey.objects.filter(user=user, is_active=True).count()
        if count <= 1:
            return ''
        return format_html(
            '<span style="background-color: #e9ecef; font-size: 0.8em; padding: 1px 5px; '
            'border-radius: 10px; color: #495057; margin-left: 5px;">{}</span>',
            count
        )
    
    def app_badge(self, obj):
        """Affiche le nom de l'application comme un badge coloré"""
        colors = {
            'mobile': '#28a745',
            'web': '#007bff',
            'desktop': '#6610f2',
            'api': '#fd7e14',
            'serveur': '#20c997',
            'server': '#20c997',
            'test': '#dc3545',
            'dev': '#6c757d',
            'prod': '#17a2b8'
        }
        
        # Déterminer la couleur basée sur des mots-clés dans app_name
        color = '#6c757d'  # Couleur par défaut
        for keyword, keyword_color in colors.items():
            if keyword.lower() in obj.app_name.lower():
                color = keyword_color
                break
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 0.9em;">{}</span>',
            color, obj.app_name
        )
    app_badge.short_description = _('Application')
    app_badge.admin_order_field = 'app_name'
    
    def user_display(self, obj):
        """Affiche l'utilisateur sans lien (pour éviter les erreurs d'URL)"""
        if obj.user:
            return obj.user.username
        return '-'
    user_display.short_description = _('Utilisateur')
    user_display.admin_order_field = 'user__username'
    
    def status_badge(self, obj):
        """Affiche le statut comme un badge coloré"""
        if not obj.is_active:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 4px; font-size: 0.9em;">Désactivée</span>'
            )
        
        if obj.expires_at and obj.expires_at < timezone.now():
            return format_html(
                '<span style="background-color: #ffc107; color: #212529; padding: 3px 8px; '
                'border-radius: 4px; font-size: 0.9em;">Expirée</span>'
            )
        
        if not obj.expires_at:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 4px; font-size: 0.9em;">Permanente</span>'
            )
        
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 0.9em;">Active</span>'
        )
    status_badge.short_description = _('Statut')
    
    def created_at_formatted(self, obj):
        """Affiche la date de création formatée"""
        return format_html(
            '<span style="color: #6c757d;">{}</span>',
            obj.created_at.strftime('%d/%m/%Y')
        )
    created_at_formatted.short_description = _('Créée le')
    created_at_formatted.admin_order_field = 'created_at'
    
    def expires_formatted(self, obj):
        """Affiche la date d'expiration avec indication des jours restants"""
        if not obj.expires_at:
            return format_html(
                '<span style="color: #28a745; font-style: italic;">Jamais</span>'
            )
        
        # Calcul des jours restants
        days_left = (obj.expires_at - timezone.now()).days
        
        if days_left < 0:
            return format_html(
                '<span style="color: #dc3545;">Expirée</span>'
            )
        elif days_left < 7:
            return format_html(
                '<span style="color: #ffc107;">{} <small>({}j)</small></span>',
                obj.expires_at.strftime('%d/%m/%Y'), days_left
            )
        else:
            return format_html(
                '{} <small style="color: #6c757d;">({}j)</small>',
                obj.expires_at.strftime('%d/%m/%Y'), days_left
            )
    expires_formatted.short_description = _('Expire le')
    expires_formatted.admin_order_field = 'expires_at'
    
    def last_used_formatted(self, obj):
        """Affiche la dernière utilisation formatée"""
        if not obj.last_used:
            return format_html(
                '<span style="color: #6c757d; font-style: italic;">Jamais</span>'
            )
        
        # Calcul du temps écoulé depuis la dernière utilisation
        days_ago = (timezone.now() - obj.last_used).days
        
        if days_ago == 0:
            return format_html(
                '<span style="color: #28a745;">Aujourd\'hui</span>'
            )
        elif days_ago < 7:
            return format_html(
                '<span style="color: #17a2b8;">Il y a {} jours</span>',
                days_ago
            )
        else:
            return format_html(
                '{} <small style="color: #6c757d;">({}j)</small>',
                obj.last_used.strftime('%d/%m/%Y'), days_ago
            )
    last_used_formatted.short_description = _('Dernière utilisation')
    last_used_formatted.admin_order_field = 'last_used'
    
    def activate_keys(self, request, queryset):
        """Action pour activer plusieurs clés"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} clés API ont été activées.")
    activate_keys.short_description = _("Activer les clés sélectionnées")
    
    def deactivate_keys(self, request, queryset):
        """Action pour désactiver plusieurs clés"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} clés API ont été désactivées.")
    deactivate_keys.short_description = _("Désactiver les clés sélectionnées")
    
    def extend_expiration(self, request, queryset):
        """Action pour prolonger l'expiration de 30 jours"""
        count = 0
        for api_key in queryset:
            if api_key.expires_at:
                api_key.expires_at = api_key.expires_at + timezone.timedelta(days=30)
            else:
                api_key.expires_at = timezone.now() + timezone.timedelta(days=30)
            api_key.save()
            count += 1
        self.message_user(request, f"L'expiration de {count} clés API a été prolongée de 30 jours.")
    extend_expiration.short_description = _("Prolonger l'expiration (+30 jours)")

@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__email', 'action', 'changes')
    readonly_fields = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'changes', 'ip_address')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(models.PGPKey)
class PGPKeyAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'key_id_display', 
        'algorithm_display', 
        'user_display', 
        'expiry_status', 
        'is_active'
    )
    
    list_filter = (
        'is_active', 
        'algorithm',
    )
    
    search_fields = (
        'name', 
        'key_id', 
        'fingerprint', 
        'user_name', 
        'user_email'
    )
    
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at', 
        'short_key_id_display', 
        'days_until_expiry_display', 
        'expiry_status'
    )
    
    fieldsets = (
        ('🔑 Key Information', {
            'fields': (
                'name', 
                'key_id', 
                'fingerprint', 
                'algorithm', 
                'key_size', 
                'short_key_id_display'
            ),
        }),
        ('👤 User Information', {
            'fields': (
                'user_name', 
                'user_email'
            ),
        }),
        ('⏱️ Validity', {
            'fields': (
                'is_active',
                'created_at', 
                'updated_at', 
                'expires_at', 
                'days_until_expiry_display', 
                'expiry_status'
            ),
        }),
        ('🔐 Key Material', {
            'fields': (
                'public_key', 
                'private_key_reference'
            ),
            'classes': ('collapse',),
        }),
    )
    
    def key_id_display(self, obj):
        """Display key ID with emoji"""
        return f"🔑 {obj.key_id}"
    key_id_display.short_description = 'Key ID'
    
    def algorithm_display(self, obj):
        """Display algorithm with key size"""
        if obj.algorithm and obj.key_size:
            return f"🔐 {obj.algorithm} ({obj.key_size} bits)"
        elif obj.algorithm:
            return f"🔐 {obj.algorithm}"
        return "—"
    algorithm_display.short_description = 'Algorithm'
    
    def user_display(self, obj):
        """Display user info"""
        if obj.user_name and obj.user_email:
            return f"👤 {obj.user_name} ({obj.user_email})"
        elif obj.user_name:
            return f"👤 {obj.user_name}"
        elif obj.user_email:
            return f"📧 {obj.user_email}"
        return "—"
    user_display.short_description = 'User'
    
    def short_key_id_display(self, obj):
        """Display short key ID"""
        if obj.short_key_id:
            return f"🔑 {obj.short_key_id}"
        return "—"
    short_key_id_display.short_description = 'Short Key ID'
    
    def days_until_expiry_display(self, obj):
        """Display days until expiry"""
        days = obj.days_until_expiry
        if days is None:
            return "♾️ Never expires"
        elif days == 0:
            return "⚠️ Expired today"
        elif days < 0:
            return f"⚠️ Expired {abs(days)} days ago"
        elif days <= 30:
            return f"⚠️ Expires in {days} days"
        else:
            return f"✅ {days} days remaining"
    days_until_expiry_display.short_description = 'Days Until Expiry'
    
    def expiry_status(self, obj):
        """Display expiry status with color indicator"""
        if not obj.expires_at:
            return mark_safe('<span style="color: green;">♾️ Never expires</span>')
        
        days = obj.days_until_expiry
        if days is None:
            return mark_safe('<span style="color: green;">♾️ Never expires</span>')
        elif days <= 0:
            return mark_safe('<span style="color: red;">⚠️ Expired</span>')
        elif days <= 30:
            return mark_safe(f'<span style="color: orange;">⚠️ {days} days left</span>')
        else:
            return mark_safe(f'<span style="color: green;">✅ Valid</span>')
    expiry_status.short_description = 'Expiry Status'
    
    actions = ['activate_keys', 'deactivate_keys', 'extend_expiry']
    
    def activate_keys(self, request, queryset):
        """Activate selected keys"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} key(s) have been activated.")
    activate_keys.short_description = "Activate selected keys"
    
    def deactivate_keys(self, request, queryset):
        """Deactivate selected keys"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} key(s) have been deactivated.")
    deactivate_keys.short_description = "Deactivate selected keys"
    
    def extend_expiry(self, request, queryset):
        """Extend expiry by 1 year for selected keys"""
        count = 0
        for key in queryset:
            if key.expires_at:
                # Extend by 1 year from current expiry
                key.expires_at = key.expires_at + timezone.timedelta(days=365)
                key.save(update_fields=['expires_at'])
                count += 1
            elif not key.expires_at:
                # Set expiry to 1 year from now if not set
                key.expires_at = timezone.now() + timezone.timedelta(days=365)
                key.save(update_fields=['expires_at'])
                count += 1
        
        self.message_user(request, f"Extended expiry for {count} key(s) by 1 year.")
    extend_expiry.short_description = "Extend expiry by 1 year"
