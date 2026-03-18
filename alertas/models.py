from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone

class Alerta(models.Model):
    TIPOS_ALERTA = [
        ('Incendio', 'Incendio'),
        ('Sismo', 'Sismo'),
        ('Seguridad', 'Seguridad'),
        ('Salud', 'Salud'),
        ('Aviso importante', 'Aviso importante'),
        ('Reunión', 'Reunión'),
    ]
    
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('resuelto', 'Resuelto'),
    ]
    
    # Transiciones válidas de estado
    TRANSICIONES_VALIDAS = {
        'pendiente': ['en_proceso'],
        'en_proceso': ['resuelto', 'pendiente'],
        'resuelto': [],
    }

    tipo = models.CharField(max_length=50, choices=TIPOS_ALERTA)
    descripcion = models.TextField()
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alertas_enviadas')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    atendido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas_atendidas')
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    edificio = models.ForeignKey(
        'viviendas.Edificio',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
    )
    vivienda = models.ForeignKey(
        'viviendas.Vivienda',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas',
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        indexes = [
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['estado', '-fecha']),
            models.Index(fields=['edificio', '-fecha']),
        ]

    def clean(self):
        # Validar transición de estado
        if self.pk:
            try:
                anterior = Alerta.objects.get(pk=self.pk)
                if anterior.estado != self.estado:
                    permitidos = self.TRANSICIONES_VALIDAS.get(anterior.estado, [])
                    if self.estado not in permitidos:
                        raise ValidationError({
                            'estado': f'No se puede cambiar de "{anterior.estado}" a "{self.estado}".'
                        })
            except Alerta.DoesNotExist:
                pass

        # Si se resuelve, debe tener atendido_por
        if self.estado == 'resuelto' and not self.atendido_por:
            raise ValidationError({
                'atendido_por': 'Debe indicar quién atendió la alerta para marcarla como resuelta.'
            })

        # Si está pendiente, no debería tener atendido_por ni fecha_atencion
        if self.estado == 'pendiente':
            self.atendido_por = None
            self.fecha_atencion = None

    def save(self, *args, **kwargs):
        # Auto-asignar fecha_atencion al resolver
        if self.estado == 'resuelto' and not self.fecha_atencion:
            self.fecha_atencion = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.enviado_por.username} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"