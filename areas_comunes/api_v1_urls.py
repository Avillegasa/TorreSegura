from django.urls import path
from . import api

urlpatterns = [
    path("", api.listar_areas, name="api_v1_listar_areas"),
    path("<int:area_id>/reservar/", api.crear_reserva, name="api_v1_crear_reserva"),
    path("<int:area_id>/reservas/", api.listar_reservas_area, name="api_v1_reservas_area"),
    path("mis-reservas/", api.mis_reservas, name="api_v1_mis_reservas"),
    path("reservas/<int:reserva_id>/cancelar/", api.cancelar_reserva, name="api_v1_cancelar_reserva"),
]
