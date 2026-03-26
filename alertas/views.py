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
from django.db.models import Q
from datetime import datetime
import json
from .models import Alerta, Anuncio, OpcionVoto, Voto
from .serializers import AlertaSerializer, CrearAlertaSerializer, AnuncioSerializer, CrearAnuncioSerializer


def _resolver_edificio_usuario(user):
    """Devuelve el edificio asociado al usuario según su rol."""
    if hasattr(user, 'residente') and user.residente and user.residente.vivienda:
        return user.residente.vivienda.edificio
    if hasattr(user, 'vigilante') and user.vigilante:
        return user.vigilante.edificio
    if hasattr(user, 'gerente') and user.gerente:
        return user.gerente.edificio
    if hasattr(user, 'empleado') and user.empleado:
        return user.empleado.edificio
    return None

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

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def crear_alerta(request):
    """
    Crear una nueva alerta (auto-asigna edificio del usuario)
    """
    serializer = CrearAlertaSerializer(data=request.data)
    if serializer.is_valid():
        edificio = _resolver_edificio_usuario(request.user)
        alerta = serializer.save(enviado_por=request.user, edificio=edificio)

        response_serializer = AlertaSerializer(alerta)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


# ─── Polling de alertas nuevas ───────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def alertas_nuevas(request):
    """
    Endpoint de polling para la app móvil (JWT).
    Devuelve alertas del edificio del usuario creadas después de ?since=<ISO>.
    Solo para Vigilante y Gerente.
    """
    rol_nombre = getattr(getattr(request.user, 'rol', None), 'nombre', None)
    if rol_nombre not in ('Vigilante', 'Gerente'):
        return Response([])

    since = request.query_params.get('since')
    if not since:
        return Response([])

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return Response({'error': 'Formato de fecha inválido'}, status=status.HTTP_400_BAD_REQUEST)

    edificio = _resolver_edificio_usuario(request.user)
    if not edificio:
        return Response([])

    nuevas = (
        Alerta.objects
        .filter(edificio=edificio, fecha__gt=since_dt)
        .exclude(enviado_por=request.user)
        .select_related('enviado_por')
        .order_by('-fecha')[:20]
    )
    serializer = AlertaSerializer(nuevas, many=True)
    return Response(serializer.data)


@login_required
def alertas_nuevas_web(request):
    """
    Endpoint de polling para el dashboard web (sesión Django).
    Devuelve alertas creadas después de ?since=<ISO>.
    Solo para Administrador y Gerente.
    """
    rol_nombre = getattr(getattr(request.user, 'rol', None), 'nombre', None)
    if rol_nombre not in ('Administrador', 'Gerente'):
        return JsonResponse([], safe=False)

    since = request.GET.get('since')
    if not since:
        return JsonResponse([], safe=False)

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    alertas = Alerta.objects.filter(fecha__gt=since_dt).select_related('enviado_por', 'atendido_por')

    # Gerente: solo su edificio
    if rol_nombre == 'Gerente' and hasattr(request.user, 'gerente') and request.user.gerente and request.user.gerente.edificio:
        edificio = request.user.gerente.edificio
        alertas = alertas.filter(
            Q(enviado_por__residente__vivienda__edificio=edificio) |
            Q(enviado_por__vigilante__edificio=edificio) |
            Q(enviado_por__empleado__edificio=edificio) |
            Q(enviado_por__gerente__edificio=edificio)
        )

    alertas = alertas.order_by('-fecha')[:20]

    data = []
    for a in alertas:
        data.append({
            'id': a.id,
            'tipo': a.tipo,
            'descripcion': a.descripcion,
            'estado': a.estado,
            'fecha': a.fecha.isoformat(),
            'enviado_por': a.enviado_por.get_full_name() or a.enviado_por.username,
        })

    return JsonResponse(data, safe=False)


# ─── Alertas del edificio (para app, todos los roles) ─────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def alertas_edificio(request):
    """
    Lista las alertas del edificio del usuario autenticado.
    Disponible para todos los roles (Residente, Vigilante, Gerente).
    """
    edificio = _resolver_edificio_usuario(request.user)
    if not edificio:
        return Response([])

    alertas = (
        Alerta.objects
        .filter(edificio=edificio)
        .select_related('enviado_por', 'atendido_por')
        .order_by('-fecha')[:50]
    )
    serializer = AlertaSerializer(alertas, many=True)
    return Response(serializer.data)


