# Fix pour l'erreur de validation email Resend

## Problème résolu

L'application générait une erreur lors de l'envoi d'emails via l'API Resend :
```
ERROR Failed to send email via Resend: Invalid `to` field. The email address needs to follow the `email@example.com` or `Name <email@example.com>` format.
```

**Cause identifiée** : Un ou plusieurs administrateurs avaient des adresses email invalides dans la base de données (exemple : UUID au lieu d'un email valide), ce qui causait l'échec de l'envoi des notifications administrateurs.

## Solution implémentée

### 1. Validation des emails dans `AssignmentNotificationService`

**Fichier** : `app/services/assignment_notifications.py`

- Ajout d'une méthode statique `_validate_and_clean_email()` qui :
  - Nettoie les espaces avant/après
  - Valide le format email avec Django's `validate_email`
  - Retourne `None` pour les emails invalides
  - Log les emails invalides pour diagnostic

- Modification de `notify_admin()` pour :
  - Valider chaque email admin avant l'envoi
  - Logger les admins avec emails invalides (username, ID, email)
  - Continuer avec les emails valides
  - Retourner `False` si aucun email valide n'est trouvé

### 2. Validation robuste dans le backend Resend

**Fichier** : `app/utils/email_backend.py`

- Ajout de la méthode `_clean_email_list()` qui :
  - Filtre et valide tous les emails (to, cc, bcc)
  - Ne conserve que les emails valides
  - Log les emails invalides ignorés

- Modification de `_convert_message_to_resend()` pour :
  - Valider tous les destinataires avant conversion
  - Ne pas envoyer si aucun destinataire valide

- Modification de `send_messages()` pour :
  - Vérifier qu'il y a au moins un destinataire valide
  - Logger et skip les messages sans destinataires valides

### 3. Commande de diagnostic

**Fichier** : `app/management/commands/check_admin_emails.py`

Nouvelle commande Django pour diagnostiquer les problèmes d'emails admin :

```bash
python manage.py check_admin_emails
```

Cette commande affiche :
- Liste de tous les administrateurs avec leur statut (actif/inactif)
- Validation de chaque email
- Résumé des emails valides/invalides
- Alerte si aucun admin actif n'a d'email valide

### 4. Tests automatisés

**Fichier** : `app/tests/test_assignment_service.py`

Ajout de tests unitaires pour :
- `AssignmentNotificationService._validate_and_clean_email()`
- `ResendEmailBackend._clean_email_list()`

Tests couvrant :
- Emails valides
- Emails avec espaces
- Emails invalides
- Listes mixtes valides/invalides
- Listes vides

## Résultats du diagnostic

```
python manage.py check_admin_emails
```

**Résultat actuel** :
- 1 administrateur actif trouvé (ID: 147, username: twfmw0pcwg)
- Email invalide : `617b9590-e0a1-701b-16a4-a33f9f09f10b` (UUID au lieu d'email)
- **CRITIQUE** : Aucun admin avec email valide → notifications impossibles

## Actions requises

### 1. Corriger l'email administrateur invalide

**Option A : Via Django Admin**
```
1. Se connecter à l'admin Django : /admin/
2. Aller dans Users
3. Trouver l'utilisateur ID 147 (twfmw0pcwg)
4. Modifier le champ email avec une adresse valide (ex: admin@jhbridge.com)
5. Sauvegarder
```

**Option B : Via shell Django**
```bash
python manage.py shell
```
```python
from app.models import User
admin = User.objects.get(id=147)
admin.email = 'admin@jhbridge.com'  # Remplacer par le vrai email
admin.save()
print(f"Email mis à jour : {admin.email}")
```

**Option C : Via SQL direct (si nécessaire)**
```sql
UPDATE app_user
SET email = 'admin@jhbridge.com'
WHERE id = 147;
```

### 2. Vérifier la correction

Après avoir corrigé l'email, relancer la commande de diagnostic :

```bash
python manage.py check_admin_emails
```

Résultat attendu :
```
✓ Emails valides: 1
✓ Administrateurs actifs avec email valide: 1
```

### 3. Tester l'envoi de notifications

Tester l'acceptation d'une assignation pour vérifier que les notifications admin fonctionnent :

1. Créer ou utiliser une assignation existante
2. Faire accepter l'assignation par un interprète (via le lien email)
3. Vérifier les logs pour confirmer l'envoi réussi :
   ```
   INFO Email sent successfully via Resend API. ID: [resend-id]
   ```

## Bénéfices de la solution

1. **Robustesse** : Le système continue de fonctionner même avec des emails invalides
2. **Visibilité** : Les emails invalides sont loggés pour correction
3. **Prévention** : Toute tentative d'envoi à un email invalide est interceptée
4. **Diagnostic** : Commande dédiée pour identifier rapidement les problèmes
5. **Couverture** : Tests automatisés assurent la pérennité du correctif

## Comportement après correctif

### Avant
❌ Erreur Resend → Échec complet de l'envoi
❌ Aucune notification aux admins valides
❌ Pas de visibilité sur le problème

### Après
✅ Emails invalides filtrés automatiquement
✅ Notifications envoyées aux admins avec emails valides
✅ Warnings loggés pour les emails invalides
✅ Commande de diagnostic disponible
✅ Système résilient aux données invalides

## Maintenance future

### Bonnes pratiques
1. Exécuter `python manage.py check_admin_emails` régulièrement
2. Surveiller les logs pour les warnings "Invalid email" ou "Invalid admin email"
3. Valider les emails lors de la création de nouveaux admins
4. Considérer l'ajout d'une validation au niveau du modèle User

### Amélioration potentielle (optionnelle)
Ajouter une validation au niveau du modèle `User` dans `app/models/users.py` :

```python
from django.core.validators import EmailValidator

class User(AbstractUser):
    email = models.EmailField(
        _('email address'),
        validators=[EmailValidator()],
        unique=True,
        blank=False  # Rendre obligatoire
    )
```

⚠️ Ceci nécessiterait une migration Django et la correction de toutes les données existantes.

## Support

Si le problème persiste après correction de l'email :
1. Vérifier les logs Resend pour plus de détails
2. Vérifier la variable d'environnement `RESEND_API_KEY`
3. Tester l'envoi d'email simple via `python manage.py shell`
4. Contacter le support Resend si l'API rejette toujours des emails valides
