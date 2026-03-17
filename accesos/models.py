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

    def save(self, *args, **kwargs):
        if not self.qr_nonce:
            # token_urlsafe() puede traer '-' y '_' (ok en QR); truncamos para tamaño fijo
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
    
    def __str__(self):
        tipo = "Entrada" if self.fecha_hora_entrada and not self.fecha_hora_salida else "Salida"
        fecha = self.fecha_hora_entrada if tipo == "Entrada" else self.fecha_hora_salida
        return f"{self.residente} - {tipo} - {fecha.strftime('%d/%m/%Y %H:%M') if fecha else 'N/A'}"
