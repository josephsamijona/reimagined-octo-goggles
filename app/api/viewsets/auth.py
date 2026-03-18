"""Authentication views: login, token refresh, current user profile."""
import logging

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from app.models import User

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """
    POST /auth/login/
    Accepts email + password, returns JWT access/refresh tokens and user info.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Django's authenticate uses USERNAME_FIELD which is 'email' on this custom User
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'detail': 'Account is disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Build user payload
        user_data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active,
        }

        # Update last login IP
        ip = self._get_client_ip(request)
        if ip:
            User.objects.filter(pk=user.pk).update(last_login_ip=ip)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data,
        })

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """
    POST /auth/token/refresh/
    Wraps SimpleJWT TokenRefreshView.  Accepts { refresh } and returns { access }.
    """
    pass


class MeView(APIView):
    """
    GET /auth/me/
    Returns the currently authenticated user's profile information.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'phone': user.phone,
            'is_active': user.is_active,
            'registration_complete': user.registration_complete,
            'is_dashboard_enabled': user.is_dashboard_enabled,
            'created_at': user.created_at,
        }

        # Append role-specific profile data
        if user.role == 'CLIENT' and hasattr(user, 'client_profile'):
            client = user.client_profile
            data['profile'] = {
                'id': client.id,
                'company_name': client.company_name,
                'city': client.city,
                'state': client.state,
                'active': client.active,
            }
        elif user.role == 'INTERPRETER' and hasattr(user, 'interpreter_profile'):
            interp = user.interpreter_profile
            data['profile'] = {
                'id': interp.id,
                'city': interp.city,
                'state': interp.state,
                'active': interp.active,
                'is_manually_blocked': interp.is_manually_blocked,
                'has_accepted_contract': interp.has_accepted_contract,
                'background_check_status': interp.background_check_status,
                'w9_on_file': interp.w9_on_file,
            }

        return Response(data)
