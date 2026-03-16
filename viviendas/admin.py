# viviendas/admin.py - Configuración del admin de Django para viviendas
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Edificio, Vivienda, Residente

@admin.register(Edificio)
class EdificioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'direccion', 'pisos', 'total_viviendas', 'porcentaje_ocupacion', 'fecha_construccion']
    list_filter = ['pisos', 'fecha_construccion']
    search_fields = ['nombre', 'direccion']
    ordering = ['nombre']
    
    def total_viviendas(self, obj):
        return obj.get_total_viviendas()
    total_viviendas.short_description = 'Total Viviendas'
    
    def porcentaje_ocupacion(self, obj):
        porcentaje = obj.get_porcentaje_ocupacion()
        color = 'green' if porcentaje > 80 else 'orange' if porcentaje > 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, porcentaje
        )
    porcentaje_ocupacion.short_description = 'Ocupación'

@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'edificio', 'piso', 'estado', 'activo', 'metros_cuadrados', 'residentes_count', 'link_to_residentes']
    list_filter = ['edificio', 'estado', 'activo', 'piso', 'habitaciones']
    search_fields = ['numero', 'edificio__nombre']
    ordering = ['edificio__nombre', 'piso', 'numero']
    list_editable = ['estado']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('edificio', 'numero', 'piso')
        }),
        ('Características', {
            'fields': ('metros_cuadrados', 'habitaciones', 'baños')
        }),
        ('Estado', {
            'fields': ('estado', 'activo')
        }),
        ('Información de Baja', {
            'fields': ('fecha_baja', 'motivo_baja'),
            'classes': ('collapse',),
            'description': 'Solo se completa cuando la vivienda se da de baja'
        }),
    )
    
    def residentes_count(self, obj):
        count = obj.get_residentes_activos().count()
        if count == 0:
            return '0'
        return format_html('<strong>{}</strong>', count)
    residentes_count.short_description = 'Residentes Activos'
    
    def link_to_residentes(self, obj):
        count = obj.residentes.count()
        if count == 0:
            return 'Sin residentes'
        
        url = reverse('admin:viviendas_residente_changelist')
        return format_html(
            '<a href="{}?vivienda__id__exact={}">Ver {} residente{}</a>',
            url, obj.pk, count, 's' if count != 1 else ''
        )
    link_to_residentes.short_description = 'Residentes'
    
    def save_model(self, request, obj, form, change):
        """Personalizar el guardado desde el admin"""
        if not change:  # Nuevo objeto
            obj.save()
        else:  # Editando objeto existente
            # Verificar cambios importantes
            if 'estado' in form.changed_data:
                # Log del cambio de estado
                pass
            obj.save()

@admin.register(Residente)
class ResidenteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'vivienda', 'tipo_residente', 'activo', 'fecha_ingreso', 'vehiculos']
    list_filter = ['activo', 'es_propietario', 'vivienda__edificio', 'fecha_ingreso']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'usuario__email', 'vivienda__numero']
    ordering = ['vivienda__edificio__nombre', 'vivienda__numero', 'usuario__last_name']
    list_editable = ['activo']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Vivienda', {
            'fields': ('vivienda', 'es_propietario')
        }),
        ('Información Adicional', {
            'fields': ('vehiculos', 'activo', 'fecha_ingreso')
        }),
    )
    
    def nombre_completo(self, obj):
        return obj.nombre_completo
    nombre_completo.short_description = 'Nombre'
    nombre_completo.admin_order_field = 'usuario__last_name'
    
    def tipo_residente(self, obj):
        tipo = obj.tipo_residente
        color = 'blue' if obj.es_propietario else 'green'
        return format_html('<span style="color: {};">{}</span>', color, tipo)
    tipo_residente.short_description = 'Tipo'
    
    def save_model(self, request, obj, form, change):
        """Personalizar el guardado desde el admin"""
        obj.save()
        
        # Si se cambió la vivienda, actualizar estados
        if change and 'vivienda' in form.changed_data:
            # La lógica de actualización de estados se maneja en el modelo
            pass

# ===== ACCIONES PERSONALIZADAS =====

def marcar_viviendas_como_mantenimiento(modeladmin, request, queryset):
    """Acción para marcar viviendas seleccionadas como en mantenimiento"""
    count = 0
    for vivienda in queryset:
        if vivienda.activo and vivienda.estado != 'OCUPADO':
            vivienda.estado = 'MANTENIMIENTO'
            vivienda.save()
            count += 1
    
    modeladmin.message_user(
        request, 
        f'{count} vivienda(s) marcada(s) como en mantenimiento.'
    )
marcar_viviendas_como_mantenimiento.short_description = "Marcar como en mantenimiento"

def liberar_viviendas_ocupadas(modeladmin, request, queryset):
    """Acción para liberar viviendas que no tienen residentes activos"""
    count = 0
    for vivienda in queryset:
        if vivienda.estado == 'OCUPADO' and not vivienda.get_residentes_activos().exists():
            vivienda.estado = 'DESOCUPADO'
            vivienda.save()
            count += 1
    
    modeladmin.message_user(
        request, 
        f'{count} vivienda(s) liberada(s) automáticamente.'
    )
liberar_viviendas_ocupadas.short_description = "Liberar viviendas sin residentes"

def activar_residentes(modeladmin, request, queryset):
    """Acción para activar residentes seleccionados"""
    count = queryset.filter(activo=False).update(activo=True)
    modeladmin.message_user(
        request, 
        f'{count} residente(s) activado(s).'
    )
activar_residentes.short_description = "Activar residentes seleccionados"

def desactivar_residentes(modeladmin, request, queryset):
    """Acción para desactivar residentes seleccionados"""
    count = queryset.filter(activo=True).update(activo=False)
    modeladmin.message_user(
        request, 
        f'{count} residente(s) desactivado(s).'
    )
desactivar_residentes.short_description = "Desactivar residentes seleccionados"

# Agregar acciones a los modelos
ViviendaAdmin.actions = [marcar_viviendas_como_mantenimiento, liberar_viviendas_ocupadas]
ResidenteAdmin.actions = [activar_residentes, desactivar_residentes]

# ===== INLINE ADMINS =====

class ResidenteInline(admin.TabularInline):
    model = Residente
    extra = 0
    fields = ['usuario', 'es_propietario', 'activo', 'vehiculos']
    readonly_fields = ['fecha_ingreso']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')

class ViviendaInline(admin.TabularInline):
    model = Vivienda
    extra = 0
    fields = ['numero', 'piso', 'estado', 'metros_cuadrados', 'habitaciones']
    readonly_fields = []
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('piso', 'numero')

# Agregar inlines
EdificioAdmin.inlines = [ViviendaInline]
ViviendaAdmin.inlines = [ResidenteInline]