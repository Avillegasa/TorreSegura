from django.urls import path
from . import views

urlpatterns = [
    # Areas Comunes
    path("", views.AreaComunListView.as_view(), name="area-comun-list"),
    path("crear/", views.AreaComunCreateView.as_view(), name="area-comun-create"),
    path("<int:pk>/", views.AreaComunDetailView.as_view(), name="area-comun-detail"),
    path("<int:pk>/editar/", views.AreaComunUpdateView.as_view(), name="area-comun-update"),
    path("<int:pk>/eliminar/", views.AreaComunDeleteView.as_view(), name="area-comun-delete"),
    # Reservas
    path("reservas/", views.ReservaListView.as_view(), name="reserva-list"),
    path("reservas/<int:pk>/eliminar/", views.ReservaDeleteView.as_view(), name="reserva-delete"),
]
