from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para el ViewSet
router = DefaultRouter()
router.register(r'alertas', views.AlertaViewSet)

urlpatterns = [
    # Rutas específicas PRIMERO (antes del router)
    path('api/alertas/crear/', views.crear_alerta, name='crear_alerta_custom'),
    path('api/alertas/mis-alertas/', views.mis_alertas, name='mis_alertas'),
    path('api/alertas/<int:pk>/estado/', views.actualizar_estado_alerta, name='actualizar_estado_alerta'),
    
    # Nueva ruta para cambio de estado desde web
    path('web/alertas/<int:pk>/estado/', views.cambiar_estado_web, name='cambiar_estado_web'),

    # Polling de alertas nuevas (web)
    path('web/alertas/nuevas/', views.alertas_nuevas_web, name='alertas_nuevas_web'),
    
    # Router al final
    path('api/', include(router.urls)),
    
    # Rutas HTML
    path('lista/', views.lista_alertas, name='lista_alertas'),
]