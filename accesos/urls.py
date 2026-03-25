from django.urls import path
from . import views
from . import api

urlpatterns = [
    # URLs web para Visita
    path('visitas/', views.VisitaListView.as_view(), name='visita-list'),
    path('visitas/nueva/', views.VisitaCreateView.as_view(), name='visita-create'),
    path('visitas/<int:pk>/', views.VisitaDetailView.as_view(), name='visita-detail'),
    path('visitas/<int:pk>/salida/', views.registrar_salida_visita, name='visita-salida'),

    # URLs web para Movimiento de Residentes
    path('movimientos/', views.MovimientoResidenteListView.as_view(), name='movimiento-list'),
    path('movimientos/<int:pk>/', views.MovimientoResidenteDetailView.as_view(), name='movimiento-detail'),
    path('movimientos/entrada/', views.MovimientoResidenteEntradaView.as_view(), name='movimiento-entrada'),
    path('movimientos/salida/', views.MovimientoResidenteSalidaView.as_view(), name='movimiento-salida'),

    # API web (session auth) — historial y residentes por vivienda
    path('api/visitas/historial/', api.historial_visitas, name='api-visitas-historial'),
    path('api/viviendas/<int:vivienda_id>/residentes/', api.residentes_por_vivienda, name='api-residentes-vivienda'),
    path('api/visitas/<int:visita_id>/qr/', api.generar_qr_visita, name='api-generar-qr-visita'),
]