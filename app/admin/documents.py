from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib import messages
from app import models

@admin.register(models.InterpreterContractSignature)
class InterpreterContractSignatureAdmin(admin.ModelAdmin):
    list_display = ('emoji_status', 'interpreter_name', 'interpreter_email', 
                    'token_display', 'signature_type_display', 'signed_date', 
                    'status', 'is_fully_signed', 'is_active')
    
    list_filter = ('status', 'is_fully_signed', 'is_active', 'signature_type', 
                  'account_type', 'signed_at')
    search_fields = ('interpreter_name', 'interpreter_email', 'interpreter_phone', 
                    'signature_hash', 'token', 'otp_code')
    readonly_fields = ('signature_hash', 'signed_at', 'id', 'created_at',
                      'account_number_display', 'routing_number_display', 'swift_code_display',
                      'encrypted_account_number', 'encrypted_routing_number','account_holder_name',
                      'signature_converted_url', 'encrypted_swift_code')
    
    date_hierarchy = 'signed_at'
    
    fieldsets = (
        ('🧑‍💼 Interpreter Information', {
            'fields': (
                'user', 'interpreter', 'interpreter_name', 'interpreter_email', 
                'interpreter_phone', 'interpreter_address'
            ),
        }),
        ('🔐 Contract Authentication', {
            'fields': (
                'token', 'otp_code', 'created_at', 'expires_at', 'status',
            ),
        }),
        ('📝 Contract Details', {
            'fields': (
                'contract_document', 'contract_version', 'signature_type',
                'signed_at', 'ip_address', 'signature_hash',
            ),
        }),
        ('✍️ Signature Data', {
            'fields': (
                'signature_image', 'signature_converted_url', 'signature_typography_text', 
                'signature_typography_font', 'signature_manual_data',
            ),
            'classes': ('collapse',),
        }),
        ('💰 Banking Information', {
            'fields': (
                'bank_name', 'account_type','account_holder_name',
                'account_number_display', 'routing_number_display', 'swift_code_display',
            ),
            'description': 'Banking information is encrypted and can only be viewed in masked form. To modify banking information, please use the application interface.',
            'classes': ('collapse',),
        }),
        ('🏢 Company Information', {
            'fields': (
                'company_representative_name', 'company_representative_signature', 'company_signed_at',
            ),
        }),
        ('📊 Status', {
            'fields': (
                'is_fully_signed', 'is_active',
            ),
        }),
    )
    
    def emoji_status(self, obj):
        """Display status with emoji"""
        status_map = {
            'PENDING': "📋 ⏳",
            'SIGNED': "📋 ✅",
            'EXPIRED': "📋 ⌛",
            'LINK_ACCESSED': "📋 👁️",
            'REJECTED': "📋 ❌",
            'COMPLETED': "📋 ✅✅"
        }
        return status_map.get(obj.status, "📋 ❓")
    emoji_status.short_description = "Status"
    
    def token_display(self, obj):
        """Display shortened token"""
        if obj.token:
            short_token = obj.token[:8] + "..." + obj.token[-8:]
            return f"🔑 {short_token}"
        return "—"
    token_display.short_description = 'Token'
    
    def signature_type_display(self, obj):
        """Display signature type with emoji"""
        types = {
            'upload': '🖼️ Image',
            'type': '🔤 Typography',
            'draw': '✒️ Manual'
        }
        return types.get(obj.signature_type, obj.signature_type or "—")
    signature_type_display.short_description = 'Type'
    
    def signed_date(self, obj):
        """Format signed date with emoji"""
        if obj.signed_at:
            return f"🗓️ {obj.signed_at.strftime('%Y-%m-%d')}"
        return "—"
    signed_date.short_description = 'Signed On'
    
    def account_number_display(self, obj):
        """Display masked account number"""
        account_number = obj.get_account_number()
        if not account_number:
            return '—'
        # Show only last 4 digits
        masked = '*' * (len(account_number) - 4) + account_number[-4:]
        return f"🔒 {masked}"
    account_number_display.short_description = 'Account Number (Masked)'
    
    def routing_number_display(self, obj):
        """Display masked routing number"""
        routing_number = obj.get_routing_number()
        if not routing_number:
            return '—'
        # Show only first and last 2 digits
        masked = routing_number[:2] + '*' * (len(routing_number) - 4) + routing_number[-2:]
        return f"🔒 {masked}"
    routing_number_display.short_description = 'Routing Number (Masked)'
    
    def swift_code_display(self, obj):
        """Display masked SWIFT code"""
        swift_code = obj.get_swift_code()
        if not swift_code:
            return '—'
        # Show only first 4 characters
        masked = swift_code[:4] + '*' * (len(swift_code) - 4) 
        return f"🔒 {masked}"
    swift_code_display.short_description = 'SWIFT Code (Masked)'
    
    # Ajout des mappings User <-> Interpreter pour JavaScript
    def get_user_interpreter_mappings(self):
        """Génère un dictionnaire de correspondance entre users et interprètes"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Récupérer les utilisateurs qui ont des profils d'interprète
        users_with_interpreters = User.objects.filter(interpreter_profile__isnull=False)
        
        # Créer dictionnaires pour les mappings dans les deux sens
        user_to_interpreter = {}
        interpreter_to_user = {}
        
        for user in users_with_interpreters:
            try:
                interpreter_id = user.interpreter_profile.id
                user_to_interpreter[user.id] = interpreter_id
                interpreter_to_user[interpreter_id] = user.id
            except:
                continue
        
        return user_to_interpreter, interpreter_to_user
    
    class Media:
        js = ('admin/js/interpreter_contract_admin.js',)
    
    def changelist_view(self, request, extra_context=None):
        """Ajoute le script JS pour la liaison user-interprète"""
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Ajoute les mappings user-interprète au contexte pour la page de détail"""
        extra_context = extra_context or {}
        user_to_interpreter, interpreter_to_user = self.get_user_interpreter_mappings()
        
        # Ajoute ces data dans une balise script pour les récupérer en JS
        script = f"""
        <script>
            // Mappings User -> Interpreter
            var userToInterpreter = {user_to_interpreter};
            // Mappings Interpreter -> User
            var interpreterToUser = {interpreter_to_user};
            
            document.addEventListener('DOMContentLoaded', function() {{
                // Sélection des champs d'entrée
                var userSelect = document.getElementById('id_user');
                var interpreterSelect = document.getElementById('id_interpreter');
                
                if (userSelect && interpreterSelect) {{
                    // Ajouter les écouteurs d'événements
                    userSelect.addEventListener('change', function() {{
                        var userId = this.value;
                        if (userId && userToInterpreter[userId]) {{
                            // Mise à jour du champ interpreter quand user change
                            interpreterSelect.value = userToInterpreter[userId];
                        }}
                    }});
                    
                    interpreterSelect.addEventListener('change', function() {{
                        var interpreterId = this.value;
                        if (interpreterId && interpreterToUser[interpreterId]) {{
                            // Mise à jour du champ user quand interpreter change
                            userSelect.value = interpreterToUser[interpreterId];
                        }}
                    }});
                }}
            }});
        </script>
        """
        
        # Ajoute le script au contexte
        extra_context['after_related_objects'] = mark_safe(script)
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        """Ajoute les mappings user-interprète au contexte pour la page d'ajout"""
        extra_context = extra_context or {}
        user_to_interpreter, interpreter_to_user = self.get_user_interpreter_mappings()
        
        # Ajoute ces data dans une balise script pour les récupérer en JS
        script = f"""
        <script>
            // Mappings User -> Interpreter
            var userToInterpreter = {user_to_interpreter};
            // Mappings Interpreter -> User
            var interpreterToUser = {interpreter_to_user};
            
            document.addEventListener('DOMContentLoaded', function() {{
                // Sélection des champs d'entrée
                var userSelect = document.getElementById('id_user');
                var interpreterSelect = document.getElementById('id_interpreter');
                
                if (userSelect && interpreterSelect) {{
                    // Ajouter les écouteurs d'événements
                    userSelect.addEventListener('change', function() {{
                        var userId = this.value;
                        if (userId && userToInterpreter[userId]) {{
                            // Mise à jour du champ interpreter quand user change
                            interpreterSelect.value = userToInterpreter[userId];
                        }}
                    }});
                    
                    interpreterSelect.addEventListener('change', function() {{
                        var interpreterId = this.value;
                        if (interpreterId && interpreterToUser[interpreterId]) {{
                            // Mise à jour du champ user quand interpreter change
                            userSelect.value = interpreterToUser[interpreterId];
                        }}
                    }});
                }}
            }});
        </script>
        """
        
        # Ajoute le script au contexte
        extra_context['after_related_objects'] = mark_safe(script)
        
        return super().add_view(request, form_url, extra_context=extra_context)

    actions = ['mark_as_expired', 'mark_as_completed', 'resend_contract_email', 'debug_contract_status']
    
    def mark_as_expired(self, request, queryset):
        """Mark selected contracts as expired"""
        updated = queryset.update(status='EXPIRED')
        self.message_user(request, f"{updated} contract(s) marked as expired.")
    mark_as_expired.short_description = "Mark selected contracts as expired"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected contracts as completed"""
        for contract in queryset:
            contract.status = 'COMPLETED'
            contract.is_fully_signed = True
            contract.is_active = True
            
            # Mettre à jour la date de signature de l'entreprise si elle n'existe pas
            if not contract.company_signed_at:
                contract.company_signed_at = timezone.now()
            
            # Mettre à jour l'utilisateur lié pour marquer son inscription comme complète
            if contract.user:
                contract.user.registration_complete = True
                contract.user.save(update_fields=['registration_complete'])
            
            # Mettre à jour l'interprète lié
            if contract.interpreter:
                contract.interpreter.active = True
                contract.interpreter.save()
            
            contract.save()
        
        self.message_user(request, f"{queryset.count()} contract(s) marked as completed.")
    mark_as_completed.short_description = "Mark selected contracts as completed"
    
    def debug_contract_status(self, request, queryset):
        """Afficher des informations de débogage sur les contrats sélectionnés"""
        for contract in queryset:
            status_info = [
                f"ID: {contract.id}",
                f"Status: {contract.status}",
                f"Signature Type: {contract.signature_type}",
                f"Signature Typography Text: {'Présent' if contract.signature_typography_text else 'Absent'}",
                f"Signature Typography Font: {'Présent' if hasattr(contract, 'signature_typography_font') and contract.signature_typography_font else 'Absent'}",
                f"Signature Manual Data: {'Présent' if contract.signature_manual_data else 'Absent'}",
                f"Signature Image: {'Présent' if contract.signature_image else 'Absent'}",
                f"User Registration Complete: {'Oui' if contract.user and contract.user.registration_complete else 'Non'}",
                f"Interpreter Active: {'Oui' if contract.interpreter and contract.interpreter.active else 'Non'}"
            ]
            
            self.message_user(request, f"Contract Debug Info:\n" + "\n".join(status_info))
    debug_contract_status.short_description = "Debug selected contracts"
    
    def resend_contract_email(self, request, queryset):
        """Renvoie l'email de contrat avec un nouveau token et OTP aux interprètes sélectionnés"""
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.urls import reverse
        import uuid
        import random
        import socket
        import time
        
        count = 0
        updated = 0
        errors = 0
        
        for contract in queryset:
            if not contract.interpreter_email:
                continue
                
            try:
                # Toujours générer un nouveau token et OTP pour garantir que le lien fonctionnera
                contract.token = str(uuid.uuid4())
                contract.otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                contract.expires_at = timezone.now() + timezone.timedelta(hours=24)
                
                # Réinitialiser le statut si nécessaire pour permettre une nouvelle signature
                if contract.status in ['EXPIRED', 'LINK_ACCESSED']:
                    contract.status = 'PENDING'
                    
                contract.save()
                updated += 1
                
                # Création d'un identifiant unique pour ce message
                message_id = f"<contract-renewal-{contract.id}-{uuid.uuid4()}@{socket.gethostname()}>"
                
                # Construction de l'URL absolue pour le lien de vérification
                path = reverse('dbdint:contract_verification', kwargs={'token': contract.token})
                verification_url = request.build_absolute_uri(path)
                
                # Préparation des données pour le template
                context = {
                    'interpreter_name': contract.interpreter_name,
                    'token': contract.token,
                    'otp_code': contract.otp_code,
                    'verification_url': verification_url,
                    'email': contract.interpreter_email
                }
                
                # Rendu du template HTML
                html_message = render_to_string('notifmail/esign_notif.html', context)
                plain_message = strip_tags(html_message)
                
                # Ligne d'objet optimisée pour la délivrabilité
                first_name = contract.interpreter_name.split()[0] if contract.interpreter_name else "Interprète"
                subject = f"{first_name}, votre contrat d'interprète JH Bridge est prêt à signer"
                
                # Format professionnel pour l'adresse expéditeur
                from_email = f"JH Bridge Contrats <contracts@jhbridgetranslation.com>"
                
                # Création de l'email
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=from_email,
                    to=[contract.interpreter_email],
                    reply_to=['support@jhbridgetranslation.com']
                )
                
                # Ajout de la version HTML comme alternative
                email.attach_alternative(html_message, "text/html")
                
                # En-têtes optimisés pour la délivrabilité
                email.extra_headers = {
                    'Message-ID': message_id,
                    'X-Entity-Ref-ID': str(contract.token),
                    'X-Mailer': 'JHBridge-ContractMailer/1.0',
                    'X-Contact-ID': str(contract.id),
                    'List-Unsubscribe': f'<mailto:unsubscribe@jhbridgetranslation.com?subject=Unsubscribe-{contract.interpreter_email}>',
                    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                    'Precedence': 'bulk',
                    'Auto-Submitted': 'auto-generated',
                    'Feedback-ID': f'contract-{contract.id}:{contract.interpreter.id if contract.interpreter else "0"}:jhbridge:{int(time.time())}',
                    'X-Priority': '1',
                    'X-MSMail-Priority': 'High',
                    'Importance': 'High'
                }
                
                # Envoi de l'email
                email.send(fail_silently=False)
                
                self.message_user(
                    request, 
                    f"✓ Email envoyé à {contract.interpreter_email} avec lien: {verification_url}",
                    level=messages.SUCCESS
                )
                count += 1
                
            except Exception as e:
                errors += 1
                self.message_user(
                    request, 
                    f"❌ Erreur pour {contract.interpreter_email}: {str(e)}", 
                    level=messages.ERROR
                )
        
        # Message récapitulatif
        if count > 0:
            self.message_user(
                request, 
                f"✅ {count} email(s) envoyé(s) avec succès. {updated} contrat(s) mis à jour.",
                level=messages.SUCCESS
            )
        
        if errors > 0:
            self.message_user(
                request, 
                f"⚠️ {errors} erreur(s) rencontrée(s). Consultez les messages ci-dessus.",
                level=messages.WARNING
            )
            
    resend_contract_email.short_description = "📧 Renvoyer un email avec nouveau lien de contrat"

