# personal/models.py

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from usuarios.models import Usuario
from viviendas.models import Edificio, Vivienda

class Puesto(models.Model):
    """
    Modelo para definir los diferentes puestos de trabajo del personal
    del condominio, como conserje, jardinero, técnico de mantenimiento, etc.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    requiere_especializacion = models.BooleanField(default=False)
    # ✅ CORRECCIÓN: Campos adicionales para mejor gestión
    activo = models.BooleanField(default=True, help_text="Indica si el puesto está disponible para asignar")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip().title()
            if len(self.nombre) < 3:
                raise ValidationError({'nombre': 'El nombre del puesto debe tener al menos 3 caracteres.'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = "Puesto"
        verbose_name_plural = "Puestos"
        ordering = ['nombre']
        # ✅ CORRECCIÓN: Solo constraints compatibles con SQLite
        constraints = [
            models.CheckConstraint(
                check=models.Q(nombre__isnull=False),
                name='puesto_nombre_not_null'
            ),
        ]

class Empleado(models.Model):
    """
    Modelo para gestionar los empleados que trabajan en el condominio.
    Se relaciona con el modelo Usuario para gestionar la autenticación.
    """
    TIPOS_CONTRATO = [
        ('PERMANENTE', 'Permanente'),
        ('TEMPORAL', 'Temporal'),
        ('EXTERNO', 'Proveedor Externo'),
    ]
    
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='empleado')
    puesto = models.ForeignKey(Puesto, on_delete=models.PROTECT, related_name='empleados')
    edificio = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True, blank=True, related_name='empleados')
    fecha_contratacion = models.DateField()
    tipo_contrato = models.CharField(max_length=15, choices=TIPOS_CONTRATO, default='PERMANENTE')
    salario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    contacto_emergencia = models.CharField(max_length=150, blank=True)
    telefono_emergencia = models.CharField(max_length=15, blank=True)
    especialidad = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    # ✅ CORRECCIÓN: Campos adicionales para auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    creado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='empleados_creados'
    )
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
    
        # ✅ VERIFICAR si el usuario existe antes de acceder a sus propiedades
        if hasattr(self, 'usuario') and self.usuario is not None:
            if hasattr(self.usuario, 'rol') and self.usuario.rol:
                if self.usuario.rol.nombre != "Personal":
                    raise ValidationError("Solo los usuarios con rol 'Personal' pueden ser asignados como empleados.")

        # Validar fecha de contratación
        if self.fecha_contratacion:
            if self.fecha_contratacion > timezone.now().date():
                raise ValidationError({'fecha_contratacion': 'La fecha de contratación no puede ser futura.'})
    
        # Validar salario
        if self.salario is not None and self.salario < 0:
            raise ValidationError({'salario': 'El salario no puede ser negativo.'})
    
        # Validar contacto de emergencia
        if self.contacto_emergencia and not self.telefono_emergencia:
            raise ValidationError({'telefono_emergencia': 'Si proporciona contacto de emergencia, debe incluir el teléfono.'})
    
        if self.telefono_emergencia and not self.contacto_emergencia:
            raise ValidationError({'contacto_emergencia': 'Si proporciona teléfono de emergencia, debe incluir el contacto.'})
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - {self.puesto.nombre}"
    
    @property
    def nombre_completo(self):
        return f"{self.usuario.first_name} {self.usuario.last_name}"
    
    @property
    def antiguedad_anos(self):
        """Calcula los años de antigüedad del empleado"""
        if self.fecha_contratacion:
            delta = timezone.now().date() - self.fecha_contratacion
            return delta.days // 365
        return 0
    
    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['usuario__last_name', 'usuario__first_name']
        # ✅ CORRECCIÓN: Solo constraints compatibles con SQLite
        constraints = [
            models.CheckConstraint(
                check=models.Q(salario__gte=0) | models.Q(salario__isnull=True),
                name='empleado_salario_no_negativo'
            ),
        ]

class Asignacion(models.Model):
    """
    Modelo para gestionar las asignaciones de trabajo a los empleados.
    Puede ser una tarea puntual o una responsabilidad recurrente.
    """
    TIPOS_ASIGNACION = [
        ('TAREA', 'Tarea puntual'),
        ('RESPONSABILIDAD', 'Responsabilidad recurrente'),
    ]
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROGRESO', 'En progreso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    PRIORIDADES = [
        (1, 'Baja'),
        (2, 'Normal'),
        (3, 'Alta'),
        (4, 'Urgente'),
    ]
    
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asignaciones')
    tipo = models.CharField(max_length=20, choices=TIPOS_ASIGNACION)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='asignaciones', null=True, blank=True)
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, related_name='asignaciones', null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE')
    prioridad = models.IntegerField(choices=PRIORIDADES, default=2)
    notas = models.TextField(blank=True)
    asignado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='asignaciones_creadas')
    # ✅ CORRECCIÓN: Campos adicionales para seguimiento
    fecha_completada = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora cuando se completó la asignación")
    tiempo_estimado_horas = models.PositiveIntegerField(null=True, blank=True, help_text="Tiempo estimado en horas")
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        
        # Validar fechas
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_inicio > self.fecha_fin:
                raise ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'})
        
        # Para tareas puntuales, requerir fecha de fin
        if self.tipo == 'TAREA' and not self.fecha_fin:
            raise ValidationError({'fecha_fin': 'Las tareas puntuales deben tener fecha de finalización.'})
        
        # Validar que la vivienda pertenezca al edificio
        if self.vivienda and self.edificio:
            if self.vivienda.edificio != self.edificio:
                raise ValidationError({'vivienda': 'La vivienda seleccionada no pertenece al edificio especificado.'})
        
        # Auto-asignar edificio si solo se especifica vivienda
        if self.vivienda and not self.edificio:
            self.edificio = self.vivienda.edificio
        
        # Validar título
        if self.titulo and len(self.titulo.strip()) < 5:
            raise ValidationError({'titulo': 'El título debe tener al menos 5 caracteres.'})
        
        # Validar tiempo estimado
        if self.tiempo_estimado_horas is not None and self.tiempo_estimado_horas > 168:
            raise ValidationError({'tiempo_estimado_horas': 'El tiempo estimado no puede exceder 168 horas (1 semana).'})
    
    def save(self, *args, **kwargs):
        # Auto-completar fecha de completada si cambia a COMPLETADA
        if self.estado == 'COMPLETADA' and not self.fecha_completada:
            self.fecha_completada = timezone.now()
        elif self.estado != 'COMPLETADA':
            self.fecha_completada = None
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.titulo} - {self.empleado}"
    
    @property
    def esta_vencida(self):
        """Verifica si la asignación está vencida"""
        if not self.fecha_fin or self.estado in ['COMPLETADA', 'CANCELADA']:
            return False
        return timezone.now().date() > self.fecha_fin
    
    @property
    def dias_restantes(self):
        """Calcula los días restantes para completar la asignación"""
        if not self.fecha_fin or self.estado in ['COMPLETADA', 'CANCELADA']:
            return None
        delta = self.fecha_fin - timezone.now().date()
        return delta.days
    
    @property
    def duracion_real_horas(self):
        """Calcula la duración real en horas si está completada"""
        if self.estado == 'COMPLETADA' and self.fecha_completada:
            delta = self.fecha_completada - self.fecha_asignacion
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ['-fecha_asignacion', '-prioridad']
        # ✅ CORRECCIÓN: Solo constraints básicos compatibles con SQLite
        constraints = [
            models.CheckConstraint(
                check=models.Q(prioridad__gte=1) & models.Q(prioridad__lte=4),
                name='asignacion_prioridad_valida'
            ),
            models.CheckConstraint(
                check=models.Q(tiempo_estimado_horas__gte=0) | models.Q(tiempo_estimado_horas__isnull=True),
                name='asignacion_tiempo_estimado_no_negativo'
            ),
        ]
        # ✅ CORRECCIÓN: Índices básicos
        indexes = [
            models.Index(fields=['estado', '-fecha_asignacion']),
            models.Index(fields=['empleado', '-fecha_asignacion']),
            models.Index(fields=['edificio', 'estado']),
        ]

class ComentarioAsignacion(models.Model):
    """
    Modelo para registrar comentarios sobre las asignaciones,
    ya sea por parte del empleado o de los administradores.
    """
    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(max_length=1000)
    # ✅ CORRECCIÓN: Campos adicionales
    es_privado = models.BooleanField(default=False, help_text="Solo visible para administradores")
    editado = models.BooleanField(default=False)
    fecha_edicion = models.DateTimeField(null=True, blank=True)
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        if self.comentario:
            comentario_limpio = self.comentario.strip()
            if len(comentario_limpio) < 3:
                raise ValidationError({'comentario': 'El comentario debe tener al menos 3 caracteres.'})
            self.comentario = comentario_limpio
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Comentario de {self.usuario} en {self.asignacion.titulo}"
    
    class Meta:
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"
        ordering = ['-fecha']
        # ✅ CORRECCIÓN: Sin constraints problemáticos para SQLite
        indexes = [
            models.Index(fields=['asignacion', '-fecha']),
            models.Index(fields=['usuario', '-fecha']),
        ]

# ✅ CORRECCIÓN: Señales mejoradas con mejor manejo de errores
@receiver(post_save, sender=Usuario)
def update_empleado_status(sender, instance, **kwargs):
    """Sincronizar el estado del empleado cuando cambia el estado del usuario"""
    try:
        if hasattr(instance, 'empleado'):
            empleado = instance.empleado
            if empleado.activo != instance.is_active:
                empleado.activo = instance.is_active
                empleado.save(update_fields=['activo'])
                
                # ✅ CORRECCIÓN: Cancelar asignaciones pendientes si se desactiva
                if not instance.is_active:
                    asignaciones_pendientes = Asignacion.objects.filter(
                        empleado=empleado,
                        estado__in=['PENDIENTE', 'EN_PROGRESO']
                    )
                    for asignacion in asignaciones_pendientes:
                        ComentarioAsignacion.objects.create(
                            asignacion=asignacion,
                            usuario=instance,
                            comentario=f"Asignación cancelada automáticamente debido a la desactivación del empleado.",
                            es_privado=True
                        )
                    asignaciones_pendientes.update(estado='CANCELADA')
                    
    except Exception as e:
        # Log el error pero no fallar la operación principal
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al sincronizar estado de empleado para usuario {instance.id}: {e}")

# ✅ CORRECCIÓN: Modelo simplificado para historial
class HistorialAsignacion(models.Model):
    """Modelo para registrar el historial de cambios en las asignaciones"""
    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='historial')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    campo_modificado = models.CharField(max_length=50)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Historial de Asignación"
        verbose_name_plural = "Historiales de Asignaciones"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['asignacion', '-fecha']),
        ]