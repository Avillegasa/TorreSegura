# views.py en condominio_app que condominio app es el que tiene el archivo settings.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from viviendas.models import Edificio, Vivienda, Residente
from accesos.models import Visita, MovimientoResidente
from personal.models import Empleado, Asignacion
from usuarios.views import tiene_acceso_web
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings


def test_email(request):
    """Vista temporal para probar email en producción"""
    try:
        result = send_mail(
            'Prueba de email desde Railway',
            'Este es un email de prueba desde la aplicación en producción',
            settings.DEFAULT_FROM_EMAIL,
            ['apolacadilan@gmail.com'],
            fail_silently=False
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Email enviado exitosamente. Resultado: {result}',
            'email_backend': settings.EMAIL_BACKEND,
            'email_host': settings.EMAIL_HOST,
            'email_from': settings.DEFAULT_FROM_EMAIL
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'email_backend': getattr(settings, 'EMAIL_BACKEND', 'No configurado'),
            'email_host': getattr(settings, 'EMAIL_HOST', 'No configurado'),
        })
    
@login_required
def dashboard(request):
    """
    Vista principal del dashboard con estadísticas del condominio
    Incluye filtrado por edificio y optimizaciones de consultas
    """
    # Obtener todos los edificios para el selector
    edificios = Edificio.objects.all()
    
    # Verificar que existan edificios en el sistema
    if not edificios.exists():
        messages.warning(request, "No hay edificios registrados en el sistema. Por favor, registre al menos un edificio para ver las estadísticas.")
        return render(request, 'dashboard_empty.html', {'edificios': edificios})
    
    # Obtener el edificio seleccionado (si existe)
    edificio_id = request.GET.get('edificio')
    edificio_seleccionado = None
    edificio_nombre = "Todos los edificios"
    
    # Validar y procesar el edificio seleccionado
    if edificio_id:
        try:
            edificio_seleccionado = int(edificio_id)
            edificio_obj = Edificio.objects.get(id=edificio_id)
            edificio_nombre = edificio_obj.nombre
            viviendas = Vivienda.objects.filter(edificio_id=edificio_id, activo=True)
        except (ValueError, Edificio.DoesNotExist):
            messages.error(request, "El edificio seleccionado no es válido.")
            return redirect('dashboard')
    else:
        viviendas = Vivienda.objects.filter(activo=True)
        edificio_seleccionado = None
    
    # Verificar si existen viviendas
    if not viviendas.exists():
        messages.info(request, f"No hay viviendas registradas en {edificio_nombre}.")
    
    # Usar caché para estadísticas (5 minutos)
    cache_key = f"dashboard_stats_{edificio_id or 'all'}"
    cached_stats = cache.get(cache_key)
    
    if cached_stats is None:
        # Estadísticas de viviendas optimizadas en una sola consulta
        vivienda_stats = viviendas.aggregate(
            total=Count('id'),
            ocupadas=Count('id', filter=Q(estado='OCUPADO')),
            desocupadas=Count('id', filter=Q(estado='DESOCUPADO')),
            mantenimiento=Count('id', filter=Q(estado='MANTENIMIENTO'))
        )
        
        total_viviendas = vivienda_stats['total']
        viviendas_ocupadas = vivienda_stats['ocupadas']
        viviendas_desocupadas = vivienda_stats['desocupadas']
        viviendas_mantenimiento = vivienda_stats['mantenimiento']
        
        # Calcular porcentaje de ocupación (evitando división por cero)
        if total_viviendas > 0:
            porcentaje_ocupacion = round((viviendas_ocupadas / total_viviendas) * 100, 1)
        else:
            porcentaje_ocupacion = 0
        
        # Estadísticas de residentes
        if edificio_id:
            residentes_query = Residente.objects.filter(
                vivienda__edificio_id=edificio_id, 
                activo=True,
                vivienda__activo=True
            )
        else:
            residentes_query = Residente.objects.filter(
                activo=True,
                vivienda__activo=True
            )
        
        # Estadísticas de residentes optimizadas
        residente_stats = residentes_query.aggregate(
            total=Count('id'),
            propietarios=Count('id', filter=Q(es_propietario=True)),
            inquilinos=Count('id', filter=Q(es_propietario=False))
        )
        
        total_residentes = residente_stats['total']
        propietarios_count = residente_stats['propietarios']
        inquilinos_count = residente_stats['inquilinos']
        
        # Estadísticas de visitas
        if edificio_id:
            visitas_activas = Visita.objects.filter(
                vivienda_destino__edificio_id=edificio_id,
                vivienda_destino__activo=True,
                fecha_hora_salida__isnull=True
            ).count()
        else:
            visitas_activas = Visita.objects.filter(
                vivienda_destino__activo=True,
                fecha_hora_salida__isnull=True
            ).count()
        
        # Estadísticas de personal
        total_personal = Empleado.objects.filter(activo=True).count()
        
        # Asignaciones pendientes
        total_asignaciones_pendientes = Asignacion.objects.filter(estado='PENDIENTE').count()
        
        # Guardar en caché por 5 minutos
        cached_stats = {
            'total_viviendas': total_viviendas,
            'viviendas_ocupadas': viviendas_ocupadas,
            'viviendas_desocupadas': viviendas_desocupadas,
            'viviendas_mantenimiento': viviendas_mantenimiento,
            'porcentaje_ocupacion': porcentaje_ocupacion,
            'total_residentes': total_residentes,
            'propietarios_count': propietarios_count,
            'inquilinos_count': inquilinos_count,
            'visitas_activas': visitas_activas,
            'total_personal': total_personal,
            'total_asignaciones_pendientes': total_asignaciones_pendientes,
        }
        cache.set(cache_key, cached_stats, 300)  # 5 minutos
    
    # Extraer estadísticas del caché
    total_viviendas = cached_stats['total_viviendas']
    viviendas_ocupadas = cached_stats['viviendas_ocupadas']
    viviendas_desocupadas = cached_stats['viviendas_desocupadas']
    viviendas_mantenimiento = cached_stats['viviendas_mantenimiento']
    porcentaje_ocupacion = cached_stats['porcentaje_ocupacion']
    total_residentes = cached_stats['total_residentes']
    propietarios_count = cached_stats['propietarios_count']
    inquilinos_count = cached_stats['inquilinos_count']
    visitas_activas = cached_stats['visitas_activas']
    total_personal = cached_stats['total_personal']
    total_asignaciones_pendientes = cached_stats['total_asignaciones_pendientes']
    
    # Obtener datos recientes (no cacheados para mostrar información actualizada)
    # Últimas visitas
    if edificio_id:
        ultimas_visitas = Visita.objects.filter(
            vivienda_destino__edificio_id=edificio_id,
            vivienda_destino__activo=True
        ).select_related('vivienda_destino', 'vivienda_destino__edificio').order_by('-fecha_hora_entrada')[:5]
    else:
        ultimas_visitas = Visita.objects.filter(
            vivienda_destino__activo=True
        ).select_related('vivienda_destino', 'vivienda_destino__edificio').order_by('-fecha_hora_entrada')[:5]
    
    # Últimas asignaciones
    ultimas_asignaciones = Asignacion.objects.select_related(
        'empleado__usuario', 'edificio', 'vivienda'
    ).order_by('-fecha_asignacion')[:5]
    
    # Últimos movimientos de residentes
    if edificio_id:
        ultimos_movimientos = MovimientoResidente.objects.filter(
            residente__vivienda__edificio_id=edificio_id,
            residente__activo=True,
            residente__vivienda__activo=True
        ).select_related(
            'residente__usuario', 'residente__vivienda'
        ).order_by('-fecha_hora_entrada', '-fecha_hora_salida')[:5]
    else:
        ultimos_movimientos = MovimientoResidente.objects.filter(
            residente__activo=True,
            residente__vivienda__activo=True
        ).select_related(
            'residente__usuario', 'residente__vivienda'
        ).order_by('-fecha_hora_entrada', '-fecha_hora_salida')[:5]
    
    # Preparar contexto para el template
    context = {
        'viviendas_ocupadas': viviendas_ocupadas or 0,
        'viviendas_desocupadas': viviendas_desocupadas or 0,
        'viviendas_mantenimiento': viviendas_mantenimiento or 0,
        'edificios': edificios,
        'edificio_seleccionado': edificio_seleccionado,
        'edificio_nombre': edificio_nombre,
        'total_viviendas': total_viviendas,
        'porcentaje_ocupacion': porcentaje_ocupacion,
        'total_residentes': total_residentes,
        'propietarios_count': propietarios_count,
        'inquilinos_count': inquilinos_count,
        'visitas_activas': visitas_activas,
        'ultimas_visitas': ultimas_visitas,
        'ultimos_movimientos': ultimos_movimientos,
        'total_personal': total_personal,
        'total_asignaciones_pendientes': total_asignaciones_pendientes,
        'ultimas_asignaciones': ultimas_asignaciones,
    }
    
    return render(request, 'dashboard.html', context)

def home(request):
    """
    Vista de la página de inicio
    Redirige al dashboard si el usuario está autenticado
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

@login_required
def perfil(request):
    """
    Vista del perfil del usuario
    """
    return render(request, 'perfil.html', {'usuario': request.user})

def handler404(request, exception):
    """
    Manejador personalizado para errores 404
    """
    return render(request, '404.html', status=404)

def handler500(request):
    """
    Manejador personalizado para errores 500
    """
    return render(request, '500.html', status=500)

