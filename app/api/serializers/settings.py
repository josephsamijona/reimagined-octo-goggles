"""Serializers for settings endpoints: APIKey and CompanyInfo."""
import secrets

from django.conf import settings
from rest_framework import serializers

from app.models import APIKey


# ---------------------------------------------------------------------------
# APIKey
# ---------------------------------------------------------------------------

class APIKeySerializer(serializers.ModelSerializer):
    """Read serializer — key is masked."""
    key_preview = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = (
            'id', 'name', 'app_name', 'key_preview',
            'is_active', 'is_valid', 'created_at', 'expires_at', 'last_used',
        )
        read_only_fields = fields

    def get_key_preview(self, obj):
        return obj.key[:8] + '...' if obj.key else ''

    def get_is_valid(self, obj):
        return obj.is_valid()


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Write serializer — returns full key once on creation."""
    key = serializers.CharField(read_only=True)

    class Meta:
        model = APIKey
        fields = ('id', 'name', 'app_name', 'expires_at', 'key')
        read_only_fields = ('id', 'key')

    def create(self, validated_data):
        validated_data['key'] = secrets.token_hex(32)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Company Info (read-only from Django settings)
# ---------------------------------------------------------------------------

class CompanyInfoSerializer(serializers.Serializer):
    site_url = serializers.CharField()
    app_name = serializers.CharField()
    environment = serializers.CharField()
    debug = serializers.BooleanField()

    def to_representation(self, instance):
        return {
            'site_url': getattr(settings, 'SITE_URL', ''),
            'app_name': 'JHBridge Translation',
            'environment': getattr(settings, 'RAILWAY_ENVIRONMENT', 'development'),
            'debug': getattr(settings, 'DEBUG', False),
        }
