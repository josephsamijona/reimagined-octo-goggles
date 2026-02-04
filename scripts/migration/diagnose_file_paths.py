import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.models import (
    Document, InterpreterContractSignature, SignedDocument,
    ClientPayment, InterpreterPayment, Expense, Reimbursement,
    Interpreter
)
from django.db.models import Q

def diagnose_file_paths():
    """
    Diagnostic des chemins de fichiers en base de données.
    Vérifie la structure actuelle pour déterminer si une migration est nécessaire.
    """
    print("=" * 80)
    print("🔍 DIAGNOSTIC DES CHEMINS DE FICHIERS EN BASE DE DONNÉES")
    print("=" * 80)
    
    issues = []
    
    # 1. Documents
    print("\n📄 Documents (app_document)")
    print("-" * 80)
    docs = Document.objects.filter(file__isnull=False)[:10]
    if docs.exists():
        for doc in docs:
            path = doc.file.name
            print(f"   ID: {doc.id}")
            print(f"   Path: {path}")
            
            # Vérifications
            if path.startswith('http://') or path.startswith('https://'):
                issues.append(f"Document {doc.id}: URL absolue détectée → {path}")
                print(f"   ⚠️  URL ABSOLUE (doit être converti en chemin relatif)")
            elif path.startswith('media/'):
                print(f"   ℹ️  Préfixe 'media/' présent (vérifier si double préfixe)")
            else:
                print(f"   ✅ Chemin relatif standard")
            print()
    else:
        print("   Aucun document avec fichier trouvé.")
    
    # 2. Signatures de Contrats
    print("\n✍️  Signatures de Contrats (app_interpretercontractsignature)")
    print("-" * 80)
    contracts = InterpreterContractSignature.objects.filter(
        Q(signature_image__isnull=False) | Q(contract_document__isnull=False)
    )[:10]
    
    if contracts.exists():
        for contract in contracts:
            if contract.signature_image:
                path = contract.signature_image.name
                print(f"   ID: {contract.id} (signature_image)")
                print(f"   Path: {path}")
                
                if path.startswith('http://') or path.startswith('https://'):
                    issues.append(f"Contract {contract.id}: URL absolue dans signature_image")
                    print(f"   ⚠️  URL ABSOLUE")
                elif path.startswith('media/'):
                    print(f"   ℹ️  Préfixe 'media/' présent")
                else:
                    print(f"   ✅ Chemin relatif")
                print()
            
            if contract.contract_document:
                path = contract.contract_document.name
                print(f"   ID: {contract.id} (contract_document)")
                print(f"   Path: {path}")
                
                if path.startswith('http://') or path.startswith('https://'):
                    issues.append(f"Contract {contract.id}: URL absolue dans contract_document")
                    print(f"   ⚠️  URL ABSOLUE")
                elif path.startswith('media/'):
                    print(f"   ℹ️  Préfixe 'media/' présent")
                else:
                    print(f"   ✅ Chemin relatif")
                print()
    else:
        print("   Aucun contrat avec fichier trouvé.")
    
    # 3. Paiements Clients
    print("\n💰 Paiements Clients (app_clientpayment)")
    print("-" * 80)
    payments = ClientPayment.objects.filter(payment_proof__isnull=False)[:5]
    if payments.exists():
        for payment in payments:
            path = payment.payment_proof.name
            print(f"   ID: {payment.id}")
            print(f"   Path: {path}")
            
            if path.startswith('http://') or path.startswith('https://'):
                issues.append(f"ClientPayment {payment.id}: URL absolue")
                print(f"   ⚠️  URL ABSOLUE")
            elif path.startswith('media/'):
                print(f"   ℹ️  Préfixe 'media/' présent")
            else:
                print(f"   ✅ Chemin relatif")
            print()
    else:
        print("   Aucun paiement avec preuve trouvé.")
    
    # 4. Profils Interprètes
    print("\n👤 Profils Interprètes (app_interpreter)")
    print("-" * 80)
    interpreters = Interpreter.objects.filter(profile_image__isnull=False)[:5]
    if interpreters.exists():
        for interp in interpreters:
            path = interp.profile_image.name
            print(f"   ID: {interp.id}")
            print(f"   Path: {path}")
            
            if path.startswith('http://') or path.startswith('https://'):
                issues.append(f"Interpreter {interp.id}: URL absolue")
                print(f"   ⚠️  URL ABSOLUE")
            elif path.startswith('media/'):
                print(f"   ℹ️  Préfixe 'media/' présent")
            else:
                print(f"   ✅ Chemin relatif")
            print()
    else:
        print("   Aucun interprète avec image de profil trouvé.")
    
    # Résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 80)
    
    if issues:
        print(f"\n⚠️  {len(issues)} PROBLÈME(S) DÉTECTÉ(S):\n")
        for issue in issues:
            print(f"   - {issue}")
        print("\n🔧 ACTION REQUISE: Exécuter le script de migration pour corriger ces chemins.")
    else:
        print("\n✅ Aucun problème critique détecté.")
        print("   Les chemins semblent être des chemins relatifs standards.")
        print("\n💡 RECOMMANDATION:")
        print("   - Vérifier que `custom_storages.MediaStorage` a `location='media'`")
        print("   - Tester l'accès à un fichier via `.url` pour confirmer le bon fonctionnement")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose_file_paths()
