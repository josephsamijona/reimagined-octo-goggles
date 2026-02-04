import io
import json
import time
import random
import string
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import pytz
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet

# Constants
BOSTON_TZ = pytz.timezone('America/New_York')
TZ_BOSTON = BOSTON_TZ  # Alias for compatibility
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

@csrf_exempt
@require_http_methods(["POST"])
def generate_pdf(request):
    """
    Vue pour générer un PDF à partir d'une capture d'écran.
    """
    try:
        # Récupérer et valider les données JSON
        try:
            data = json.loads(request.body)
            if 'imageData' not in data:
                return JsonResponse({
                    'error': 'Données d\'image manquantes'
                }, status=400)
            
            image_data = data['imageData'].split(',')[1]
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Données JSON invalides'
            }, status=400)
        
        # Décodage de l'image
        try:
            import base64
            from PIL import Image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return JsonResponse({
                'error': f'Erreur lors du traitement de l\'image: {str(e)}'
            }, status=400)

        # Création du PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        title_style.alignment = 1  # Center
        
        # Contenu
        elements = []
        
        # Titre
        elements.append(Paragraph("Capture d'écran", title_style))
        elements.append(Spacer(1, 20))
        
        # Image
        # Calculer la taille pour qu'elle tienne dans la page
        img_width, img_height = image.size
        aspect = img_height / float(img_width)
        
        available_width = letter[0] - 60
        available_height = letter[1] - 100
        
        display_width = available_width
        display_height = display_width * aspect
        
        if display_height > available_height:
            display_height = available_height
            display_width = display_height / aspect
            
        # Sauvegarder l'image temporairement pour ReportLab
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            image.save(tmp_file, format='PNG')
            tmp_path = tmp_file.name
            
        from reportlab.platypus import Image as RLImage
        rl_image = RLImage(tmp_path, width=display_width, height=display_height)
        elements.append(rl_image)
        
        # Générer
        doc.build(elements)
        
        # Nettoyage
        try:
            os.unlink(tmp_path)
        except:
            pass
            
        # Réponse
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response = JsonResponse({
            'success': True,
            'pdf_base64': base64.b64encode(pdf_data).decode('utf-8')
        })
        return response

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def format_decimal(value):
    """Format decimal numbers to remove trailing zeros if no cents"""
    if value is None:
        return "0"
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    formatted = f"{value:.2f}"
    if formatted.endswith('.00'):
        return formatted[:-3]
    return formatted

def generate_document_number():
    """Generate a unique document number based on timestamp and random string"""
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"DOC-{timestamp}-{random_str}"

def calculate_trend(current, previous):
    """
    Calcule le pourcentage d'évolution entre deux valeurs
    """
    if not previous:
        return 0
    try:
        return round(((current - previous) / previous) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0

def calculate_percentage(part, total):
    """
    Calcule le pourcentage d'une partie par rapport au total
    """
    if not total:
        return 0
    try:
        return round((part / total) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0
