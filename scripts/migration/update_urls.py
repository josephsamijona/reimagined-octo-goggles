import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.models import Document, InterpreterContractSignature, Interpreter, ClientPayment, Expense
from django.db import transaction

def update_urls():
    print("🚀 Démarrage mise à jour des URLs en base de données")
    
    # 1. Documents
    print("\n📄 Mise à jour Documents...")
    documents = Document.objects.all()
    count = 0
    with transaction.atomic():
        for doc in documents:
            if doc.file and not doc.metadata.get('s3_migrated'):
                # Logique simple: S3 stocke avec le même path relatif souvent
                # Mais B2 URLs sont différentes.
                # Ici on suppose que le FileField stocke le chemin relatif (ex: documents/2026/02/file.pdf)
                # Si on change le storage backend, Django utilisera ce chemin avec le nouveau domain.
                # Donc souvent, on n'a rien à changer SI le chemin relatif est conservé.
                
                # Vérification : Est-ce que les données actuelles sont des URLs complètes ou des chemins relatifs ?
                # Django FileField stocke généralement le chemin relatif.
                
                print(f"   Vérification: {doc.file.name}")
                # doc.metadata['s3_migrated'] = True
                # doc.save()
                count += 1
    print(f"   ✅ {count} documents vérifiés.")

    # 2. Signatures Contracts
    print("\n✍️  Mise à jour Contrats...")
    contracts = InterpreterContractSignature.objects.all()
    # (Logique similaire selon comment les données sont stockées)

    print("\n⚠️ NOTE: Django FileField stocke généralement des chemins relatifs.")
    print("   Si vous changez `DEFAULT_FILE_STORAGE` pour S3Boto3Storage,")
    print("   Django générera automatiquement les nouvelles URLs S3 basées sur ces chemins.")
    print("   Ce script est utile seulement si vous avez stocké des URLs absolues en dur (CharField).")

if __name__ == "__main__":
    update_urls()
