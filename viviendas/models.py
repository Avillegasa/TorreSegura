# viviendas/models.py - VERSIÓN CORREGIDA PARA COMPATIBILIDAD
from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class Edificio(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    pisos = models.PositiveIntegerField()
    fecha_construccion = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return self.nombre
    
    def get_total_viviendas(self):
        """Devuelve el número total de viviendas en el edificio"""
        return self.viviendas.count()
    
    def get_viviendas_ocupadas(self):
        """Devuelve el número de viviendas ocupadas"""
        return self.viviendas.filter(estado='OCUPADO').count()
    
    def get_porcentaje_ocupacion(self):
        """Calcula el porcentaje de ocupación"""
        total = self.get_total_viviendas()
        if total == 0:
            return 0
        return round((self.get_viviendas_ocupadas() / total) * 100, 1)
    
    class Meta:
        verbose_name = "Edificio"
        verbose_name_plural = "Edificios"
        ordering = ['nombre']

class Vivienda(models.Model):
    ESTADOS = [
        ('OCUPADO', 'Ocupado'),
        ('DESOCUPADO', 'Desocupado'),
        ('MANTENIMIENTO', 'En mantenimiento'),
        ('BAJA', 'Dado de baja'),
    ]
    
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='viviendas')
    numero = models.CharField(max_length=10)
    piso = models.PositiveIntegerField()
    metros_cuadrados = models.DecimalField(max_digits=6, decimal_places=2)
    habitaciones = models.PositiveIntegerField(default=1)
    baños = models.PositiveIntegerField(default=1)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='DESOCUPADO')
    activo = models.BooleanField(default=True, help_text="Indica si la vivienda está activa o ha sido dada de baja")
    fecha_baja = models.DateField(null=True, blank=True, help_text="Fecha en la que se dio de baja la vivienda")
    motivo_baja = models.TextField(blank=True, null=True, help_text="Motivo por el cual se dio de baja la vivienda")
    
    def __str__(self):
        return f"Vivienda {self.numero} - Piso {self.piso}"
    
    def clean(self):
        """Validaciones personalizadas"""
        if self.piso and self.edificio:
            if self.piso > self.edificio.pisos:
                raise ValidationError(f'El piso {self.piso} excede los {self.edificio.pisos} pisos del edificio')
        
        # Si está inactiva, debe estar en estado BAJA
        if not self.activo and self.estado != 'BAJA':
            self.estado = 'BAJA'
        
        # Si se reactiva, no puede estar en BAJA
        if self.activo and self.estado == 'BAJA':
            self.estado = 'DESOCUPADO'
    
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        
        # Manejar fecha de baja automáticamente
        if not self.activo and not self.fecha_baja:
            self.fecha_baja = timezone.now().date()
        elif self.activo:
            self.fecha_baja = None
            self.motivo_baja = None
        
        super().save(*args, **kwargs)
    
    def get_residentes_activos(self):
        """Devuelve los residentes activos de esta vivienda"""
        return self.residentes.filter(activo=True)
    
    def get_propietarios(self):
        """Devuelve los propietarios de esta vivienda"""
        return self.residentes.filter(es_propietario=True, activo=True)
    
    def get_inquilinos(self):
        """Devuelve los inquilinos de esta vivienda"""
        return self.residentes.filter(es_propietario=False, activo=True)
    
    def puede_ocuparse(self):
        """Verifica si la vivienda puede ser ocupada"""
        return self.activo and self.estado in ['DESOCUPADO', 'MANTENIMIENTO']
    
    def marcar_como_ocupada(self):
        """Marca la vivienda como ocupada si es posible"""
        if self.puede_ocuparse():
            self.estado = 'OCUPADO'
            self.save(update_fields=['estado'])
            return True
        return False
    
    def liberar_vivienda(self):
        """Libera la vivienda si no tiene residentes activos"""
        if self.activo and not self.get_residentes_activos().exists():
            self.estado = 'DESOCUPADO'
            self.save(update_fields=['estado'])
            return True
        return False
    
    @property
    def nombre_completo(self):
        """Devuelve el nombre completo de la vivienda"""
        return f"{self.edificio.nombre} - Vivienda {self.numero} (Piso {self.piso})"
    
    class Meta:
        verbose_name = "Vivienda"
        verbose_name_plural = "Viviendas"
        ordering = ['edificio__nombre', 'piso', 'numero']
        unique_together = ('edificio', 'numero')
        indexes = [
            models.Index(fields=['edificio', 'estado']),
            models.Index(fields=['activo', 'estado']),
        ]

