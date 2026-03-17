from django.urls import path

from . import api

urlpatterns = [
    # Endpoints DRF/JWT existentes (mobile-ready)
    path("visitas/crear/", api.crear_visita, name="api_v1_crear_visita"),
    path("visitas/verificar-qr/", api.verificar_qr_visita, name="api_v1_verificar_qr_visita"),
]
