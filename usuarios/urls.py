# usuarios/urls.py — rutas web (session auth)
from django.urls import path
from . import views
from .views import (
    UsuarioListView, UsuarioCreateView, UsuarioUpdateView,
    UsuarioDetailView, UsuarioChangeStateView,
    RolListView, RolCreateView, RolUpdateView, RolDeleteView,
    CustomLoginView, VerificarEmailView,
    ClientePotencialListView,
)

urlpatterns = [
    # URLs para Usuario
    path('', views.UsuarioListView.as_view(), name='usuario-list'),
    path('nuevo/', views.UsuarioCreateView.as_view(), name='usuario-create'),
    path('<int:pk>/', views.UsuarioDetailView.as_view(), name='usuario-detail'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario-update'),
    path('<int:pk>/estado/', views.UsuarioChangeStateView.as_view(), name='usuario-change-state'),
    path('credenciales/', views.usuario_credenciales, name='usuario-credenciales'),

    # URLs para Rol
    path('roles/', views.RolListView.as_view(), name='rol-list'),
    path('roles/nuevo/', views.RolCreateView.as_view(), name='rol-create'),
    path('roles/<int:pk>/editar/', views.RolUpdateView.as_view(), name='rol-update'),
    path('roles/<int:pk>/eliminar/', views.RolDeleteView.as_view(), name='rol-delete'),

    # AJAX
    path('ajax/cargar-viviendas/', views.cargar_viviendas, name='ajax-cargar-viviendas'),

    # Clientes potenciales (vista web)
    path('clientes-potenciales/', ClientePotencialListView.as_view(), name='clientes-potenciales-list'),

    # Verificación email
    path('verificar-email/<uidb64>/<token>/', views.VerificarEmailView.as_view(), name='verificar-email'),
]
