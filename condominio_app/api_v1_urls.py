from django.urls import include, path

from rest_framework.routers import DefaultRouter

from accesos.api_v1_visitantes import VisitanteViewSet

router = DefaultRouter()
router.register(r"visitantes", VisitanteViewSet, basename="visitantes")

urlpatterns = [
    # Auth/JWT + endpoints de usuario para móvil
    path("auth/", include("usuarios.api_v1_urls")),

    # Alertas (DRF, JWT)
    path("alertas/", include("alertas.api_v1_urls")),

    # Visitas/Accesos (solo los endpoints DRF/JWT)
    path("accesos/", include("accesos.api_v1_urls")),

    # Areas comunes y reservas
    path("areas-comunes/", include("areas_comunes.api_v1_urls")),

    # Financiero (cuotas y pagos para app movil)
    path("financiero/", include("financiero.api_v1_urls")),

    # Visitantes (gestión móvil)
    path("", include(router.urls)),
]
