from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Financiero - DEBE IR PRIMERO
    path('', views.dashboard_financiero, name='dashboard-financiero'),

    # APIs para actualización asíncrona
    path('api/cuotas-por-vivienda/<int:vivienda_id>/', views.api_cuotas_por_vivienda, name='api-cuotas-por-vivienda'),
    path('api/resumen-financiero/', views.api_resumen_financiero, name='api-resumen-financiero'),
    path('api/datos-chart/', views.dashboard_financiero_api, name='dashboard-financiero-api'),
    
    # ConceptoCuota URLS
    path('conceptos/', views.ConceptoCuotaListView.as_view(), name='concepto-list'),
    path('conceptos/crear/', views.ConceptoCuotaCreateView.as_view(), name='concepto-create'),
    path('conceptos/<int:pk>/', views.ConceptoCuotaDetailView.as_view(), name='concepto-detail'),
    path('conceptos/<int:pk>/editar/', views.ConceptoCuotaUpdateView.as_view(), name='concepto-update'),
    path('conceptos/<int:pk>/eliminar/', views.ConceptoCuotaDeleteView.as_view(), name='concepto-delete'),
    
    # Cuota URLS
    path('cuotas/', views.CuotaListView.as_view(), name='cuota-list'),
    path('cuotas/crear/', views.CuotaCreateView.as_view(), name='cuota-create'),
    path('cuotas/<int:pk>/', views.CuotaDetailView.as_view(), name='cuota-detail'),
    path('cuotas/<int:pk>/editar/', views.CuotaUpdateView.as_view(), name='cuota-update'),
    path('cuotas/generar/', views.generar_cuotas, name='cuota-generar'),
    
    # Pago URLS
    path('pagos/', views.PagoListView.as_view(), name='pago-list'),
    path('pagos/crear/', views.PagoCreateView.as_view(), name='pago-create'),
    path('pagos/<int:pk>/', views.PagoDetailView.as_view(), name='pago-detail'),
    path('pagos/<int:pk>/editar/', views.PagoUpdateView.as_view(), name='pago-update'),
    path('pagos/<int:pk>/verificar/', views.verificar_pago, name='pago-verificar'),
    path('pagos/<int:pk>/rechazar/', views.rechazar_pago, name='pago-rechazar'),
    
    # CategoriaGasto URLS
    path('categorias-gasto/', views.CategoriaGastoListView.as_view(), name='categoria-gasto-list'),
    path('categorias-gasto/crear/', views.CategoriaGastoCreateView.as_view(), name='categoria-gasto-create'),
    path('categorias-gasto/<int:pk>/', views.CategoriaGastoDetailView.as_view(), name='categoria-gasto-detail'),
    path('categorias-gasto/<int:pk>/editar/', views.CategoriaGastoUpdateView.as_view(), name='categoria-gasto-update'),
    path('categorias-gasto/<int:pk>/eliminar/', views.CategoriaGastoDeleteView.as_view(), name='categoria-gasto-delete'),
    
    # Gasto URLS
    path('gastos/', views.GastoListView.as_view(), name='gasto-list'),
    path('gastos/crear/', views.GastoCreateView.as_view(), name='gasto-create'),
    path('gastos/<int:pk>/', views.GastoDetailView.as_view(), name='gasto-detail'),
    path('gastos/<int:pk>/editar/', views.GastoUpdateView.as_view(), name='gasto-update'),
    path('gastos/<int:pk>/marcar-pagado/', views.marcar_gasto_pagado, name='gasto-marcar-pagado'),
    path('gastos/<int:pk>/cancelar/', views.cancelar_gasto, name='gasto-cancelar'),
    
    # EstadoCuenta URLS
    path('estados-cuenta/', views.EstadoCuentaListView.as_view(), name='estado-cuenta-list'),
    path('estados-cuenta/crear/', views.EstadoCuentaCreateView.as_view(), name='estado-cuenta-create'),
    path('estados-cuenta/<int:pk>/', views.EstadoCuentaDetailView.as_view(), name='estado-cuenta-detail'),
    path('estados-cuenta/<int:pk>/pdf/', views.estado_cuenta_pdf, name='estado-cuenta-pdf'),
    path('estados-cuenta/<int:pk>/enviar/', views.enviar_estado_cuenta, name='estado-cuenta-enviar'),
    path('estados-cuenta/generar-masivos/', views.generar_estados_cuenta, name='estado-cuenta-generar-masivos'),
    
    
]