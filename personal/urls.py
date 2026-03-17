# personal/urls.py - REEMPLAZA TODO EL CONTENIDO
from django.urls import path
from . import views

urlpatterns = [
    # Vistas de puestos
    path('puestos/', views.PuestoListView.as_view(), name='puesto-list'),
    path('puestos/crear/', views.PuestoCreateView.as_view(), name='puesto-create'),
    path('puestos/<int:pk>/editar/', views.PuestoUpdateView.as_view(), name='puesto-update'),
    path('puestos/<int:pk>/eliminar/', views.PuestoDeleteView.as_view(), name='puesto-delete'),
    
    # Vistas de empleados
    path('empleados/', views.EmpleadoListView.as_view(), name='empleado-list'),
    path('empleados/crear/', views.EmpleadoCreateView.as_view(), name='empleado-create'),
    # ✅ NUEVA URL: Para que Gerentes creen personal desde cero
    path('personal/crear/', views.PersonalCreateView.as_view(), name='personal-create'),
    path('empleados/<int:pk>/', views.EmpleadoDetailView.as_view(), name='empleado-detail'),
    path('empleados/<int:pk>/editar/', views.EmpleadoUpdateView.as_view(), name='empleado-update'),
    path('empleados/<int:pk>/estado/', views.empleado_change_state, name='empleado-change-state'),
    
    # Vistas de asignaciones
    path('asignaciones/', views.AsignacionListView.as_view(), name='asignacion-list'),
    path('asignaciones/crear/', views.AsignacionCreateView.as_view(), name='asignacion-create'),
    path('asignaciones/<int:pk>/', views.AsignacionDetailView.as_view(), name='asignacion-detail'),
    path('asignaciones/<int:pk>/editar/', views.AsignacionUpdateView.as_view(), name='asignacion-update'),
    path('asignaciones/<int:pk>/estado/', views.cambiar_estado_asignacion, name='cambiar-estado-asignacion'),
    
    # API endpoints
    path('api/viviendas-por-edificio/', views.viviendas_por_edificio_api, name='api-viviendas-por-edificio'),
]