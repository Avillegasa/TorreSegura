from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from . import views
from usuarios.views import CustomLoginView

def health_check(request):
    """Endpoint básico para verificar que la app funciona"""
    return JsonResponse({'status': 'ok', 'message': 'Django app is running!'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('', views.home, name='home'),
     
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
    
    # URLs de autenticación
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='password_change.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'), name='password_change_done'),
    path('cambiar-password-obligatorio/', views.forzar_cambio_password, name='forzar_cambio_password'),
    
    # ✅ API limpia para móvil (JWT/JSON)
    path('api/v1/', include('condominio_app.api_v1_urls')),

    # URLs para el restablecimiento de contraseña
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    
    # Incluir URLs de las aplicaciones
    path('usuarios/', include('usuarios.urls')),
    path('viviendas/', include('viviendas.urls')),
    path('accesos/', include('accesos.urls')),
    path('personal/', include('personal.urls')),
    path('alertas/', include('alertas.urls')),  # Vistas HTML (dashboard)
    path('areas-comunes/', include('areas_comunes.urls')),
    path('financiero/', include('financiero.urls')),
    path('reportes/', include('reportes.urls')),
    
    # OAuth URLs
    path('accounts/', include('allauth.urls')),

]

# Archivos estáticos/media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Manejadores de errores
handler404 = 'condominio_app.views.handler404'
handler500 = 'condominio_app.views.handler500'