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


class Anuncio(models.Model):
    """
    Anuncios y comunicados del condominio.
    Los Gerentes publican anuncios para los residentes de su edificio.
    Los Residentes pueden crear anuncios visibles para su edificio.
    """
    CATEGORIA_CHOICES = [
        ('general', 'General'),
        ('mantenimiento', 'Mantenimiento'),
        ('reunion', 'Reunión'),
        ('evento', 'Evento'),
        ('reglas', 'Reglas y Normativas'),
        ('financiero', 'Financiero'),
    ]

    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='general')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='anuncios',
    )
    edificio = models.ForeignKey(
        'viviendas.Edificio', on_delete=models.CASCADE,
        related_name='anuncios',
    )
    fijado = models.BooleanField(default=False, help_text="Anuncios fijados aparecen primero")
    activo = models.BooleanField(default=True)

    # ── Votación ──────────────────────────────────────────────────────
    es_votacion = models.BooleanField(default=False, help_text="Si es True, este anuncio tiene una encuesta adjunta")
    voto_anonimo = models.BooleanField(default=False, help_text="Si es True, no se muestra quién votó")
    fecha_cierre_votacion = models.DateTimeField(
        null=True, blank=True,
        help_text="Fecha y hora límite para votar. Null = sin límite.",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fijado', '-fecha_creacion']
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'
        indexes = [
            models.Index(fields=['edificio', '-fecha_creacion']),
            models.Index(fields=['activo', 'edificio']),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.edificio.nombre}"

    @property
    def votacion_abierta(self):
        """True si la votación sigue abierta."""
        if not self.es_votacion:
            return False
        if self.fecha_cierre_votacion and timezone.now() > self.fecha_cierre_votacion:
            return False
        return True

    @property
    def total_votos(self):
        return Voto.objects.filter(opcion__anuncio=self).count()


class OpcionVoto(models.Model):
    """Opción dentro de una votación de un anuncio."""
    anuncio = models.ForeignKey(Anuncio, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = 'Opción de Voto'
        verbose_name_plural = 'Opciones de Voto'

    def __str__(self):
        return f"{self.texto} (Anuncio: {self.anuncio_id})"

    @property
    def cantidad_votos(self):
        return self.votos.count()


class Voto(models.Model):
    """Voto de un usuario a una opción."""
    opcion = models.ForeignKey(OpcionVoto, on_delete=models.CASCADE, related_name='votos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votos_anuncios')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un usuario solo puede votar una vez por anuncio (se valida en la vista)
        unique_together = ('opcion', 'usuario')
        verbose_name = 'Voto'
        verbose_name_plural = 'Votos'

    def __str__(self):
        return f"{self.usuario.username} -> {self.opcion.texto}"