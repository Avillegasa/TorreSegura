from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views_api import CustomTokenObtainPairView, usuario_actual
from . import views

urlpatterns = [
    # JWT
    path("token/", CustomTokenObtainPairView.as_view(), name="api_v1_token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="api_v1_token_refresh"),
    path("me/", usuario_actual, name="api_v1_usuario_actual"),

    # Clientes potenciales (útil si el móvil también registra leads)
    path("clientes-potenciales/", views.api_clientes_potenciales, name="api_v1_clientes_potenciales"),
    path(
        "clientes-potenciales/crear/",
        views.crear_cliente_potencial,
        name="api_v1_crear_cliente_potencial",
    ),
    path(
        "clientes-potenciales/crear-simple/",
        views.crear_cliente_potencial_simple,
        name="api_v1_crear_cliente_potencial_simple",
    ),
    path(
        "clientes-potenciales/estadisticas/",
        views.estadisticas_clientes_potenciales,
        name="api_v1_estadisticas_clientes_potenciales",
    ),
]
