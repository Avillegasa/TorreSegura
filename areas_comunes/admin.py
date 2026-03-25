from django.contrib import admin
from .models import AreaComun, Reserva


@admin.register(AreaComun)
class AreaComunAdmin(admin.ModelAdmin):
    list_display = ["nombre", "edificio", "capacidad_maxima", "horario_inicio", "horario_fin", "activo"]
    list_filter = ["edificio", "activo"]
    search_fields = ["nombre", "descripcion"]
    list_editable = ["activo"]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["area_comun", "residente", "fecha", "hora_inicio", "hora_fin", "estado"]
    list_filter = ["estado", "area_comun", "fecha"]
    search_fields = ["area_comun__nombre", "residente__usuario__username"]
    list_editable = ["estado"]
