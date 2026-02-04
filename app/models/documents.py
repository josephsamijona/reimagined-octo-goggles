from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os
import time
import base64
import binascii
import hashlib
import random
import logging
from cryptography.fernet import Fernet, InvalidToken
from .users import User, Interpreter
import sys

# Import relatif pour éviter les imports circulaires
# On importe la fonction seulement quand nécessaire ou on la définit ici si c'est une utilitaire pure
# Mais comme elle est importée depuis .utils.signature_app dans le fichier original, on suppose qu'elle existe

logger = logging.getLogger(__name__)

def signature_upload_path(instance, filename):
    """Chemin personnalisé pour les signatures"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('signatures', filename)

def pdf_upload_path(instance, filename):
    """Chemin personnalisé pour les PDFs"""
    return os.path.join('documents', f"{uuid.uuid4()}.pdf")

def get_expiration_time():
    return timezone.now() + timezone.timedelta(hours=24)

# Utilitaires de conversion (simplifié)
def convert_signature_data_to_png(data):
    # Cette fonction doit être importée ou implémentée
    # Pour éviter les dépendances circulaires, on peut l'importer à l'intérieur de la méthode qui l'utilise
    from app.utils.signature_app import convert_signature_data_to_png as converter
    return converter(data)

class InterpreterContractSignature(models.Model):
    """Model for interpreter contract signatures with secure encryption for confidential data"""
    
    # Contract status choices
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SIGNED', 'Signed'),
        ('EXPIRED', 'Expired'),
        ('LINK_ACCESSED', 'Link_accessed'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed')  # Signé par l'interprète et par la compagnie
    ]
    
    # Signature types
    SIGNATURE_TYPE_CHOICES = [
        ('upload', 'Uploaded image'),
        ('type', 'Typography signature'),
        ('draw', 'Manual signature'),
    ]
    
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Contract authentication information (pour l'email et la validation)
    token = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=get_expiration_time)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # User relationship (can be null)
    user = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL,
        related_name='interpreter_contracts',
        null=True,
        blank=True,
        help_text="Associated user account if available"
    )
    
    # Interpreter relationship (should not be null when using registration system)
    interpreter = models.ForeignKey(
        'Interpreter',
        on_delete=models.CASCADE,
        related_name='contracts',
        null=True,
        blank=True
    )
    
    # Interpreter information
    interpreter_name = models.CharField(max_length=255)
    interpreter_email = models.EmailField()
    interpreter_phone = models.CharField(max_length=20)
    interpreter_address = models.TextField()
    
    # Banking information (non-encrypted - for basic information)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    account_type = models.CharField(
        max_length=20, 
        choices=[('checking', 'Checking'), ('savings', 'Savings')],
        blank=True,
        null=True
    )
    
    # Banking information (encrypted)
    encrypted_account_number = models.BinaryField(blank=True, null=True)
    encrypted_routing_number = models.BinaryField(blank=True, null=True)
    encrypted_swift_code = models.BinaryField(blank=True, null=True)
    
    # Contract document
    contract_document = models.FileField(upload_to='interpreter_contracts/', blank=True, null=True)
    contract_version = models.CharField(max_length=20, default='1.0')
    
    # Signature
    signature_type = models.CharField(max_length=20, choices=SIGNATURE_TYPE_CHOICES, blank=True, null=True)
    signature_image = models.ImageField(
        upload_to='signatures/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'png', 'jpeg'])]
    )
    signature_converted_url = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="URL S3 de la signature manuelle convertie en PNG"
    )
    signature_typography_text = models.CharField(max_length=100, blank=True, null=True)
    signature_typography_font = models.CharField(max_length=50, blank=True, null=True)
    signature_manual_data = models.TextField(blank=True, null=True, help_text="Coordinates of manual signature")
    
    # Signature metadata
    signed_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    signature_hash = models.CharField(max_length=64, blank=True, null=True)  # Hash for verification
    
    # Company signature
    company_representative_name = models.CharField(max_length=255, default="Marc-Henry Valme")
    company_representative_signature = models.TextField(blank=True, null=True)
    company_signed_at = models.DateTimeField(blank=True, null=True)
    
    # Contract status
    is_fully_signed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    
    # Notifications & Reminders
    email_sent_at = models.DateTimeField(null=True, blank=True)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    modal_viewed_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'app_interpretercontractsignature'

    def __str__(self):
        return f"Interpreter contract for {self.interpreter_name} ({self.status})"
    
    def get_signature_url(self):
        """
        Retourne l'URL de la signature selon le type.
        Pour 'draw': retourne signature_converted_url
        Pour 'upload': retourne signature_image.url
        Pour 'type': retourne None (pas d'image)
        """
        if self.signature_type == 'draw' and self.signature_converted_url:
            return self.signature_converted_url
        elif self.signature_type == 'upload' and self.signature_image:
            return self.signature_image.url
        return None
      
    def get_signature_display_info(self):
        """
        Retourne les informations d'affichage de la signature selon le type.
        """
        info = {
            'type': self.signature_type,
            'image_url': None,
            'text': None,
            'font': None,
            'raw_data': None
        }
        
        if self.signature_type == 'type':
            info['text'] = self.signature_typography_text
            info['font'] = self.signature_typography_font
        elif self.signature_type == 'draw':
            info['image_url'] = self.signature_converted_url
            info['raw_data'] = self.signature_manual_data
        elif self.signature_type == 'upload':
            info['image_url'] = self.signature_image.url if self.signature_image else None
        
        return info  
    
    @staticmethod
    def get_encryption_key():
        """Get the encryption key from settings"""
        try:
            # Try to convert from hex format
            key_bytes = binascii.unhexlify(settings.ENCRYPTION_KEY)
            # Ensure it's properly base64 encoded for Fernet
            return base64.urlsafe_b64encode(key_bytes[:32])
        except (binascii.Error, TypeError, AttributeError):
            # If the key is already in correct format or settings doesn't exist
            if hasattr(settings, 'ENCRYPTION_KEY'):
                return settings.ENCRYPTION_KEY
            else:
                # Fallback for development only - NEVER use in production
                import warnings
                warnings.warn("Using default encryption key! This is insecure for production!")
                return Fernet.generate_key()
    
    @classmethod
    def encrypt_data(cls, data):
        """Encrypt sensitive data"""
        if not data:
            return None
        
        f = Fernet(cls.get_encryption_key())
        return f.encrypt(str(data).encode())
    
    @classmethod
    def decrypt_data(cls, encrypted_data):
        """Decrypt sensitive data"""
        if not encrypted_data:
            return None
        
        try:
            f = Fernet(cls.get_encryption_key())
            return f.decrypt(encrypted_data).decode()
        except (TypeError, ValueError, InvalidToken):
            return None
    
    def set_account_number(self, account_number):
        """Encrypt and set the account number"""
        self.encrypted_account_number = self.encrypt_data(account_number)
    
    def get_account_number(self):
        """Decrypt and return the account number"""
        return self.decrypt_data(self.encrypted_account_number)
    
    def set_routing_number(self, routing_number):
        """Encrypt and set the routing number"""
        self.encrypted_routing_number = self.encrypt_data(routing_number)
    
    def get_routing_number(self):
        """Decrypt and return the routing number"""
        return self.decrypt_data(self.encrypted_routing_number)
    
    def set_swift_code(self, swift_code):
        """Encrypt and set the SWIFT code"""
        self.encrypted_swift_code = self.encrypt_data(swift_code)
    
    def get_swift_code(self):
        """Decrypt and return the SWIFT code"""
        return self.decrypt_data(self.encrypted_swift_code)
    
    def is_expired(self):
        """Check if the contract signing period has expired"""
        return timezone.now() > self.expires_at
    
    def generate_signature_hash(self):
        """Generate a unique hash for the signature"""
        data = f"{self.interpreter_name}{self.interpreter_email}{timezone.now().isoformat()}{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def upload_signature_to_s3(self, image_data, filename_prefix='signature'):
        """
        Upload une image de signature vers Backblaze B2 en utilisant le système de stockage Django
        """
        try:
            # Nom du fichier
            filename = f"signatures/{filename_prefix}_{self.id}_{int(time.time())}.png"
            
            # Créer un ContentFile à partir des données de l'image
            content_file = ContentFile(image_data.getvalue(), name=filename)
            
            # Sauvegarder le fichier en utilisant le système de stockage par défaut
            saved_path = default_storage.save(filename, content_file)
            
            # Obtenir l'URL publique du fichier
            url = default_storage.url(saved_path)
            
            logger.info(f"Signature uploadée avec succès: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Erreur lors de l'upload vers B2: {e}")
            return None
    
    def mark_as_signed(self, signature_type, ip_address, **kwargs):
        """Mark the contract as signed by the interpreter"""
        self.status = 'SIGNED'
        self.signature_type = signature_type
        self.ip_address = ip_address
        self.signed_at = timezone.now()
        self.signature_hash = self.generate_signature_hash()
        
        logger.info(f"Marquage du contrat {self.id} comme signé avec méthode: {signature_type}")
        
        # Set signature data based on type
        if signature_type == 'type':
            if 'text' in kwargs and kwargs['text']:
                self.signature_typography_text = kwargs['text']
            
            if 'font' in kwargs and kwargs['font']:
                self.signature_typography_font = kwargs['font']
        
        elif signature_type == 'draw':
            if 'data' in kwargs and kwargs['data']:
                # Sauvegarder les données brutes
                self.signature_manual_data = kwargs['data']
                
                # Convertir les données en image PNG
                try:
                    # Import local pour éviter dépendance circulaire
                    from app.utils.signature_app import convert_signature_data_to_png
                    img_data = convert_signature_data_to_png(kwargs['data'])
                    
                    if img_data:
                        # Upload vers B2 en utilisant la méthode de l'instance
                        url = self.upload_signature_to_s3(img_data)
                        
                        if url:
                            # Sauvegarder l'URL dans le nouveau champ
                            self.signature_converted_url = url
                except Exception as e:
                    logger.error(f"Erreur lors de la conversion/upload de la signature: {e}")
        
        elif signature_type == 'upload' and self.signature_image:
            logger.info(f"Image de signature déjà définie: {self.signature_image.name}")
        
        # Sauvegarder toutes les modifications
        self.save(update_fields=[
            'status', 'signature_type', 'ip_address', 'signed_at', 
            'signature_hash', 'signature_typography_text', 
            'signature_typography_font', 'signature_manual_data',
            'signature_converted_url', 'signature_image'
        ])
        
        return self
    
    def mark_as_company_signed(self, signature_data=None):
        """Mark the contract as signed by the company representative"""
        self.company_representative_signature = signature_data or "Electronically signed"
        self.company_signed_at = timezone.now()  # Toujours enregistrer la date actuelle
        
        # If both parties have signed, mark as fully signed
        if self.signed_at:
            self.is_fully_signed = True
            self.is_active = True
            self.status = 'COMPLETED'
        
        self.save()
    
    def save(self, *args, **kwargs):
        """Override save method to ensure hash creation and auto-populate from user when possible"""
        # Auto-populate from user if available and fields are not set
        if self.user and not self.pk:  # Only for new records
            if not self.interpreter_name and self.user.get_full_name():
                self.interpreter_name = self.user.get_full_name()
            if not self.interpreter_email:
                self.interpreter_email = self.user.email
            if not self.interpreter_phone and hasattr(self.user, 'phone'):
                self.interpreter_phone = self.user.phone
        
        # Auto-populate from interpreter if available
        if self.interpreter and not self.pk:
            if not self.interpreter_name:
                self.interpreter_name = f"{self.interpreter.user.first_name} {self.interpreter.user.last_name}"
            if not self.interpreter_email:
                self.interpreter_email = self.interpreter.user.email
            if not self.interpreter_phone:
                self.interpreter_phone = self.interpreter.user.phone
            if not self.interpreter_address:
                self.interpreter_address = f"{self.interpreter.address}, {self.interpreter.city}, {self.interpreter.state} {self.interpreter.zip_code}"
        
        # Generate token and OTP if this is a new record and they're not set
        if not self.pk:
            if not self.token:
                self.token = str(uuid.uuid4())
            if not self.otp_code:
                self.otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            if not self.expires_at:
                self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        
        super().save(*args, **kwargs)

class Document(models.Model):
    """
    Modèle pour stocker les documents générés avec leurs métadonnées.
    Peut être utilisé pour des contrats, factures, devis, etc.
    """
    DOCUMENT_TYPES = [
        ('CONTRACT', 'Contract'),
        ('INVOICE', 'Invoice'),
        ('QUOTE', 'Quote'),
        ('CERTIFICATE', 'Certificate'),
        ('LETTER', 'Letter'),
        ('REPORT', 'Report'),
        ('OTHER', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SIGNED', 'Signed'),
        ('SENT', 'Sent'),
        ('CANCELLED', 'Cancelled'),
        ('ARCHIVED', 'Archived')
    ]
    
    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_number = models.CharField(
        max_length=50, 
        unique=True,
        null=True,
        blank=True,
        help_text="Numéro unique du document (généré automatiquement)"
    )
    agreement_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="ID de l'accord associé, si applicable"
    )
    
    # Informations de base
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Relations
    user = models.ForeignKey(
        'User', 
        on_delete=models.PROTECT, 
        null=True,
        blank=True,
        related_name='documents'
    )
    interpreter_contract = models.ForeignKey(
        'InterpreterContractSignature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    
    # Fichier et données
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        null=True,
        blank=True
    )
    file_hash = models.CharField(
        max_length=128, 
        null=True, 
        blank=True,
        help_text="Hachage SHA-256 du fichier pour vérification d'intégrité"
    )
    
    # Métadonnées PGP
    pgp_signature = models.TextField(
        null=True, 
        blank=True,
        help_text="Signature PGP du document"
    )
    signing_key = models.ForeignKey(
        'PGPKey',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='signed_documents'
    )
    
    # Métadonnées temporelles
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées JSON pour des champs flexibles
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Métadonnées PDF et informations supplémentaires"
    )
    
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['agreement_id']),
            models.Index(fields=['document_type']),
            models.Index(fields=['created_at']),
        ]
        db_table = 'app_document'
    
    def __str__(self):
        return f"{self.title} - {self.document_number}"
    
    def save(self, *args, **kwargs):
        # Générer le numéro de document s'il n'existe pas
        if not self.document_number:
            self.document_number = self.generate_document_number()
        
        # Calculer le hachage du fichier s'il existe
        if self.file and not self.file_hash:
            self.calculate_file_hash()
        
        # Si le statut devient 'SIGNED', enregistrer la date de signature
        if self.status == 'SIGNED' and not self.signed_at:
            self.signed_at = timezone.now()
            
        super().save(*args, **kwargs)
    
    def generate_document_number(self):
        """Génère un numéro de document unique."""
        today = timezone.now()
        prefix_map = {
            'CONTRACT': 'CONT',
            'INVOICE': 'INV',
            'QUOTE': 'QUO',
            'CERTIFICATE': 'CERT',
            'LETTER': 'LTR',
            'REPORT': 'RPT',
            'OTHER': 'DOC'
        }
        prefix = prefix_map.get(self.document_type, 'DOC')
        
        # Format: PREFIX-YEAR-MONTH-RANDOM
        random_part = str(uuid.uuid4())[:6].upper()
        return f"{prefix}-{today.year}{today.month:02d}-{random_part}"
    
    def calculate_file_hash(self):
        """Calcule le hachage SHA-256 du fichier."""
        if not self.file:
            return
        
        self.file.open(mode='rb')
        content = self.file.read()
        self.file.close()
        
        self.file_hash = hashlib.sha256(content).hexdigest()
    
    def add_metadata(self, key, value):
        """Ajoute une métadonnée au document."""
        metadata = self.metadata or {}
        metadata[key] = value
        self.metadata = metadata
    
    def get_metadata(self, key, default=None):
        """Récupère une métadonnée du document."""
        return (self.metadata or {}).get(key, default)
    
    def sign_document(self, key=None):
        """
        Signe le document avec PGP. Cette méthode devra être implémentée
        selon votre infrastructure spécifique.
        """
        # Code de signature PGP à implémenter selon votre système
        pass

class SignedDocument(models.Model):
    """Modèle pour les documents signés"""
    SIGNATURE_TYPES = [
        ('handwritten', 'Signature manuscrite'),
        ('image', 'Image de signature'),
        ('typographic', 'Signature typographique'),
    ]
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=True, blank=True)
    original_document = models.FileField(upload_to=pdf_upload_path)
    signed_document = models.FileField(upload_to=pdf_upload_path, null=True, blank=True)
    signature_image = models.ImageField(upload_to=signature_upload_path, null=True, blank=True)
    signature_type = models.CharField(max_length=20, choices=SIGNATURE_TYPES)
    signature_position = models.JSONField(default=dict)  # Stocke les coordonnées x, y, page, width, height
    signature_metadata = models.JSONField(default=dict)  # Stocke auteur, raison, date, etc
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'app_signeddocument'
    
    def __str__(self):
        return f"Document signé le {self.created_at.strftime('%d/%m/%Y')}"
