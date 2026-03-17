from django.db import models
from django.conf import settings

class Reporte(models.Model):
    TIPO_CHOICES = [
        ('ACCESOS', 'Accesos'),
        ('RESIDENTES', 'Residentes'),
        ('VIVIENDAS', 'Viviendas'),
        ('PERSONAL', 'Personal'),
        ('FINANCIERO', 'Financiero'),
    ]
    FORMATO_CHOICES = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    ]

    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    formato_preferido = models.CharField(max_length=10, choices=FORMATO_CHOICES, default='PDF')
    fecha_desde = models.DateField(null=True, blank=True)
    fecha_hasta = models.DateField(null=True, blank=True)
    es_favorito = models.BooleanField(default=False)
    puesto = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    edificio = models.ForeignKey('viviendas.Edificio', on_delete=models.SET_NULL, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_creados'
    )
    ultima_generacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nombre