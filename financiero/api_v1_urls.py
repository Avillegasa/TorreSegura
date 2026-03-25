from django.urls import path
from . import api

urlpatterns = [
    path("cuotas/pendientes/", api.mis_cuotas_pendientes, name="api-cuotas-pendientes"),
    path("cuotas/pagadas/", api.mis_cuotas_pagadas, name="api-cuotas-pagadas"),
    path("pagos/", api.mis_pagos, name="api-mis-pagos"),
    path("pagos/registrar/", api.registrar_pago, name="api-registrar-pago"),
]
