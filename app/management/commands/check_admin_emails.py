"""
Commande de diagnostic pour vérifier les emails des administrateurs.
"""
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from app.models import User


class Command(BaseCommand):
    help = 'Vérifie la validité des emails des administrateurs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Vérification des emails administrateurs'))
        self.stdout.write('')

        admin_users = User.objects.filter(role='ADMIN')

        if not admin_users.exists():
            self.stdout.write(self.style.WARNING('Aucun utilisateur avec le rôle ADMIN trouvé'))
            return

        total_admins = admin_users.count()
        active_admins = admin_users.filter(is_active=True).count()
        valid_emails = 0
        invalid_emails = 0

        self.stdout.write(f'Total administrateurs: {total_admins}')
        self.stdout.write(f'Administrateurs actifs: {active_admins}')
        self.stdout.write('')

        for user in admin_users:
            status_parts = []

            # Vérifier si actif
            if user.is_active:
                status_parts.append(self.style.SUCCESS('ACTIF'))
            else:
                status_parts.append(self.style.WARNING('INACTIF'))

            # Vérifier l'email
            email = user.email.strip() if user.email else ''

            if not email:
                status_parts.append(self.style.ERROR('EMAIL VIDE'))
                invalid_emails += 1
            else:
                try:
                    validate_email(email)
                    status_parts.append(self.style.SUCCESS('EMAIL VALIDE'))
                    valid_emails += 1
                except ValidationError:
                    status_parts.append(self.style.ERROR('EMAIL INVALIDE'))
                    invalid_emails += 1

            # Afficher les informations de l'utilisateur
            self.stdout.write(
                f"  [{user.id}] {user.username:20s} | {email:40s} | {' | '.join(status_parts)}"
            )

        # Résumé
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Résumé'))
        self.stdout.write(f'Emails valides: {valid_emails}')

        if invalid_emails > 0:
            self.stdout.write(self.style.ERROR(f'Emails invalides ou vides: {invalid_emails}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'ATTENTION: Les administrateurs avec des emails invalides ne recevront pas les notifications!'
            ))
            self.stdout.write(self.style.WARNING(
                'Corrigez ces emails dans l\'admin Django ou la base de données.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Tous les emails administrateurs sont valides!'))

        # Vérifier les admins actifs avec emails valides
        active_valid = 0
        for user in admin_users.filter(is_active=True):
            email = user.email.strip() if user.email else ''
            if email:
                try:
                    validate_email(email)
                    active_valid += 1
                except ValidationError:
                    pass

        self.stdout.write('')
        if active_valid == 0:
            self.stdout.write(self.style.ERROR(
                'CRITIQUE: Aucun administrateur actif avec email valide! '
                'Les notifications ne peuvent pas être envoyées.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Administrateurs actifs avec email valide: {active_valid}'
            ))
