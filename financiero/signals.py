# financiero/signals.py - Señales para manejo automático de cuotas y pagos
from django.db.models.signals import post_save, post_delete, pre_save
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging

from .models import Pago, PagoCuota, Cuota, EstadoCuenta
from viviendas.models import Residente

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PagoCuota)
def actualizar_cuota_al_crear_pago_cuota(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza un PagoCuota, actualiza el estado de la cuota
    """
    try:
        cuota = instance.cuota
        pago = instance.pago
        
        # Solo procesar si el pago está verificado
        if pago.estado != 'VERIFICADO':
            return
        
        # Recalcular si la cuota está completamente pagada
        total_pagado = PagoCuota.objects.filter(
            cuota=cuota,
            pago__estado='VERIFICADO'
        ).aggregate(
            total=models.Sum('monto_aplicado')
        )['total'] or Decimal('0')
        
        total_cuota = cuota.total_a_pagar()
        
        if total_pagado >= total_cuota:
            # Cuota completamente pagada
            cuota.pagada = True
            cuota.recargo = Decimal('0')  # Limpiar recargos
            cuota.save(update_fields=['pagada', 'recargo'])
            logger.info(f"Cuota {cuota.id} marcada como pagada")
        else:
            # Pago parcial - actualizar monto pendiente
            monto_pendiente = cuota.monto - total_pagado
            if monto_pendiente > 0:
                cuota.monto = monto_pendiente
                cuota.pagada = False
                cuota.save(update_fields=['monto', 'pagada'])
                logger.info(f"Cuota {cuota.id} actualizada con pago parcial")
    
    except Exception as e:
        logger.error(f"Error al actualizar cuota en PagoCuota {instance.id}: {e}")

@receiver(post_delete, sender=PagoCuota)
def revertir_cuota_al_eliminar_pago_cuota(sender, instance, **kwargs):
    """
    Cuando se elimina un PagoCuota, revierte el estado de la cuota si es necesario
    """
    try:
        cuota = instance.cuota
        pago = instance.pago
        
        # Solo procesar si el pago estaba verificado
        if pago.estado != 'VERIFICADO':
            return
        
        # Si la cuota estaba marcada como pagada, revertir
        if cuota.pagada:
            cuota.pagada = False
            
            # Restaurar el monto original si es necesario
            # (esto es complejo, por simplicidad recalcular recargos)
            cuota.actualizar_recargo()
            cuota.save(update_fields=['pagada', 'recargo'])
            logger.info(f"Cuota {cuota.id} revertida por eliminación de pago")
    
    except Exception as e:
        logger.error(f"Error al revertir cuota en eliminación de PagoCuota: {e}")

@receiver(post_save, sender=Pago)
def procesar_pago_verificado(sender, instance, created, **kwargs):
    """
    Procesar automáticamente un pago cuando se verifica
    """
    try:
        # Solo procesar cuando el pago se marca como verificado
        if instance.estado == 'VERIFICADO' and not created:
            # Verificar si ya tiene cuotas asignadas
            cuotas_asignadas = PagoCuota.objects.filter(pago=instance).exists()
            
            if not cuotas_asignadas and instance.monto > 0:
                # Auto-asignar a cuotas pendientes más antiguas
                auto_asignar_pago_a_cuotas(instance)
    
    except Exception as e:
        logger.error(f"Error al procesar pago verificado {instance.id}: {e}")

def auto_asignar_pago_a_cuotas(pago):
    """
    Asigna automáticamente un pago a las cuotas pendientes más antiguas
    """
    try:
        # Obtener cuotas pendientes de la vivienda, ordenadas por vencimiento
        cuotas_pendientes = Cuota.objects.filter(
            vivienda=pago.vivienda,
            pagada=False
        ).order_by('fecha_vencimiento')
        
        monto_restante = pago.monto
        
        for cuota in cuotas_pendientes:
            if monto_restante <= Decimal('0'):
                break
            
            total_cuota = cuota.total_a_pagar()
            monto_aplicado = min(monto_restante, total_cuota)
            
            # Crear el PagoCuota
            PagoCuota.objects.create(
                pago=pago,
                cuota=cuota,
                monto_aplicado=monto_aplicado
            )
            
            monto_restante -= monto_aplicado
            logger.info(f"Auto-asignado ${monto_aplicado} del pago {pago.id} a cuota {cuota.id}")
    
    except Exception as e:
        logger.error(f"Error en auto-asignación de pago {pago.id}: {e}")

@receiver(post_save, sender=Pago)
def actualizar_fecha_verificacion(sender, instance, created, **kwargs):
    """
    Actualizar automáticamente la fecha de verificación cuando se verifica un pago
    """
    try:
        # Si el pago se acaba de verificar y no tiene fecha de verificación
        if (instance.estado == 'VERIFICADO' and 
            not instance.fecha_verificacion and 
            not created):
            
            # Actualizar la fecha de verificación sin disparar señales
            Pago.objects.filter(pk=instance.pk).update(
                fecha_verificacion=timezone.now()
            )
            logger.info(f"Fecha de verificación actualizada para pago {instance.id}")
    
    except Exception as e:
        logger.error(f"Error al actualizar fecha de verificación del pago {instance.id}: {e}")

@receiver(pre_save, sender=Cuota)
def calcular_recargo_antes_de_guardar(sender, instance, **kwargs):
    """
    Calcular automáticamente el recargo antes de guardar una cuota
    """
    try:
        # Solo calcular si la cuota no está pagada
        if not instance.pagada:
            nuevo_recargo = instance.calcular_recargo()
            if nuevo_recargo != instance.recargo:
                instance.recargo = nuevo_recargo
                logger.debug(f"Recargo actualizado para cuota {instance.id}: ${nuevo_recargo}")
    
    except Exception as e:
        logger.error(f"Error al calcular recargo para cuota {instance.id}: {e}")

@receiver(post_save, sender=Residente)
def sincronizar_pagos_con_residente(sender, instance, created, **kwargs):
    """
    Sincronizar información de pagos cuando se actualiza un residente
    """
    try:
        # Si el residente cambia de vivienda, actualizar pagos futuros
        if not created and instance.vivienda:
            # Solo para casos donde se necesite sincronización adicional
            # Por ahora, los pagos ya están ligados a vivienda directamente
            pass
    
    except Exception as e:
        logger.error(f"Error al sincronizar pagos con residente {instance.id}: {e}")

@receiver(post_save, sender=EstadoCuenta)
def generar_pdf_automatico(sender, instance, created, **kwargs):
    """
    Generar PDF automáticamente cuando se crea un estado de cuenta
    """
    try:
        if created and not instance.pdf_generado:
            # Esto se puede implementar más tarde con una tarea asíncrona
            # por ahora solo marcamos que necesita generación
            logger.info(f"Estado de cuenta {instance.id} creado, PDF pendiente de generación")
    
    except Exception as e:
        logger.error(f"Error al procesar nuevo estado de cuenta {instance.id}: {e}")

# ===== FUNCIONES HELPER PARA PROCESAMIENTO =====

def procesar_cuotas_vencidas():
    """
    Función para procesar cuotas vencidas y aplicar recargos
    Puede ser llamada por un cron job o task scheduler
    """
    try:
        hoy = timezone.now().date()
        cuotas_vencidas = Cuota.objects.filter(
            fecha_vencimiento__lt=hoy,
            pagada=False,
            concepto__aplica_recargo=True
        )
        
        contador = 0
        for cuota in cuotas_vencidas:
            recargo_anterior = cuota.recargo
            cuota.actualizar_recargo()
            
            if cuota.recargo != recargo_anterior:
                contador += 1
                logger.info(f"Recargo actualizado para cuota {cuota.id}: ${cuota.recargo}")
        
        logger.info(f"Procesadas {contador} cuotas vencidas con recargos actualizados")
        return contador
    
    except Exception as e:
        logger.error(f"Error al procesar cuotas vencidas: {e}")
        return 0

def limpiar_pagos_rechazados_antiguos():
    """
    Función para limpiar pagos rechazados muy antiguos
    """
    try:
        fecha_limite = timezone.now() - timezone.timedelta(days=90)
        pagos_antiguos = Pago.objects.filter(
            estado='RECHAZADO',
            fecha_verificacion__lt=fecha_limite
        )
        
        count = pagos_antiguos.count()
        if count > 0:
            # En lugar de eliminar, tal vez solo marcar como archivados
            logger.info(f"Encontrados {count} pagos rechazados antiguos para revisar")
        
        return count
    
    except Exception as e:
        logger.error(f"Error al limpiar pagos rechazados: {e}")
        return 0

def validar_integridad_financiera():
    """
    Función para validar la integridad de los datos financieros
    """
    errores = []
    
    try:
        # 1. Verificar cuotas sin vivienda
        cuotas_huerfanas = Cuota.objects.filter(vivienda__isnull=True).count()
        if cuotas_huerfanas > 0:
            errores.append(f"{cuotas_huerfanas} cuotas sin vivienda asignada")
        
        # 2. Verificar pagos sin vivienda
        pagos_huerfanos = Pago.objects.filter(vivienda__isnull=True).count()
        if pagos_huerfanos > 0:
            errores.append(f"{pagos_huerfanos} pagos sin vivienda asignada")
        
        # 3. Verificar PagoCuota inconsistentes
        from django.db import models
        pagos_cuota_inconsistentes = PagoCuota.objects.filter(
            models.Q(monto_aplicado__lte=0) |
            models.Q(monto_aplicado__gt=models.F('cuota__monto') + models.F('cuota__recargo'))
        ).count()
        if pagos_cuota_inconsistentes > 0:
            errores.append(f"{pagos_cuota_inconsistentes} relaciones PagoCuota inconsistentes")
        
        # 4. Verificar cuotas marcadas como pagadas pero sin pagos
        cuotas_pagadas_sin_pagos = Cuota.objects.filter(
            pagada=True
        ).exclude(
            id__in=PagoCuota.objects.filter(
                pago__estado='VERIFICADO'
            ).values_list('cuota_id', flat=True)
        ).count()
        if cuotas_pagadas_sin_pagos > 0:
            errores.append(f"{cuotas_pagadas_sin_pagos} cuotas marcadas como pagadas sin pagos verificados")
        
        if errores:
            logger.warning(f"Errores de integridad financiera encontrados: {errores}")
        else:
            logger.info("Validación de integridad financiera completada sin errores")
        
        return errores
    
    except Exception as e:
        logger.error(f"Error en validación de integridad financiera: {e}")
        return [f"Error en validación: {e}"]

# ===== CONFIGURACIÓN DE LOGGING =====

def setup_financial_logging():
    """
    Configurar logging específico para el módulo financiero
    """
    import logging.config
    
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '{asctime} {name} {levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'financial_file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': 'logs/financial.log',
                'formatter': 'detailed',
            },
        },
        'loggers': {
            'financiero.signals': {
                'handlers': ['financial_file'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    }
    
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
    except Exception:
        # Si no se puede configurar el logging, continuar sin errores
        pass

# Inicializar logging al importar el módulo
setup_financial_logging()