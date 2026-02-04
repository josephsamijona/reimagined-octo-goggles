import json
import logging
import socket
import time
import uuid
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views import View
from django.contrib import messages
from django.views.decorators.cache import never_cache

from ...models import InterpreterContractSignature, Document

logger = logging.getLogger(__name__)

@method_decorator(never_cache, name='dispatch')
class ContractConfirmationView(View):
    template_name = 'signature_app/confirmationsign.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        logger.info("Confirmation page accessed")
        
        # Vérification des sessions
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        otp_verified = request.session.get('otp_verified', False)
        payment_info_completed = request.session.get('payment_info_completed', False)
        signature_completed = request.session.get('signature_completed', False)
        
        # Vérifier que l'utilisateur a bien complété les étapes précédentes
        if not all([contract_id, agreement_number, otp_verified, payment_info_completed, signature_completed]):
            logger.warning("Unauthorized access attempt to confirmation page")
            messages.error(request, 'You must complete the previous steps first.')
            return render(request, self.template_name_error, {'error': 'Unauthorized access'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Générer le PDF et envoyer l'email si ce n'est pas déjà fait
            if not request.session.get('pdf_generated'):
                success = self.process_contract_pdf(contract, agreement_number)
                
                if success:
                    request.session['pdf_generated'] = True
                    messages.success(request, 'Your contract has been generated and sent to your email.')
                else:
                    messages.warning(request, 'There was an issue generating your contract. Our team has been notified.')
            
            # Préparer les données bancaires sécurisées
            account_number = None
            routing_number = None
            swift_code = None
            
            try:
                if contract.encrypted_account_number:
                    account_number = contract.get_account_number()
                    # Masquer le numéro de compte pour l'affichage
                    if account_number and len(account_number) > 4:
                        account_number = '••••' + account_number[-4:]
                
                if contract.encrypted_routing_number:
                    routing_number = contract.get_routing_number()
                    # Masquer le numéro de routage pour l'affichage
                    if routing_number and len(routing_number) > 4:
                        routing_number = '••••' + routing_number[-4:]
                
                if contract.encrypted_swift_code:
                    swift_code = contract.get_swift_code()
                    # Masquer le code SWIFT pour l'affichage
                    if swift_code and len(swift_code) > 4:
                        swift_code = '••••' + swift_code[-4:]
            except Exception as e:
                logger.error(f"Error decrypting banking information: {str(e)}")
                # Continuer même si le déchiffrement échoue
            
            # Préparation des informations de signature
            signature_info = {
                'type': contract.signature_type,
                'display_type': self.get_signature_display_type(contract.signature_type),
                'font': None,
                'data': None,
                'image_url': None
            }
            
            # Récupérer les données de signature selon le type
            if contract.signature_type == 'type':
                signature_info['data'] = contract.signature_typography_text
                signature_info['font'] = getattr(contract, 'signature_typography_font', 'font-brush-script')
            elif contract.signature_type == 'draw':
                signature_info['data'] = contract.signature_manual_data
            elif contract.signature_type == 'upload' and contract.signature_image:
                signature_info['image_url'] = contract.signature_image.url
            
            # Journal pour le débogage
            logger.info(f"Signature type: {contract.signature_type}")
            logger.info(f"Signature typography text: {contract.signature_typography_text}")
            logger.info(f"Signature manual data exists: {'Yes' if contract.signature_manual_data else 'No'}")
            logger.info(f"Signature image exists: {'Yes' if contract.signature_image else 'No'}")
            
            # Préparation du contexte pour la page de confirmation
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'interpreter_email': contract.interpreter_email,
                'interpreter_phone': contract.interpreter_phone,
                'interpreter_address': contract.interpreter_address,
                'agreement_number': agreement_number,
                'account_holder_name': contract.account_holder_name,
                'bank_name': contract.bank_name,
                'account_type': contract.account_type,
                'account_number': account_number,
                'routing_number': routing_number,
                'swift_code': swift_code,
                'signed_at': contract.signed_at,
                'signature_type': contract.signature_type,
                'signature_info': signature_info,
                'current_date': timezone.now().strftime('%B %d, %Y %H:%M:%S')
            }
            
            logger.info(f"Confirmation page rendered for contract ID: {contract_id}")
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in confirmation page: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def get_signature_display_type(self, signature_type):
        """Retourne un nom lisible pour le type de signature."""
        types = {
            'draw': 'Drawn Signature',
            'type': 'Typed Signature',
            'upload': 'Uploaded Signature',
            None: 'Electronic Signature'
        }
        return types.get(signature_type, 'Electronic Signature')
    
    def process_contract_pdf(self, contract, agreement_number):
        """
        Processus complet de génération et envoi du PDF
        """
        try:
            logger.info(f"Starting PDF process for contract {contract.id}")
            
            # 1. Créer une clé PGP pour ce contrat
            logger.info("Step 1: Creating PGP key...")
            pgp_key = self._create_pgp_key_for_contract(contract)
            
            # 2. Créer un document dans la base de données
            logger.info("Step 2: Creating document record...")
            document = self._create_document_record(contract, pgp_key, agreement_number)
            
            # 3. Préparer les données pour l'API
            logger.info("Step 3: Preparing PDF data...")
            pdf_data = self._prepare_pdf_data(contract, document, agreement_number)
            
            # 4. Envoyer à l'API PDF
            logger.info("Step 4: Sending to PDF API...")
            pdf_download_url = self._send_to_pdf_api(pdf_data)
            
            if not pdf_download_url:
                logger.error("Failed to get PDF download URL from API")
                raise Exception("Failed to get PDF download URL from API")
            
            logger.info(f"Received download URL: {pdf_download_url[:100]}...")
            
            # 5. Télécharger le PDF
            logger.info("Step 5: Downloading PDF...")
            pdf_content = self._download_pdf(pdf_download_url)
            
            if not pdf_content:
                logger.error("Failed to download PDF content")
                raise Exception("Failed to download PDF content")
            
            logger.info(f"Downloaded PDF: {len(pdf_content)} bytes")
            
            # 6. Sauvegarder le PDF
            logger.info("Step 6: Saving PDF to storage...")
            pdf_path = self._save_pdf_to_storage(contract, pdf_content)
            
            # 7. Mettre à jour les enregistrements
            logger.info("Step 7: Updating records...")
            self._update_records_with_pdf(contract, document, pdf_path)
            
            # 8. Envoyer l'email avec le PDF
            logger.info("Step 8: Sending confirmation email...")
            self._send_confirmation_email_with_pdf(contract, pdf_content, agreement_number)
            
            logger.info(f"PDF process completed successfully for contract {contract.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in PDF process for contract {contract.id}: {str(e)}", exc_info=True)
            
            # Envoyer une notification à l'équipe technique
            try:
                # TODO: Implement Slack/PagerDuty notification for critical failures
                logger.critical(f"PDF generation failed for contract {contract.id} - {contract.interpreter_email}")
            except Exception as e:
                logger.error(f"Failed to log critical PDF error: {e}")
                
            return False
    
    def _create_pgp_key_for_contract(self, contract):
        """Crée une clé PGP dérivée pour ce contrat"""
        from ...models import PGPKey
        from ...mixins.signup_mixins import KeyDerivationMixin
        
        try:
            key_name = f"Contract Key - {contract.interpreter_name} - {contract.id}"
            pgp_key = KeyDerivationMixin.derive_key(
                name=key_name,
                user_name=contract.interpreter_name,
                user_email=contract.interpreter_email,
                expiry_days=365 * 5
            )
            
            logger.info(f"PGP key created for contract {contract.id}: {pgp_key.key_id}")
            return pgp_key
            
        except Exception as e:
            logger.error(f"Error creating PGP key: {str(e)}")
            raise
    
    def _create_document_record(self, contract, pgp_key, agreement_number):
        """Crée un enregistrement dans la table Document"""
        from ...models import Document
        
        try:
            document = Document.objects.create(
                title=f"Interpreter Service Agreement - {contract.interpreter_name}",
                document_type='CONTRACT',
                status='DRAFT',
                user=contract.user,
                interpreter_contract=contract,
                signing_key=pgp_key,
                agreement_id=agreement_number
            )
            
            document.add_metadata('contract_id', str(contract.id))
            document.add_metadata('interpreter_email', contract.interpreter_email)
            document.add_metadata('signature_type', contract.signature_type)
            document.save()
            
            logger.info(f"Document record created: {document.document_number}")
            return document
            
        except Exception as e:
            logger.error(f"Error creating document record: {str(e)}")
            raise
    
    def _prepare_pdf_data(self, contract, document, agreement_number):
        """
        Prépare les données pour l'API PDF
        Utilise les informations décryptées et les URLs existantes dans la DB
        """
        # Décrypter les informations bancaires
        account_number = contract.get_account_number() if contract.encrypted_account_number else ""
        routing_number = contract.get_routing_number() if contract.encrypted_routing_number else ""
        swift_code = contract.get_swift_code() if contract.encrypted_swift_code else ""
        
        # Déterminer la signature selon le type stocké dans la DB
        signature_type = 'text'  # Valeur par défaut
        signature_value = contract.interpreter_name  # Valeur par défaut
        
        if contract.signature_type == 'type':
            # Signature typographique - texte simple
            signature_type = 'text'
            signature_value = contract.signature_typography_text
            
        elif contract.signature_type == 'draw':
            # Signature dessinée - utiliser l'URL stockée dans signature_converted_url
            if contract.signature_converted_url:
                signature_type = 'image'
                signature_value = contract.get_signature_url()  # URL déjà complète depuis B2
            
        elif contract.signature_type == 'upload':
            # Signature uploadée - utiliser l'URL de signature_image
            if contract.signature_image:
                signature_type = 'image'
                signature_value = contract.get_signature_url()  # Utilise la méthode du modèle
        
        # Générer la signature PGP
        pgp_signature = self._generate_pgp_signature(contract, document)
        
        pdf_data = {
            "agreement_id": agreement_number,
            "date_created": timezone.now().strftime("%B %d, %Y"),
            "agreement_date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y"),
            "interpreter": {
                "name": contract.interpreter_name,
                "address": contract.interpreter_address,
                "contact_information": f"{contract.interpreter_email} | {contract.interpreter_phone}"
            },
            "company_signature": {
                "type": "text",
                "value": contract.company_representative_name,
                "date": contract.company_signed_at.strftime("%B %d, %Y") if contract.company_signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "interpreter_signature": {
                "type": signature_type,
                "value": signature_value,
                "date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "personal_information": {
                "name": contract.interpreter_name,
                "address": contract.interpreter_address,
                "phone": contract.interpreter_phone,
                "email": contract.interpreter_email
            },
            "account_type": contract.account_type.capitalize() if contract.account_type else "Checking",
            "banking_information": {
                "bank_name": contract.bank_name or "",
                "bank_address": contract.interpreter_address,  # Utiliser l'adresse de l'interprète
                "account_holder_name": contract.account_holder_name or contract.interpreter_name,
                "account_number": account_number,  # Décrypté
                "routing_number": routing_number,  # Décrypté
                "swift_code": swift_code  # Décrypté
            },
            "authorization": {
                "signature": {
                    "type": signature_type,
                    "value": signature_value
                },
                "date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "document_metadata": {
                "document_number": document.document_number,
                "agreement_id": agreement_number,
                "title": document.title,
                "document_type": document.document_type,
                "user": f"USR-{contract.user.id}" if contract.user else None,
                "interpreter_contract": f"IC-{contract.id}",
                "pgp_signature": pgp_signature,
                "signing_key": document.signing_key.key_id if document.signing_key else None,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
                "metadata": document.metadata
            }
        }
        
        return pdf_data
    
    def _generate_pgp_signature(self, contract, document):
        """Génère la signature PGP pour le document"""
        try:
            from ...mixins.signup_mixins import KeyDerivationMixin
            
            content_to_sign = f"{document.document_number}|{contract.id}|{contract.interpreter_email}|{contract.signed_at}"
            
            if document.signing_key:
                signature, success, message = KeyDerivationMixin.generate_signature(
                    content_to_sign,
                    document.signing_key.key_id
                )
                
                if success:
                    return f"-----BEGIN PGP SIGNATURE-----\nVersion: BCPG v1.69\n\n{signature}\n-----END PGP SIGNATURE-----"
            
            logger.warning(f"Failed to generate PGP signature for document {document.id}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating PGP signature: {e}")
            return None
    
    def _send_to_pdf_api(self, pdf_data):
        """Envoie les données à l'API PDF en utilisant la bibliothèque requests."""
        try:
            # URL fixe de l'API sur Railway
            api_url = 'https://jhbridge-esign-production.up.railway.app/api/generate-contract'
            
            # Si vous voulez utiliser les settings, assurez-vous que settings.API_URL_PDF_GENERATOR est correct
            # api_url = settings.API_URL_PDF_GENERATOR
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': settings.PDF_GENERATOR_API_KEY  # Assurez-vous que cette clé est correcte dans settings
            }
            
            logger.info(f"Envoi de la requête POST à l'API PDF : {api_url}")
            logger.debug(f"Headers: {headers}")
            
            # Log des données envoyées (sans les infos sensibles)
            safe_data = {
                'agreement_id': pdf_data.get('agreement_id'),
                'interpreter_name': pdf_data.get('interpreter', {}).get('name'),
                'document_number': pdf_data.get('document_metadata', {}).get('document_number')
            }
            logger.info(f"Envoi de données pour : {safe_data}")

            # Utiliser un timeout de 310 secondes (légèrement plus que le timeout de Next.js)
            response = requests.post(
                api_url, 
                json=pdf_data,  # Utiliser json= au lieu de data=json.dumps()
                headers=headers, 
                timeout=310
            )

            logger.info(f"Réponse de l'API PDF - Statut : {response.status_code}")
            
            # Vérifier le statut de la réponse
            if response.status_code != 200:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:500]}"
                logger.error(error_msg)
                return None

            # Parser la réponse JSON
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                logger.error(f"Response text: {response.text[:500]}")
                return None

            # Vérifier le succès de l'opération
            if not response_json.get('success', False):
                logger.error(f"API indicated failure: {response_json.get('error', 'Unknown error')}")
                return None

            # Récupérer l'URL de téléchargement
            download_url = response_json.get('downloadUrl')
            
            if not download_url:
                logger.error("No 'downloadUrl' in API response")
                logger.error(f"Response data: {response_json}")
                return None

            # Logs additionnels pour le débogage
            logger.info(f"PDF généré avec succès")
            logger.info(f"Download URL: {download_url[:100]}...")
            logger.info(f"Filename: {response_json.get('fileName')}")
            logger.info(f"Expires: {response_json.get('expires')}")
            
            return download_url

        except requests.exceptions.HTTPError as http_err:
            error_details = str(http_err)
            if http_err.response is not None:
                try:
                    error_json = http_err.response.json()
                    error_details = f"{http_err} - {error_json.get('error', error_json)}"
                except:
                    error_details = f"{http_err} - {http_err.response.text[:500]}"
            logger.error(f"HTTP error calling PDF API: {error_details}")
            return None
            
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error to PDF API: {conn_err}")
            return None
            
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout calling PDF API (after 310s): {timeout_err}")
            return None
            
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request exception calling PDF API: {req_err}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error calling PDF API: {str(e)}", exc_info=True)
            return None
    
    def _download_pdf(self, download_url):
        """Télécharge le PDF depuis l'URL fournie par l'API"""
        try:
            logger.info(f"Downloading PDF from: {download_url[:100]}...")
            
            # Augmenter le timeout pour les gros fichiers
            response = requests.get(download_url, timeout=60, stream=True)
            
            # Vérifier le statut
            if response.status_code != 200:
                logger.error(f"Failed to download PDF: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return None
            
            # Vérifier le Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type:
                logger.warning(f"Unexpected Content-Type: {content_type}")
            
            # Télécharger le contenu
            pdf_content = response.content
            
            # Vérifier la taille
            content_length = len(pdf_content)
            if content_length == 0:
                logger.error("Downloaded PDF is empty")
                return None
            
            logger.info(f"PDF downloaded successfully: {content_length} bytes")
            
            # Vérifier que c'est bien un PDF
            if not pdf_content.startswith(b'%PDF'):
                logger.error("Downloaded file is not a valid PDF")
                logger.error(f"First bytes: {pdf_content[:20]}")
                return None
            
            return pdf_content
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading PDF from: {download_url}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading PDF: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF: {e}", exc_info=True)
            return None
    
    def _save_pdf_to_storage(self, contract, pdf_content):
        """Sauvegarde le PDF"""
        try:
            filename = f"contracts/contract_{contract.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            path = default_storage.save(
                filename,
                ContentFile(pdf_content)
            )
            
            logger.info(f"PDF saved to storage: {path}")
            return path
            
        except Exception as e:
            logger.error(f"Error saving PDF to storage: {str(e)}")
            raise
    
    def _update_records_with_pdf(self, contract, document, pdf_path):
        """Met à jour les enregistrements"""
        try:
            # Mettre à jour le contrat
            contract.contract_document = pdf_path
            contract.save()
            
            # Mettre à jour le document
            document.file = pdf_path
            document.status = 'SIGNED'
            document.signed_at = timezone.now()
            document.calculate_file_hash()
            document.save()
            
            logger.info(f"Records updated with PDF path: {pdf_path}")
            
        except Exception as e:
            logger.error(f"Error updating records: {str(e)}")
            raise
    
    def _send_confirmation_email_with_pdf(self, contract, pdf_content, agreement_number):
        """Envoie l'email de confirmation avec le PDF en pièce jointe"""
        try:
            # Création d'un identifiant unique pour ce message
            message_id = f"<confirmation-{contract.id}-{uuid.uuid4()}@{socket.gethostname()}>"
            
            # Préparation des données pour le template
            context = {
                'interpreter_name': contract.interpreter_name,
                'email': contract.interpreter_email,
                'agreement_number': agreement_number,
                'signed_date': contract.signed_at.strftime('%B %d, %Y') if contract.signed_at else timezone.now().strftime('%B %d, %Y'),
            }
            
            # Rendu du template HTML
            html_message = render_to_string('notifmail/contract_agreement_good.html', context)
            plain_message = strip_tags(html_message)
            
            # Ligne d'objet
            subject = f"Your Contract Has Been Approved! - JH Bridge"
            
            # Format professionnel pour l'adresse expéditeur
            from_email = f"JH Bridge Contracts <contracts@jhbridgetranslation.com>"
            
            # Création de l'email avec du texte brut comme corps principal
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[contract.interpreter_email],
                reply_to=['support@jhbridgetranslation.com']
            )
            
            # Ajout de la version HTML comme alternative
            email.attach_alternative(html_message, "text/html")
            
            # Attacher le PDF
            email.attach(
                f"contract_{contract.interpreter_name.replace(' ', '_')}.pdf",
                pdf_content,
                'application/pdf'
            )
            
            # En-têtes optimisés pour la délivrabilité
            email.extra_headers = {
                # Identifiant unique de message
                'Message-ID': message_id,
                
                # En-têtes d'authentification et de traçabilité
                'X-Entity-Ref-ID': str(contract.token),
                'X-Mailer': 'JHBridge-ContractMailer/1.0',
                'X-Contact-ID': str(contract.id),
                
                # Mécanisme de désabonnement
                'List-Unsubscribe': f'<mailto:unsubscribe@jhbridgetranslation.com?subject=Unsubscribe-{contract.interpreter_email}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                
                # En-têtes de classification du message
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                
                # ID unique pour le feedback loop
                'Feedback-ID': f'contract-{contract.id}:{contract.id}:jhbridge:{int(time.time())}'
            }
            
            # Envoi de l'email
            email.send(fail_silently=False)
            
            logger.info(f"Confirmation email sent to: {contract.interpreter_email} with Message-ID: {message_id}")
            
            # Mettre à jour le statut du contrat
            contract.status = 'COMPLETED'
            contract.save()
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}", exc_info=True)
            raise
            
def contract_render_view(request):
    """
    Vue très simple qui fait uniquement le rendu du template de contrat.
    """
    return render(request, 'contract/template_contract.html')
