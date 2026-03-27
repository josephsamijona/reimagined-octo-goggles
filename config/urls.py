from django.contrib import admin
from django.urls import path, include

handler404 = 'app.views.errors.error_404'
handler500 = 'app.views.errors.error_500'
handler403 = 'app.views.errors.error_403'
handler400 = 'app.views.errors.error_400'

urlpatterns = [
    path("admin/mfa/", include('app.admin.mfa_urls')),
    path("admin/", admin.site.urls),
    path('api/v1/', include('app.api.urls')),
    path('', include('app.urls')),  # Inclure les URLs de l'application app
]