# ─── Anuncios del condominio ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def listar_anuncios(request):
    """
    Lista los anuncios del edificio del usuario.
    """
    edificio = _resolver_edificio_usuario(request.user)
    if not edificio:
        return Response([])

    anuncios = (
        Anuncio.objects
        .filter(edificio=edificio, activo=True)
        .select_related('autor')
        .prefetch_related('opciones__votos__usuario')
        .order_by('-fijado', '-fecha_creacion')[:50]
    )
    serializer = AnuncioSerializer(anuncios, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def crear_anuncio(request):
    """
    Crear un nuevo anuncio. Gerente y Residente pueden crear.
    Si es_votacion=True, se crean también las opciones de voto.
    Solo Gerente/Admin pueden crear votaciones.
    """
    serializer = CrearAnuncioSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    edificio = _resolver_edificio_usuario(request.user)
    if not edificio:
        return Response(
            {'error': 'No tienes un edificio asignado.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    es_votacion = data.get('es_votacion', False)
    opciones_texto = data.get('opciones', [])

    # Solo Gerente/Admin puede crear votaciones
    if es_votacion:
        rol_nombre = getattr(getattr(request.user, 'rol', None), 'nombre', None)
        if rol_nombre not in ('Administrador', 'Gerente'):
            return Response(
                {'error': 'Solo el gerente o administrador puede crear votaciones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if len(opciones_texto) < 2:
            return Response(
                {'error': 'Una votación necesita al menos 2 opciones.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    anuncio = Anuncio.objects.create(
        titulo=data['titulo'],
        contenido=data['contenido'],
        categoria=data.get('categoria', 'general'),
        autor=request.user,
        edificio=edificio,
        es_votacion=es_votacion,
        voto_anonimo=data.get('voto_anonimo', False),
        fecha_cierre_votacion=data.get('fecha_cierre_votacion'),
    )

    # Crear opciones de voto
    if es_votacion and opciones_texto:
        for i, texto in enumerate(opciones_texto):
            OpcionVoto.objects.create(anuncio=anuncio, texto=texto.strip(), orden=i)

    response_serializer = AnuncioSerializer(anuncio, context={'request': request})
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def votar_anuncio(request, pk):
    """
    Registrar un voto en un anuncio.
    Body: { "opcion_id": 5 }
    Un usuario solo puede votar una vez por anuncio.
    """
    try:
        anuncio = Anuncio.objects.get(pk=pk, activo=True)
    except Anuncio.DoesNotExist:
        return Response({'error': 'Anuncio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if not anuncio.es_votacion:
        return Response({'error': 'Este anuncio no tiene votación.'}, status=status.HTTP_400_BAD_REQUEST)

    if not anuncio.votacion_abierta:
        return Response({'error': 'La votación ya cerró.'}, status=status.HTTP_400_BAD_REQUEST)

    opcion_id = request.data.get('opcion_id')
    if not opcion_id:
        return Response({'error': 'Debes seleccionar una opción.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        opcion = OpcionVoto.objects.get(pk=opcion_id, anuncio=anuncio)
    except OpcionVoto.DoesNotExist:
        return Response({'error': 'Opción no válida.'}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar si ya votó en este anuncio (cualquier opción)
    voto_existente = Voto.objects.filter(
        opcion__anuncio=anuncio, usuario=request.user
    ).first()

    if voto_existente:
        # Cambiar voto
        voto_existente.opcion = opcion
        voto_existente.save(update_fields=['opcion'])
    else:
        Voto.objects.create(opcion=opcion, usuario=request.user)

    # Devolver anuncio actualizado
    anuncio.refresh_from_db()
    response_serializer = AnuncioSerializer(anuncio, context={'request': request})
    return Response(response_serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def eliminar_anuncio(request, pk):
    """
    Eliminar un anuncio. Solo el autor o Gerente/Admin pueden eliminar.
    """
    try:
        anuncio = Anuncio.objects.get(pk=pk)
    except Anuncio.DoesNotExist:
        return Response({'error': 'Anuncio no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    rol_nombre = getattr(getattr(request.user, 'rol', None), 'nombre', None)
    if anuncio.autor != request.user and rol_nombre not in ('Administrador', 'Gerente'):
        return Response({'error': 'No tienes permisos.'}, status=status.HTTP_403_FORBIDDEN)

    anuncio.activo = False
    anuncio.save(update_fields=['activo'])
    return Response({'mensaje': 'Anuncio eliminado.'}, status=status.HTTP_200_OK)