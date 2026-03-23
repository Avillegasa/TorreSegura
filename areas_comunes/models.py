from django.db import models
from django.core.exceptions import ValidationError
from viviendas.models import Edificio, Residente


class AreaComun(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    edificio = models.ForeignKey(
        Edificio, on_delete=models.CASCADE, related_name="areas_comunes"
    )
    capacidad_maxima = models.PositiveIntegerField(default=20)
    horario_inicio = models.TimeField(default="08:00")
    horario_fin = models.TimeField(default="22:00")
    imagen = models.ImageField(upload_to="areas_comunes/", blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Area Comun"
        verbose_name_plural = "Areas Comunes"

    def __str__(self):
        return f"{self.nombre} - {self.edificio.nombre}"


class Reserva(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("confirmada", "Confirmada"),
        ("cancelada", "Cancelada"),
        ("completada", "Completada"),
    ]

    area_comun = models.ForeignKey(
        AreaComun, on_delete=models.CASCADE, related_name="reservas"
    )
    residente = models.ForeignKey(
        Residente, on_delete=models.CASCADE, related_name="reservas"
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="confirmada")
    motivo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-hora_inicio"]
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        indexes = [
            models.Index(fields=["area_comun", "fecha"]),
            models.Index(fields=["residente", "-fecha"]),
        ]

    def clean(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError(
                {"hora_fin": "La hora de fin debe ser mayor a la hora de inicio."}
            )

        solapadas = Reserva.objects.filter(
            area_comun=self.area_comun,
            fecha=self.fecha,
            estado__in=["pendiente", "confirmada"],
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)

        if solapadas.exists():
            raise ValidationError(
                "Ya existe una reserva en ese horario para esta area."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.area_comun.nombre} - {self.residente} - {self.fecha}"
