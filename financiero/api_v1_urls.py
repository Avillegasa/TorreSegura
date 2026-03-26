from django.urls import path
from . import api

urlpatterns = [
    path("cuotas/pendientes/", api.mis_cuotas_pendientes, name="api-cuotas-pendientes"),
    path("cuotas/pagadas/", api.mis_cuotas_pagadas, name="api-cuotas-pagadas"),
    path("pagos/", api.mis_pagos, name="api-mis-pagos"),
    path("pagos/registrar/", api.registrar_pago, name="api-registrar-pago"),

    # QR BNB
    path("pagos/qr/generar/", api.generar_qr_pago, name="api-generar-qr"),
    path("pagos/qr/<str:qr_id>/verificar/", api.verificar_qr_pago, name="api-verificar-qr"),
    path("pagos/qr/pendientes/", api.mis_qr_pendientes, name="api-qr-pendientes"),
]
