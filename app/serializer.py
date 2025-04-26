from rest_framework import serializers
from .models import InterpreterContractSignature

class InterpreterContractSignatureSerializer(serializers.ModelSerializer):
    # Champs pour les données sensibles (write-only)
    account_number = serializers.CharField(write_only=True, required=False)
    routing_number = serializers.CharField(write_only=True, required=False)
    swift_code = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = InterpreterContractSignature
        fields = [
            'id', 'user', 'interpreter_name', 'interpreter_email', 'interpreter_phone',
            'interpreter_address', 'bank_name', 'account_type', 'account_number',
            'routing_number', 'swift_code', 'contract_document', 'contract_version',
            'signature_type', 'signature_image', 'signature_typography_text',
            'signature_manual_data', 'signed_at', 'ip_address', 'signature_hash',
            'company_representative_name', 'company_representative_signature',
            'company_signed_at', 'is_fully_signed', 'is_active'
        ]
        read_only_fields = ['id', 'signature_hash', 'signed_at']
    
    def create(self, validated_data):
        # Extraction des données sensibles à chiffrer
        account_number = validated_data.pop('account_number', None)
        routing_number = validated_data.pop('routing_number', None)
        swift_code = validated_data.pop('swift_code', None)
        
        # Création de l'instance
        instance = InterpreterContractSignature.objects.create(**validated_data)
        
        # Définition des champs chiffrés
        if account_number:
            instance.set_account_number(account_number)
        if routing_number:
            instance.set_routing_number(routing_number)
        if swift_code:
            instance.set_swift_code(swift_code)
            
        instance.save()
        return instance
    
    def update(self, instance, validated_data):
        # Extraction des données sensibles à chiffrer
        account_number = validated_data.pop('account_number', None)
        routing_number = validated_data.pop('routing_number', None)
        swift_code = validated_data.pop('swift_code', None)
        
        # Mise à jour des autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Mise à jour des champs chiffrés
        if account_number:
            instance.set_account_number(account_number)
        if routing_number:
            instance.set_routing_number(routing_number)
        if swift_code:
            instance.set_swift_code(swift_code)
            
        instance.save()
        return instance