from django.urls import path
from . import views
from . import api
from .api_views import api_visitas_historial 
urlpatterns = [
    # URLs para Visita
    path('visitas/', views.VisitaListView.as_view(), name='visita-list'),
    path('visitas/nueva/', views.VisitaCreateView.as_view(), name='visita-create'),
    path('visitas/<int:pk>/', views.VisitaDetailView.as_view(), name='visita-detail'),
    path('visitas/<int:pk>/salida/', views.registrar_salida_visita, name='visita-salida'),
    
    # URLs para Movimiento de Residentes
    path('movimientos/', views.MovimientoResidenteListView.as_view(), name='movimiento-list'),
    path('movimientos/<int:pk>/', views.MovimientoResidenteDetailView.as_view(), name='movimiento-detail'),
    path('movimientos/entrada/', views.MovimientoResidenteEntradaView.as_view(), name='movimiento-entrada'),
    path('movimientos/salida/', views.MovimientoResidenteSalidaView.as_view(), name='movimiento-salida'),
    
    # API URLs
    path('api/visitas/historial/', api.historial_visitas, name='api-visitas-historial'),
    path('api/viviendas/<int:vivienda_id>/residentes/', api.residentes_por_vivienda, name='api-residentes-vivienda'),
    # API endpoints
    path('api/visitas-historial/', api_visitas_historial, name='api-visitas-historial'),
    # API MOVILES
    path('api/visitas/<int:visita_id>/qr/', api.generar_qr_visita, name='api-generar-qr-visita'),
    path('api/visitas/crear/', api.crear_visita, name='api-crear-visita'),
    path('api/visitas/verificar_qr/', api.verificar_qr_visita, name='verificar-qr-visita'),

]