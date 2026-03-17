# financiero/admin.py - Configuración del admin para módulo financiero
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from .models import (
    ConceptoCuota, Cuota, Pago, PagoCuota,
    CategoriaGasto, Gasto, EstadoCuenta
)

@admin.register(ConceptoCuota)
class ConceptoCuotaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'monto_base', 'periodicidad', 'aplica_recargo', 'porcentaje_recargo', 'activo', 'cuotas_count']
    list_filter = ['periodicidad', 'aplica_recargo', 'activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
    list_editable = ['activo']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'monto_base', 'periodicidad')
        }),
        ('Configuración de Recargos', {
            'fields': ('aplica_recargo', 'porcentaje_recargo'),
            'description': 'Configuración para recargos por mora'
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )
    
    def cuotas_count(self, obj):
        count = obj.cuotas.count()
        if count == 0:
            return '0'
        
        url = reverse('admin:financiero_cuota_changelist')
        return format_html(
            '<a href="{}?concepto__id__exact={}"><strong>{}</strong> cuotas</a>',
            url, obj.pk, count
        )
    cuotas_count.short_description = 'Cuotas Generadas'

@admin.register(Cuota)
class CuotaAdmin(admin.ModelAdmin):
    list_display = ['concepto', 'vivienda', 'monto', 'recargo', 'total_display', 'fecha_emision', 'fecha_vencimiento', 'pagada', 'estado_vencimiento']
    list_filter = ['concepto', 'pagada', 'fecha_emision', 'fecha_vencimiento', 'vivienda__edificio']
    search_fields = ['concepto__nombre', 'vivienda__numero', 'vivienda__edificio__nombre']
    ordering = ['-fecha_vencimiento', 'vivienda__edificio__nombre', 'vivienda__numero']
    list_editable = ['pagada']
    date_hierarchy = 'fecha_vencimiento'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('concepto', 'vivienda', 'monto')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_vencimiento')
        }),
        ('Estado y Recargos', {
            'fields': ('pagada', 'recargo')
        }),
        ('Notas', {
            'fields': ('notas',)
        }),
    )
    
    readonly_fields = ['recargo']
    
    def total_display(self, obj):
        total = obj.total_a_pagar()
        color = 'green' if obj.pagada else 'red' if obj.fecha_vencimiento < timezone.now().date() else 'black'
        return format_html('<span style="color: {};">${:.2f}</span>', color, total)
    total_display.short_description = 'Total a Pagar'
    
    def estado_vencimiento(self, obj):
        if obj.pagada:
            return format_html('<span style="color: green;">✓ Pagada</span>')
        elif obj.fecha_vencimiento < timezone.now().date():
            dias_vencida = (timezone.now().date() - obj.fecha_vencimiento).days
            return format_html('<span style="color: red;">⚠ Vencida ({} días)</span>', dias_vencida)
        else:
            dias_restantes = (obj.fecha_vencimiento - timezone.now().date()).days
            return format_html('<span style="color: orange;">⏰ {} días restantes</span>', dias_restantes)
    estado_vencimiento.short_description = 'Estado'
    
    def save_model(self, request, obj, form, change):
        """Actualizar recargo automáticamente al guardar"""
        if not obj.pagada:
            obj.recargo = obj.calcular_recargo()
        obj.save()

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['id', 'vivienda', 'residente', 'monto', 'fecha_pago', 'metodo_pago', 'estado', 'registrado_por', 'cuotas_aplicadas']
    list_filter = ['estado', 'metodo_pago', 'fecha_pago', 'vivienda__edificio']
    search_fields = ['vivienda__numero', 'residente__usuario__first_name', 'residente__usuario__last_name', 'referencia']
    ordering = ['-fecha_pago', '-id']
    list_editable = ['estado']
    date_hierarchy = 'fecha_pago'
    
    fieldsets = (
        ('Información del Pago', {
            'fields': ('vivienda', 'residente', 'monto', 'fecha_pago')
        }),
        ('Detalles del Pago', {
            'fields': ('metodo_pago', 'referencia', 'comprobante')
        }),
        ('Estado y Verificación', {
            'fields': ('estado', 'registrado_por', 'verificado_por', 'fecha_verificacion')
        }),
        ('Notas', {
            'fields': ('notas',)
        }),
    )
    
    readonly_fields = ['registrado_por', 'verificado_por', 'fecha_verificacion']
    
    def cuotas_aplicadas(self, obj):
        count = obj.pagocuota_set.count()
        if count == 0:
            return 'Sin asignar'
        
        total_aplicado = obj.pagocuota_set.aggregate(
            total=models.Sum('monto_aplicado')
        )['total'] or 0
        
        return format_html(
            '<strong>{}</strong> cuotas (${:.2f})',
            count, total_aplicado
        )
    cuotas_aplicadas.short_description = 'Cuotas Aplicadas'
    
    def save_model(self, request, obj, form, change):
        """Personalizar guardado del pago"""
        if not change:  # Nuevo pago
            obj.registrado_por = request.user
        
        # Si se verifica el pago y no tiene verificador
        if obj.estado == 'VERIFICADO' and not obj.verificado_por:
            obj.verificado_por = request.user
            obj.fecha_verificacion = timezone.now()
        
        obj.save()

