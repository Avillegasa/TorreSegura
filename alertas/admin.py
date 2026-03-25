from django.contrib import admin
from .models import Alerta, Anuncio, OpcionVoto, Voto


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'descripcion', 'enviado_por', 'fecha')
    list_filter = ('tipo', 'fecha')


class OpcionVotoInline(admin.TabularInline):
    model = OpcionVoto
    extra = 0


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'categoria', 'autor', 'edificio', 'es_votacion', 'fijado', 'activo', 'fecha_creacion')
    list_filter = ('categoria', 'edificio', 'es_votacion', 'fijado', 'activo')
    search_fields = ('titulo', 'contenido')
    inlines = [OpcionVotoInline]


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'opcion', 'fecha')
    list_filter = ('fecha',)