class Residente(models.Model):
    """
    Modelo de Residente - NO MODIFICAR - Solo métodos helper
    Este modelo está en el módulo de usuarios/viviendas
    """
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='residente')
    vivienda = models.ForeignKey(Vivienda, on_delete=models.SET_NULL, null=True, related_name='residentes')
    fecha_ingreso = models.DateField(auto_now_add=True)
    vehiculos = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True, 
        help_text="Indica si el residente actualmente vive o está relacionado con la vivienda")
    es_propietario = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Evitar recursión: solo actualizar si es necesario
        vivienda_anterior = None
        
        # Si el objeto ya existe, obtener la vivienda anterior
        if self.pk:
            try:
                residente_anterior = Residente.objects.get(pk=self.pk)
                vivienda_anterior = residente_anterior.vivienda
            except Residente.DoesNotExist:
                pass
        
        # Sincronizar con el estado del usuario si existe la relación
        if hasattr(self, 'usuario') and hasattr(self.usuario, 'is_active'):
            self.activo = self.usuario.is_active
        
        # Guardar el residente primero
        super().save(*args, **kwargs)
        
        # Actualizar estados de vivienda DESPUÉS de guardar
        try:
            # Liberar vivienda anterior si cambió
            if (vivienda_anterior and 
                vivienda_anterior != self.vivienda and 
                vivienda_anterior.estado == 'OCUPADO'):
                # Verificar si quedan otros residentes activos
                otros_activos = Residente.objects.filter(
                    vivienda=vivienda_anterior,
                    activo=True
                ).exclude(pk=self.pk).exists()
                
                if not otros_activos:
                    vivienda_anterior.liberar_vivienda()
            
            # Ocupar nueva vivienda si corresponde
            if (self.vivienda and self.activo and 
                self.vivienda.estado == 'DESOCUPADO'):
                self.vivienda.marcar_como_ocupada()
            
            # Si el residente se desactiva, verificar si liberar vivienda
            elif (self.vivienda and not self.activo and 
                  self.vivienda.estado == 'OCUPADO'):
                # Solo liberar si no hay otros residentes activos
                otros_activos = self.vivienda.get_residentes_activos().exclude(pk=self.pk).exists()
                if not otros_activos:
                    self.vivienda.liberar_vivienda()
                    
        except Exception as e:
            # Log del error pero no fallar el guardado
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error al actualizar estado de vivienda para residente {self.pk}: {e}")
    
    def __str__(self):
        usuario_str = f"{self.usuario.first_name} {self.usuario.last_name}" if hasattr(self, 'usuario') else "Usuario desconocido"
        vivienda_str = f"Vivienda {self.vivienda.numero}" if self.vivienda else "Sin vivienda"
        return f"{usuario_str} - {vivienda_str}"
    
    @property
    def nombre_completo(self):
        """Devuelve el nombre completo del residente"""
        if hasattr(self, 'usuario'):
            return f"{self.usuario.first_name} {self.usuario.last_name}"
        return "Usuario desconocido"
    
    @property
    def tipo_residente(self):
        """Devuelve el tipo de residente"""
        return "Propietario" if self.es_propietario else "Inquilino"
    
    class Meta:
        verbose_name = "Residente"
        verbose_name_plural = "Residentes"
        ordering = ['vivienda__edificio__nombre', 'vivienda__numero', 'usuario__last_name']

# ===== SEÑALES PARA SINCRONIZACIÓN =====

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_residente_with_user_status(sender, instance, created, **kwargs):
    """
    Sincronizar estado del residente cuando cambia el usuario
    SOLO si no fue creado recientemente
    """
    if not created and hasattr(instance, 'residente'):
        try:
            residente = instance.residente
            if residente.activo != instance.is_active:
                # Usar update() para evitar señales en cascada
                Residente.objects.filter(pk=residente.pk).update(activo=instance.is_active)
                
                # Manejar liberación de vivienda si se desactiva
                if not instance.is_active and residente.vivienda:
                    # Verificar si hay otros residentes activos
                    otros_activos = residente.vivienda.get_residentes_activos().exclude(
                        pk=residente.pk
                    ).exists()
                    
                    if not otros_activos:
                        residente.vivienda.liberar_vivienda()
                
                # Ocupar vivienda si se reactiva
                elif instance.is_active and residente.vivienda:
                    if residente.vivienda.puede_ocuparse():
                        residente.vivienda.marcar_como_ocupada()
                        
        except Exception as e:
            # Log del error pero no fallar la operación principal
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error al sincronizar residente con usuario {instance.id}: {e}")

@receiver(pre_delete, sender=Residente)
def liberar_vivienda_before_delete_residente(sender, instance, **kwargs):
    """
    Liberar vivienda antes de eliminar un residente
    """
    try:
        if instance.vivienda and instance.activo:
            # Verificar si hay otros residentes activos
            otros_activos = instance.vivienda.get_residentes_activos().exclude(
                pk=instance.pk
            ).exists()
            
            if not otros_activos:
                instance.vivienda.liberar_vivienda()
                
    except Exception as e:
        # Log del error pero no fallar la eliminación
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error al liberar vivienda antes de eliminar residente {instance.pk}: {e}")

@receiver(post_delete, sender=Residente)
def cleanup_after_residente_delete(sender, instance, **kwargs):
    """
    Limpieza adicional después de eliminar un residente
    """
    try:
        # Esta señal se ejecuta después del borrado, por si necesitamos
        # hacer alguna limpieza adicional en el futuro
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error en limpieza post-eliminación de residente: {e}")

# ===== MÉTODOS HELPER PARA EL MÓDULO FINANCIERO =====

def get_viviendas_for_financial_module():
    """
    Helper para el módulo financiero - devuelve viviendas activas
    """
    return Vivienda.objects.filter(activo=True).select_related('edificio')

def get_viviendas_by_edificio(edificio_id):
    """
    Helper para filtrar viviendas por edificio (usado en forms financieros)
    """
    return Vivienda.objects.filter(
        edificio_id=edificio_id,
        activo=True
    ).order_by('piso', 'numero')

def validate_vivienda_for_financial_operations(vivienda):
    """
    Valida que una vivienda puede ser usada en operaciones financieras
    """
    if not vivienda.activo:
        return False, "La vivienda está dada de baja"
    
    if vivienda.estado == 'BAJA':
        return False, "La vivienda está en estado de baja"
    
    return True, "Vivienda válida"