@admin.register(PagoCuota)
class PagoCuotaAdmin(admin.ModelAdmin):
    list_display = ['pago', 'cuota', 'monto_aplicado', 'fecha_pago', 'estado_pago']
    list_filter = ['pago__estado', 'cuota__concepto', 'pago__fecha_pago']
    search_fields = ['pago__vivienda__numero', 'cuota__concepto__nombre']
    ordering = ['-pago__fecha_pago']
    
    def fecha_pago(self, obj):
        return obj.pago.fecha_pago
    fecha_pago.short_description = 'Fecha del Pago'
    
    def estado_pago(self, obj):
        estado = obj.pago.estado
        colors = {
            'VERIFICADO': 'green',
            'PENDIENTE': 'orange',
            'RECHAZADO': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(estado, 'black'), estado
        )
    estado_pago.short_description = 'Estado del Pago'

@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'presupuesto_mensual', 'gasto_mes_actual', 'porcentaje_utilizado', 'activo', 'gastos_count']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
    list_editable = ['activo']
    
    def gasto_mes_actual(self, obj):
        gasto = obj.total_gastado_mes_actual()
        return f'${gasto:.2f}'
    gasto_mes_actual.short_description = 'Gasto Mes Actual'
    
    def porcentaje_utilizado(self, obj):
        porcentaje = obj.porcentaje_presupuesto_utilizado()
        color = 'red' if porcentaje > 100 else 'orange' if porcentaje > 80 else 'green'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, porcentaje)
    porcentaje_utilizado.short_description = '% Presupuesto'
    
    def gastos_count(self, obj):
        count = obj.gastos.count()
        if count == 0:
            return '0'
        
        url = reverse('admin:financiero_gasto_changelist')
        return format_html(
            '<a href="{}?categoria__id__exact={}"><strong>{}</strong> gastos</a>',
            url, obj.pk, count
        )
    gastos_count.short_description = 'Gastos Registrados'

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ['concepto', 'categoria', 'monto', 'fecha', 'proveedor', 'estado', 'tipo_gasto', 'presupuestado', 'registrado_por']
    list_filter = ['estado', 'tipo_gasto', 'categoria', 'presupuestado', 'recurrente', 'fecha']
    search_fields = ['concepto', 'descripcion', 'proveedor', 'factura']
    ordering = ['-fecha', '-id']
    list_editable = ['estado']
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('categoria', 'concepto', 'descripcion', 'monto')
        }),
        ('Proveedor y Facturación', {
            'fields': ('proveedor', 'factura', 'comprobante')
        }),
        ('Fechas', {
            'fields': ('fecha', 'fecha_pago')
        }),
        ('Clasificación', {
            'fields': ('estado', 'tipo_gasto', 'presupuestado', 'recurrente')
        }),
        ('Información Adicional', {
            'fields': ('registrado_por', 'autorizado_por', 'notas')
        }),
    )
    
    readonly_fields = ['registrado_por']
    
    def save_model(self, request, obj, form, change):
        """Personalizar guardado del gasto"""
        if not change:  # Nuevo gasto
            obj.registrado_por = request.user
        
        # Si se marca como pagado y no tiene fecha de pago
        if obj.estado == 'PAGADO' and not obj.fecha_pago:
            obj.fecha_pago = timezone.now().date()
        
        obj.save()

@admin.register(EstadoCuenta)
class EstadoCuentaAdmin(admin.ModelAdmin):
    list_display = ['vivienda', 'periodo', 'saldo_anterior', 'total_cuotas', 'total_pagos', 'saldo_final', 'enviado', 'fecha_generacion']
    list_filter = ['enviado', 'fecha_generacion', 'vivienda__edificio']
    search_fields = ['vivienda__numero', 'vivienda__edificio__nombre']
    ordering = ['-fecha_fin', 'vivienda__edificio__nombre', 'vivienda__numero']
    list_editable = ['enviado']
    date_hierarchy = 'fecha_fin'
    
    fieldsets = (
        ('Vivienda y Período', {
            'fields': ('vivienda', 'fecha_inicio', 'fecha_fin')
        }),
        ('Saldos y Totales', {
            'fields': ('saldo_anterior', 'total_cuotas', 'total_pagos', 'total_recargos', 'saldo_final')
        }),
        ('Estado del Envío', {
            'fields': ('enviado', 'fecha_envio', 'pdf_generado')
        }),
    )
    
    readonly_fields = ['total_cuotas', 'total_pagos', 'total_recargos', 'saldo_final', 'fecha_generacion']
    
    def periodo(self, obj):
        return f"{obj.fecha_inicio.strftime('%d/%m/%Y')} - {obj.fecha_fin.strftime('%d/%m/%Y')}"
    periodo.short_description = 'Período'
    
    def save_model(self, request, obj, form, change):
        """Recalcular totales automáticamente al guardar"""
        obj.save()
        if not change:  # Nuevo estado de cuenta
            obj.calcular_totales()

