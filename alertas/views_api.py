# Agregar estos imports al inicio del archivo views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Alerta
import json

# Agregar esta vista al final del archivo views.py
@login_required
@require_http_methods(["PUT"])
def cambiar_estado_web(request, pk):
    """
    Cambiar estado de alerta desde la web (usa autenticación de Django)
    """
    try:
        # Solo staff puede cambiar estados
        if not request.user.is_staff:
            return JsonResponse(
                {'error': 'No tienes permisos para actualizar alertas'}, 
                status=403
            )
        
        # Obtener la alerta
        alerta = Alerta.objects.get(pk=pk)
        
        # Parsear el JSON del body
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        # Validar estado
        if nuevo_estado not in ['pendiente', 'en_proceso', 'resuelto']:
            return JsonResponse(
                {'error': 'Estado inválido'}, 
                status=400
            )
        
        # Actualizar alerta
        alerta.estado = nuevo_estado
        if nuevo_estado in ['en_proceso', 'resuelto']:
            alerta.atendido_por = request.user
            alerta.fecha_atencion = timezone.now()
        alerta.save()
        
        # Preparar respuesta
        response_data = {
            'id': alerta.id,
            'estado': alerta.estado,
            'atendido_por_info': None
        }
        
        if alerta.atendido_por:
            response_data['atendido_por_info'] = {
                'username': alerta.atendido_por.username,
                'first_name': alerta.atendido_por.first_name,
                'last_name': alerta.atendido_por.last_name,
            }
        
        return JsonResponse(response_data)
        
    except Alerta.DoesNotExist:
        return JsonResponse(
            {'error': 'Alerta no encontrada'}, 
            status=404
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Datos JSON inválidos'}, 
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Error interno: {str(e)}'}, 
            status=500
        )