@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'document_number', 
        'document_type_display', 
        'status_display', 
        'date_display',
        'has_signature'
    )
    
    list_filter = (
        'document_type', 
        'status', 
        'created_at'
    )
    
    search_fields = (
        'title', 
        'document_number', 
        'agreement_id',
        'metadata'
    )
    
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at', 
        'signed_at', 
        'file_hash', 
        'document_number',
        'metadata_display'
    )
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('📝 Document Information', {
            'fields': (
                'title', 
                'document_number', 
                'document_type', 
                'status', 
                'agreement_id'
            ),
        }),
        ('🔗 Relations', {
            'fields': (
                'user', 
                'interpreter_contract'
            ),
        }),
        ('📂 File', {
            'fields': (
                'file', 
                'file_hash'
            ),
        }),
        ('✍️ PGP Signature', {
            'fields': (
                'pgp_signature', 
                'signing_key', 
                'signed_at'
            ),
            'classes': ('collapse',),
        }),
        ('⏱️ Timestamps', {
            'fields': (
                'created_at', 
                'updated_at'
            ),
        }),
        ('📊 Metadata', {
            'fields': (
                'metadata_display',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def document_type_display(self, obj):
        """Display document type with emoji"""
        type_map = {
            'CONTRACT': '📑 Contract',
            'INVOICE': '💰 Invoice',
            'QUOTE': '💵 Quote',
            'CERTIFICATE': '🏆 Certificate',
            'LETTER': '✉️ Letter',
            'REPORT': '📊 Report',
            'OTHER': '📄 Other'
        }
        return type_map.get(obj.document_type, f"📄 {obj.document_type}")
    document_type_display.short_description = 'Type'
    
    def status_display(self, obj):
        """Display status with color"""
        status_map = {
            'DRAFT': '<span style="color: gray;">📝 Draft</span>',
            'SIGNED': '<span style="color: green;">✅ Signed</span>',
            'SENT': '<span style="color: blue;">📤 Sent</span>',
            'CANCELLED': '<span style="color: red;">❌ Cancelled</span>',
            'ARCHIVED': '<span style="color: brown;">🗄️ Archived</span>'
        }
        return mark_safe(status_map.get(obj.status, obj.status))
    status_display.short_description = 'Status'
    
    def date_display(self, obj):
        """Display created and signed date"""
        if obj.signed_at:
            return f"📅 {obj.created_at.strftime('%Y-%m-%d')} ✍️ {obj.signed_at.strftime('%Y-%m-%d')}"
        return f"📅 {obj.created_at.strftime('%Y-%m-%d')}"
    date_display.short_description = 'Dates'
    
    def has_signature(self, obj):
        """Display if document has signature"""
        return bool(obj.pgp_signature and obj.signing_key)
    has_signature.short_description = 'Signed'
    has_signature.boolean = True
    
    def metadata_display(self, obj):
        """Format metadata as HTML for better readability"""
        if not obj.metadata:
            return "No metadata available"
            
        html = ["<table style='width:100%; border-collapse: collapse;'>"]
        html.append("<tr><th style='text-align:left; padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Key</th><th style='text-align:left; padding:8px; border:1px solid #ddd; background-color:#f2f2f2;'>Value</th></tr>")
        
        for key, value in obj.metadata.items():
            html.append(f"<tr><td style='padding:8px; border:1px solid #ddd;'>{key}</td><td style='padding:8px; border:1px solid #ddd;'>{value}</td></tr>")
            
        html.append("</table>")
        return mark_safe("".join(html))
    metadata_display.short_description = 'Metadata'
    
    actions = ['mark_as_signed', 'mark_as_sent', 'mark_as_archived', 'mark_as_cancelled']
    
    def mark_as_signed(self, request, queryset):
        """Mark selected documents as signed"""
        updated = 0
        for document in queryset:
            if document.status != 'SIGNED':
                document.status = 'SIGNED'
                document.signed_at = timezone.now()
                document.save(update_fields=['status', 'signed_at'])
                updated += 1
        
        self.message_user(request, f"{updated} document(s) marked as signed.")
    mark_as_signed.short_description = "Mark selected documents as signed"
    
    def mark_as_sent(self, request, queryset):
        """Mark selected documents as sent"""
        updated = queryset.update(status='SENT')
        self.message_user(request, f"{updated} document(s) marked as sent.")
    mark_as_sent.short_description = "Mark selected documents as sent"
    
    def mark_as_archived(self, request, queryset):
        """Mark selected documents as archived"""
        updated = queryset.update(status='ARCHIVED')
        self.message_user(request, f"{updated} document(s) marked as archived.")
    mark_as_archived.short_description = "Mark selected documents as archived"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected documents as cancelled"""
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f"{updated} document(s) marked as cancelled.")
    mark_as_cancelled.short_description = "Mark selected documents as cancelled"
