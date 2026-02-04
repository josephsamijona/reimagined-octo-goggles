# Déploiement Lambda pour Migration B2 → S3

## Prérequis
- Compte AWS avec accès à Lambda et S3
- AWS CLI configuré

## Étapes de Déploiement

### 1. Créer le package ZIP

```bash
# Dans le dossier scripts/lambda/
pip install boto3 -t ./package/
cp migrate_b2_to_s3_lambda.py ./package/
cd package
zip -r ../migration_lambda.zip .
```

### 2. Créer la Fonction Lambda (Console AWS)

1. Aller sur AWS Lambda Console
2. Créer une nouvelle fonction:
   - **Nom**: `jhbridge-b2-s3-migration`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - **Mémoire**: 512 MB
   - **Timeout**: 15 minutes

3. Uploader le fichier `migration_lambda.zip`

### 3. Configurer les Variables d'Environnement

| Variable | Valeur |
|----------|--------|
| `B2_ENDPOINT_URL` | `https://s3.us-west-004.backblazeb2.com` |
| `B2_ACCESS_KEY_ID` | Votre clé B2 |
| `B2_SECRET_ACCESS_KEY` | Votre secret B2 |
| `B2_BUCKET_NAME` | `jhbridgestockagesystem` |
| `S3_TARGET_BUCKET` | `jhbridge-documents-prod` |

### 4. Configurer le Rôle IAM

Attacher la policy suivante au rôle Lambda:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:HeadObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::jhbridge-documents-prod",
                "arn:aws:s3:::jhbridge-documents-prod/*",
                "arn:aws:s3:::jhbridge-contracts-prod",
                "arn:aws:s3:::jhbridge-contracts-prod/*"
            ]
        }
    ]
}
```

### 5. Tester la Migration

**Test Dry-Run (sans migration réelle):**
```json
{
    "filter_docs_only": true,
    "dry_run": true
}
```

**Migration réelle:**
```json
{
    "filter_docs_only": true,
    "dry_run": false
}
```

### 6. Avantages de cette Approche

- ✅ Bande passante AWS (très rapide)
- ✅ Pas de dépendance à votre PC
- ✅ Reprise automatique en cas d'erreur
- ✅ Logs CloudWatch pour monitoring
