from django.urls import path

from .views import (
    AlertaViewSet,
    actualizar_estado_alerta,
    alertas_nuevas,
    crear_alerta,
    mis_alertas,
)

# Rutas explícitas para evitar prefijos raros y evitar depender del router
alerta_list = AlertaViewSet.as_view({"get": "list", "post": "create"})
alerta_detail = AlertaViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    # Custom helpers
    path("crear/", crear_alerta, name="api_v1_alerta_crear"),
    path("mis/", mis_alertas, name="api_v1_alerta_mis"),
    path("nuevas/", alertas_nuevas, name="api_v1_alerta_nuevas"),
    path("<int:pk>/estado/", actualizar_estado_alerta, name="api_v1_alerta_estado"),

    # CRUD estándar
    path("", alerta_list, name="api_v1_alerta_list"),
    path("<int:pk>/", alerta_detail, name="api_v1_alerta_detail"),
]
