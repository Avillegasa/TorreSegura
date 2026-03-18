from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import CreateAPIView
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from .models import Alerta
from .serializers import AlertaSerializer, CrearAlertaSerializer

class AlertaCreateView(CreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = CrearAlertaSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(enviado_por=self.request.user)

class AlertaViewSet(ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        rol_nombre = getattr(getattr(user, 'rol', None), 'nombre', None)

        # Solo Admin y Gerente ven todas (filtradas); otros solo sus propias alertas
        if rol_nombre == 'Administrador':
            queryset = Alerta.objects.select_related('enviado_por', 'atendido_por')
        elif rol_nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
            from django.db.models import Q
            edificio = user.gerente.edificio
            queryset = Alerta.objects.select_related('enviado_por', 'atendido_por').filter(
                Q(enviado_por__residente__vivienda__edificio=edificio) |
                Q(enviado_por__vigilante__edificio=edificio) |
                Q(enviado_por__empleado__edificio=edificio) |
                Q(enviado_por__gerente__edificio=edificio)
            )
        else:
            queryset = Alerta.objects.select_related('enviado_por', 'atendido_por').filter(enviado_por=user)
        
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(enviado_por__id=user_id)
        return queryset.order_by('-fecha')
    
    def perform_create(self, serializer):
        serializer.save(enviado_por=self.request.user)
    
    def perform_update(self, serializer):
        # Solo Admin/Gerente pueden actualizar alertas de otros
        rol_nombre = getattr(getattr(self.request.user, 'rol', None), 'nombre', None)
        if rol_nombre not in ['Administrador', 'Gerente']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('No tienes permisos para actualizar alertas')
        serializer.save()
    
    def perform_destroy(self, instance):
        # Solo Admin puede eliminar alertas
        rol_nombre = getattr(getattr(self.request.user, 'rol', None), 'nombre', None)
        if rol_nombre != 'Administrador':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Solo el administrador puede eliminar alertas')
        instance.delete()

def _resolver_edificio_usuario(user):
    """Obtiene el edificio del usuario según su rol."""
    # Residente → vivienda → edificio
    if hasattr(user, 'residente') and user.residente and getattr(user.residente, 'vivienda', None):
        return user.residente.vivienda.edificio
    # Vigilante → edificio
    if hasattr(user, 'vigilante') and user.vigilante:
        return user.vigilante.edificio
    # Gerente → edificio
    if hasattr(user, 'gerente') and user.gerente:
        return user.gerente.edificio
    # Empleado → edificio
    if hasattr(user, 'empleado') and user.empleado:
        return user.empleado.edificio
    return None


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def crear_alerta(request):
    """
    Crear una nueva alerta. Auto-asigna el edificio del usuario si no se envía.
    """
    data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

    # Auto-asignar edificio si no viene en el request
    if not data.get('edificio'):
        edificio = _resolver_edificio_usuario(request.user)
        if edificio:
            data['edificio'] = edificio.id

    serializer = CrearAlertaSerializer(data=data)
    if serializer.is_valid():
        alerta = serializer.save(enviado_por=request.user)

        # Retornar la alerta completa con información del usuario
        response_serializer = AlertaSerializer(alerta)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def alertas_nuevas(request):
    """
    Endpoint de polling: retorna alertas del edificio del usuario creadas después de `since` (ISO timestamp).
    GET /api/v1/alertas/nuevas/?since=2026-03-18T12:00:00Z
    """
    since_str = request.query_params.get('since')
    if not since_str:
        return Response({'error': 'Parámetro "since" requerido (ISO timestamp)'}, status=status.HTTP_400_BAD_REQUEST)

    from django.utils.dateparse import parse_datetime
    since = parse_datetime(since_str)
    if not since:
        return Response({'error': 'Formato de fecha inválido. Use ISO 8601.'}, status=status.HTTP_400_BAD_REQUEST)

    # Hacer timezone-aware si es naive
    if timezone.is_naive(since):
        since = timezone.make_aware(since)

    user = request.user
    edificio = _resolver_edificio_usuario(user)

    if not edificio:
        return Response([], status=status.HTTP_200_OK)

    alertas = (
        Alerta.objects.filter(edificio=edificio, fecha__gt=since)
        .exclude(enviado_por=user)  # No notificar de tus propias alertas
        .select_related('enviado_por')
        .order_by('-fecha')
    )

    serializer = AlertaSerializer(alertas, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def mis_alertas(request):
    """
    Obtener todas las alertas del usuario autenticado
    """
    alertas = Alerta.objects.filter(enviado_por=request.user).order_by('-fecha')
    serializer = AlertaSerializer(alertas, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def actualizar_estado_alerta(request, pk):
    """
    Actualizar el estado de una alerta (solo para staff)
    """
    try:
        alerta = Alerta.objects.get(pk=pk)
        
        # Solo Administrador y Gerente pueden cambiar el estado
        if not (hasattr(request.user, 'rol') and request.user.rol and 
                request.user.rol.nombre in ['Administrador', 'Gerente']):
            return Response(
                {'error': 'No tienes permisos para actualizar alertas'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Gerente solo puede actuar sobre alertas de su edificio
        if request.user.rol.nombre == 'Gerente' and hasattr(request.user, 'gerente') and request.user.gerente and request.user.gerente.edificio:
            from django.db.models import Q
            edificio = request.user.gerente.edificio
            if not Alerta.objects.filter(pk=pk).filter(
                Q(enviado_por__residente__vivienda__edificio=edificio) |
                Q(enviado_por__vigilante__edificio=edificio) |
                Q(enviado_por__empleado__edificio=edificio) |
                Q(enviado_por__gerente__edificio=edificio)
            ).exists():
                return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        
        nuevo_estado = request.data.get('estado')
        if nuevo_estado in ['pendiente', 'en_proceso', 'resuelto']:
            alerta.estado = nuevo_estado
            if nuevo_estado in ['en_proceso', 'resuelto']:
                alerta.atendido_por = request.user
                alerta.fecha_atencion = timezone.now()
            alerta.save()
            
            serializer = AlertaSerializer(alerta)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Estado inválido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Alerta.DoesNotExist:
        return Response(
            {'error': 'Alerta no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@login_required
def lista_alertas(request):
    """
    Vista HTML para mostrar la lista de alertas en el dashboard
    """
    user = request.user
    rol_nombre = getattr(getattr(user, 'rol', None), 'nombre', None)
    if rol_nombre not in ['Administrador', 'Gerente']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    
    alertas = Alerta.objects.all().order_by('-fecha')

    # Gerente solo ve alertas de usuarios de su edificio
    user = request.user
    if hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
        from django.db.models import Q
        from viviendas.models import Edificio
        edificio = user.gerente.edificio
        alertas = alertas.filter(
            Q(enviado_por__residente__vivienda__edificio=edificio) |
            Q(enviado_por__vigilante__edificio=edificio) |
            Q(enviado_por__empleado__edificio=edificio) |
            Q(enviado_por__gerente__edificio=edificio)
        )
    
    # Filtrar por usuario si se especifica
    user_id = request.GET.get('user_id')
    if user_id:
        alertas = alertas.filter(enviado_por__id=user_id)
    
    # Calcular estadísticas
    alertas_pendientes = alertas.filter(estado='pendiente').count()
    alertas_proceso = alertas.filter(estado='en_proceso').count()
    alertas_resueltas = alertas.filter(estado='resuelto').count()
    
    context = {
        'alertas': alertas,
        'user': request.user,
        'alertas_pendientes': alertas_pendientes,
        'alertas_proceso': alertas_proceso,
        'alertas_resueltas': alertas_resueltas,
    }
    
    return render(request, 'alertas/lista_alertas.html', context)

@login_required
@require_http_methods(["GET"])
def alertas_nuevas_web(request):
    """
    Polling endpoint para la web: retorna alertas del edificio creadas después de `since`.
    """
    since_str = request.GET.get('since')
    if not since_str:
        return JsonResponse({'error': 'Parámetro "since" requerido'}, status=400)

    from django.utils.dateparse import parse_datetime
    since = parse_datetime(since_str)
    if not since:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    if timezone.is_naive(since):
        since = timezone.make_aware(since)

    user = request.user
    edificio = _resolver_edificio_usuario(user)

    alertas = Alerta.objects.filter(fecha__gt=since).exclude(enviado_por=user).order_by('-fecha')

    if edificio and not user.is_superuser:
        alertas = alertas.filter(edificio=edificio)

    data = []
    for a in alertas.select_related('enviado_por')[:20]:
        data.append({
            'id': a.id,
            'tipo': a.tipo,
            'descripcion': a.descripcion,
            'enviado_por': a.enviado_por.get_full_name() or a.enviado_por.username,
            'fecha': a.fecha.isoformat(),
            'estado': a.estado,
        })

    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["PUT"])
def cambiar_estado_web(request, pk):
    """
    Cambiar estado de alerta desde la web (usa autenticación de Django)
    """
    try:
        # Solo Administrador y Gerente pueden cambiar estados
        if not (hasattr(request.user, 'rol') and request.user.rol and 
                request.user.rol.nombre in ['Administrador', 'Gerente']):
            return JsonResponse(
                {'error': 'No tienes permisos para actualizar alertas'}, 
                status=403
            )
        
        # Obtener la alerta
        alerta = Alerta.objects.get(pk=pk)
        
        # Gerente solo puede cambiar alertas de su edificio
        if request.user.rol.nombre == 'Gerente' and hasattr(request.user, 'gerente') and request.user.gerente and request.user.gerente.edificio:
            from django.db.models import Q
            edificio = request.user.gerente.edificio
            if not Alerta.objects.filter(
                pk=pk
            ).filter(
                Q(enviado_por__residente__vivienda__edificio=edificio) |
                Q(enviado_por__vigilante__edificio=edificio) |
                Q(enviado_por__empleado__edificio=edificio) |
                Q(enviado_por__gerente__edificio=edificio)
            ).exists():
                return JsonResponse({'error': 'No autorizado'}, status=403)
        
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
    except Exception:
        return JsonResponse(
            {'error': 'Error interno del servidor'}, 
            status=500
        )