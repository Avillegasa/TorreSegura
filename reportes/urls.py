from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReporteListView.as_view(), name='reporte-list'),
    path('nuevo/', views.ReporteCreateView.as_view(), name='reporte-create'),
    path('<int:pk>/editar/', views.ReporteUpdateView.as_view(), name='reporte-update'),
    path('<int:pk>/eliminar/', views.ReporteDeleteView.as_view(), name='reporte-delete'),

    # FALTANTES:
    path('<int:pk>/preview/', views.reporte_preview, name='reporte-preview'),
    path('<int:pk>/favorito/', views.reporte_toggle_favorito, name='reporte-toggle-favorito'),
    path('<int:pk>/duplicar/', views.reporte_duplicar, name='reporte-duplicar'),
    path('<int:pk>/pdf/', views.reporte_pdf, name='reporte-pdf'),
    path('<int:pk>/reactivar/', views.reporte_reactivar, name='reporte-reactivar'),
    path('<int:pk>/descargar/', views.reporte_descargar, name='reporte-descargar'),
]