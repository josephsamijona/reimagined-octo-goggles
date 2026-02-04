from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone

class AuditLog(models.Model):
    user = models.ForeignKey('User', on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'app_auditlog'
        
class APIKey(models.Model):
    """Modèle pour gérer les clés API"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='api_keys'
    )
    name = models.CharField(max_length=100, help_text="Nom pour identifier cette clé API")
    app_name = models.CharField(max_length=100, help_text="Nom de l'application utilisant cette clé API")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Clé API"
        verbose_name_plural = "Clés API"
        ordering = ['-created_at']
        db_table = 'app_apikey'
    
    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"
    
    def is_valid(self):
        """Vérifie si la clé API est valide (active et non expirée)"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    def mark_as_used(self):
        """Marque la clé comme utilisée en mettant à jour le timestamp de dernière utilisation"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    @classmethod
    def generate_key(cls):
        """Génère une nouvelle clé API unique"""
        return uuid.uuid4().hex + uuid.uuid4().hex  # 64 caractères

class PGPKey(models.Model):
    """
    Modèle pour stocker les clés PGP utilisées pour signer les documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Nom descriptif de cette clé")
    key_id = models.CharField(max_length=100, unique=True, help_text="Identifiant de la clé PGP (16 derniers caractères de l'empreinte)")
    fingerprint = models.CharField(max_length=255, blank=True, null=True, help_text="Empreinte complète de la clé PGP")
    public_key = models.TextField(help_text="Clé publique PGP au format ASCII")
    
    # La clé privée est stockée dans un environnement sécurisé externe
    # et référencée par cet identifiant - ne jamais stocker la clé privée en DB
    private_key_reference = models.CharField(
        max_length=255,
        help_text="Référence sécurisée à la clé privée (chemin ou identifiant)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Nouveau: date de mise à jour
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Nouveaux champs utiles
    algorithm = models.CharField(max_length=50, blank=True, null=True, help_text="Algorithme utilisé (RSA, etc.)")
    key_size = models.PositiveIntegerField(null=True, blank=True, help_text="Taille de la clé en bits")
    user_name = models.CharField(max_length=255, blank=True, null=True, help_text="Nom associé à la clé")
    user_email = models.EmailField(blank=True, null=True, help_text="Email associé à la clé")
    
    class Meta:
        verbose_name = "PGP Key"
        verbose_name_plural = "PGP Keys"
        ordering = ['-created_at']
        db_table = 'app_pgpkey'
    
    def __str__(self):
        return f"{self.name} ({self.key_id})"
    
    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Calcule le nombre de jours restants avant expiration"""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    @property
    def short_key_id(self):
        """Retourne les 8 derniers caractères de l'ID de clé (format court)"""
        if not self.key_id:
            return None
        return self.key_id[-8:] if len(self.key_id) >= 8 else self.key_id
    
    def extract_key_info(self):
        """
        Extrait les informations de la clé publique si possible.
        Cette méthode peut être appelée lors de la sauvegarde pour remplir
        automatiquement les métadonnées.
        """
        if not self.public_key:
            return
            
        try:
            from pgpy import PGPKey as PGPyKey
            
            # Analyser la clé publique
            public_key = PGPyKey()
            public_key.parse(self.public_key)
            
            # Extraire les informations
            if hasattr(public_key, 'fingerprint'):
                self.fingerprint = public_key.fingerprint.upper()
                
            # Extraire l'algorithme et la taille si possible
            # Cette partie dépend de la structure interne de PGPy
            if public_key.key_algorithm:
                self.algorithm = str(public_key.key_algorithm)
                
            # Extraire les informations utilisateur si disponibles
            for uid in public_key.userids:
                if uid.name:
                    self.user_name = uid.name
                if uid.email:
                    self.user_email = uid.email
                break  # On prend seulement le premier UID
                
        except Exception:
            # En cas d'erreur, on ne fait rien
            pass
    
    def save(self, *args, **kwargs):
        """
        Surcharge de la méthode save pour extraire automatiquement 
        les informations de la clé publique.
        """
        # Si la fingerprint n'est pas définie mais que key_id existe,
        # on utilise key_id comme valeur par défaut
        if not self.fingerprint and self.key_id:
            self.fingerprint = self.key_id
            
        # Essayer d'extraire les informations de la clé
        self.extract_key_info()
        
        super().save(*args, **kwargs)