# ===== ACCIONES PERSONALIZADAS =====

def marcar_cuotas_como_pagadas(modeladmin, request, queryset):
    """Acción para marcar cuotas seleccionadas como pagadas (usar con cuidado)"""
    count = queryset.filter(pagada=False).update(pagada=True)
    modeladmin.message_user(
        request,
        f'{count} cuota(s) marcada(s) como pagadas. ATENCIÓN: Verifique que realmente fueron pagadas.'
    )
marcar_cuotas_como_pagadas.short_description = "⚠️ Marcar como pagadas (CUIDADO)"

def actualizar_recargos_cuotas(modeladmin, request, queryset):
    """Acción para actualizar recargos de cuotas vencidas"""
    count = 0
    for cuota in queryset.filter(pagada=False):
        recargo_anterior = cuota.recargo
        cuota.actualizar_recargo()
        if cuota.recargo != recargo_anterior:
            count += 1
    
    modeladmin.message_user(
        request,
        f'Recargos actualizados en {count} cuota(s).'
    )
actualizar_recargos_cuotas.short_description = "Actualizar recargos"

def verificar_pagos_pendientes(modeladmin, request, queryset):
    """Acción para verificar pagos pendientes seleccionados"""
    count = 0
    for pago in queryset.filter(estado='PENDIENTE'):
        pago.verificar_pago(request.user)
        count += 1
    
    modeladmin.message_user(
        request,
        f'{count} pago(s) verificado(s).'
    )
verificar_pagos_pendientes.short_description = "Verificar pagos seleccionados"

def rechazar_pagos_pendientes(modeladmin, request, queryset):
    """Acción para rechazar pagos pendientes seleccionados"""
    count = 0
    for pago in queryset.filter(estado='PENDIENTE'):
        pago.rechazar_pago(request.user, "Rechazado desde el admin")
        count += 1
    
    modeladmin.message_user(
        request,
        f'{count} pago(s) rechazado(s).'
    )
rechazar_pagos_pendientes.short_description = "Rechazar pagos seleccionados"

def marcar_gastos_como_pagados(modeladmin, request, queryset):
    """Acción para marcar gastos como pagados"""
    count = 0
    for gasto in queryset.filter(estado='PENDIENTE'):
        gasto.marcar_como_pagado()
        count += 1
    
    modeladmin.message_user(
        request,
        f'{count} gasto(s) marcado(s) como pagados.'
    )
marcar_gastos_como_pagados.short_description = "Marcar como pagados"

def generar_estados_cuenta_automaticos(modeladmin, request, queryset):
    """Acción para generar estados de cuenta automáticamente"""
    count = 0
    for estado in queryset.filter(total_cuotas=0, total_pagos=0):
        estado.calcular_totales()
        count += 1
    
    modeladmin.message_user(
        request,
        f'Totales recalculados en {count} estado(s) de cuenta.'
    )
generar_estados_cuenta_automaticos.short_description = "Recalcular totales"

# Agregar acciones a los modelos
CuotaAdmin.actions = [marcar_cuotas_como_pagadas, actualizar_recargos_cuotas]
PagoAdmin.actions = [verificar_pagos_pendientes, rechazar_pagos_pendientes]
GastoAdmin.actions = [marcar_gastos_como_pagados]
EstadoCuentaAdmin.actions = [generar_estados_cuenta_automaticos]

# ===== INLINE ADMINS =====

class CuotaInline(admin.TabularInline):
    model = Cuota
    extra = 0
    fields = ['concepto', 'monto', 'fecha_emision', 'fecha_vencimiento', 'pagada']
    readonly_fields = ['fecha_emision']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('concepto').order_by('-fecha_vencimiento')

class PagoCuotaInline(admin.TabularInline):
    model = PagoCuota
    extra = 0
    fields = ['cuota', 'monto_aplicado']
    readonly_fields = []
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cuota__concepto')

class GastoInline(admin.TabularInline):
    model = Gasto
    extra = 0
    fields = ['concepto', 'monto', 'fecha', 'estado']
    readonly_fields = ['fecha']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-fecha')

# Agregar inlines donde corresponda
PagoAdmin.inlines = [PagoCuotaInline]
CategoriaGastoAdmin.inlines = [GastoInline]

# ===== CONFIGURACIÓN ADICIONAL =====

# Personalizar el título del admin
admin.site.site_header = "Torre Segura - Administración Financiera"
admin.site.site_title = "Torre Segura Admin"
admin.site.index_title = "Panel de Administración Financiera"

# Agregar CSS personalizado para el admin
class FinancieroAdminConfig(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('admin/css/financiero-admin.css',)
        }
        js = ('admin/js/financiero-admin.js',)