from django.core.exceptions import ValidationError
from django.db import models
import secrets
from django.utils import timezone
from usuarios.models import Usuario
from viviendas.models import Vivienda, Residente

class Visita(models.Model):
    nombre_visitante = models.CharField(max_length=100)
    documento_visitante = models.CharField(max_length=20)
    vivienda_destino = models.ForeignKey(Vivienda, on_delete=models.CASCADE, related_name='visitas')
    residente_autoriza = models.ForeignKey(Residente, on_delete=models.CASCADE, related_name='visitas_autorizadas')
    fecha_hora_entrada = models.DateTimeField(auto_now_add=True)
    fecha_hora_salida = models.DateTimeField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)

    # Anti-replay QR
    qr_nonce = models.CharField(max_length=32, blank=True, default='', db_index=True)
    qr_usado = models.BooleanField(default=False)
    qr_usado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_hora_entrada']
        verbose_name = 'Visita'
        verbose_name_plural = 'Visitas'
        indexes = [
            models.Index(fields=['vivienda_destino', '-fecha_hora_entrada']),
            models.Index(fields=['residente_autoriza', '-fecha_hora_entrada']),
            models.Index(fields=['qr_usado']),
        ]

    def clean(self):
        if self.documento_visitante and len(self.documento_visitante.strip()) < 6:
            raise ValidationError({
                'documento_visitante': 'El documento debe tener al menos 6 caracteres.'
            })
        if self.fecha_hora_salida and self.fecha_hora_entrada:
            if self.fecha_hora_salida < self.fecha_hora_entrada:
                raise ValidationError({
                    'fecha_hora_salida': 'La fecha de salida no puede ser anterior a la de entrada.'
                })

    def save(self, *args, **kwargs):
        if not self.qr_nonce:
            self.qr_nonce = secrets.token_urlsafe(24)[:32]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_visitante} - {self.vivienda_destino} - {self.fecha_hora_entrada.strftime('%d/%m/%Y %H:%M')}"

class MovimientoResidente(models.Model):
    residente = models.ForeignKey(Residente, on_delete=models.CASCADE, related_name='movimientos')
    fecha_hora_entrada = models.DateTimeField(null=True, blank=True)
    fecha_hora_salida = models.DateTimeField(null=True, blank=True)
    vehiculo = models.BooleanField(default=False)
    placa_vehiculo = models.CharField(max_length=10, blank=True)
    
    class Meta:
        ordering = ['-fecha_hora_entrada', '-fecha_hora_salida']
        verbose_name = 'Movimiento de Residente'
        verbose_name_plural = 'Movimientos de Residentes'
        indexes = [
            models.Index(fields=['residente', '-fecha_hora_entrada']),
            models.Index(fields=['-fecha_hora_salida']),
        ]

    def clean(self):
        if self.vehiculo and not self.placa_vehiculo.strip():
            raise ValidationError({
                'placa_vehiculo': 'Debe indicar la placa del vehículo.'
            })
        if self.fecha_hora_salida and self.fecha_hora_entrada:
            if self.fecha_hora_salida < self.fecha_hora_entrada:
                raise ValidationError({
                    'fecha_hora_salida': 'La fecha de salida no puede ser anterior a la de entrada.'
                })

    def __str__(self):
        tipo = "Entrada" if self.fecha_hora_entrada and not self.fecha_hora_salida else "Salida"
        fecha = self.fecha_hora_entrada if tipo == "Entrada" else self.fecha_hora_salida
        return f"{self.residente} - {tipo} - {fecha.strftime('%d/%m/%Y %H:%M') if fecha else 'N/A'}"
