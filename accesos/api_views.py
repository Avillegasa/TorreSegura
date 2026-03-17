# accesos/api_views.py (o agregar a views.py)
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .models import Visita
from usuarios.models import Gerente
@login_required
def api_visitas_historial(request):
    """
    API endpoint para obtener el historial de visitas (visitas completadas)
    Filtrado por edificio para gerentes
    """
    user = request.user
    
    # Determinar el edificio del gerente
    edificio_gerente = None
    
    # Si es administrador, puede ver todo
    if not (user.is_superuser or user.groups.filter(name='Administrador').exists()):
        if user.groups.filter(name='Gerente').exists():
            try:
                # Ajusta esta importación según tu estructura de modelos
                
                gerente_edificio = Gerente.objects.get(usuario=user)
                edificio_gerente = gerente_edificio.edificio
            except Gerente.DoesNotExist:
                return JsonResponse({'error': 'No tiene un edificio asignado como gerente'}, status=403)
        else:
            return JsonResponse({'error': 'No tiene permisos para acceder a esta información'}, status=403)
    
    # Construir queryset base - solo visitas históricas (con salida registrada)
    queryset = Visita.objects.filter(
        fecha_hora_salida__isnull=False
    ).select_related(
        'vivienda_destino__edificio',
        'residente_autoriza__usuario'
    )
    
    # Filtrar por edificio si es gerente
    if edificio_gerente:
        queryset = queryset.filter(vivienda_destino__edificio=edificio_gerente)
    
    # Ordenar por fecha de salida más reciente y limitar resultados
    queryset = queryset.order_by('-fecha_hora_salida')[:100]  # Limitar a las últimas 100 visitas
    
    # Construir respuesta JSON
    visitas_data = []
    for visita in queryset:
        visitas_data.append({
            'id': visita.id,
            'nombre_visitante': visita.nombre_visitante,
            'documento_visitante': visita.documento_visitante,
            'vivienda_destino': str(visita.vivienda_destino),
            'residente_autoriza': str(visita.residente_autoriza),
            'fecha_hora_entrada': visita.fecha_hora_entrada.isoformat(),
            'fecha_hora_salida': visita.fecha_hora_salida.isoformat(),
            'motivo': visita.motivo or ''
        })
    
    return JsonResponse(visitas_data, safe=False)