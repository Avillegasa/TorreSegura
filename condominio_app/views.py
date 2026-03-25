# views.py en condominio_app que condominio app es el que tiene el archivo settings.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
from datetime import datetime, timedelta
from viviendas.models import Edificio, Vivienda, Residente
from accesos.models import Visita, MovimientoResidente
from personal.models import Empleado, Asignacion
from financiero.models import Cuota, Pago
from usuarios.views import tiene_acceso_web
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied


@login_required
def dashboard(request):
    """
    Vista principal del dashboard con estadísticas del condominio
    Incluye filtrado por edificio y optimizaciones de consultas
    """
    user = request.user
    es_admin = hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Administrador'
    es_gerente = hasattr(user, 'rol') and user.rol and user.rol.nombre == 'Gerente'
    
    if not (es_admin or es_gerente):
        raise PermissionDenied
    
    # Obtener edificios según el rol
    if es_gerente and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
        edificios = Edificio.objects.filter(id=user.gerente.edificio.id)
    else:
        edificios = Edificio.objects.all()
    
    # Verificar que existan edificios en el sistema
    if not edificios.exists():
        messages.warning(request, "No hay edificios registrados en el sistema. Por favor, registre al menos un edificio para ver las estadísticas.")
        return render(request, 'dashboard_empty.html', {'edificios': edificios})
    
    # Obtener el edificio seleccionado (si existe)
    edificio_id = request.GET.get('edificio')
    edificio_seleccionado = None
    edificio_nombre = "Todos los edificios"
    
    # Gerente siempre forzado a su edificio
    if es_gerente and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
        edificio_id = str(user.gerente.edificio.id)
    
    # Validar y procesar el edificio seleccionado
    if edificio_id:
        try:
            edificio_seleccionado = int(edificio_id)
            edificio_obj = Edificio.objects.get(id=edificio_id)
            # Gerente no puede ver edificios que no le pertenecen
            if es_gerente and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
                if edificio_obj.id != user.gerente.edificio.id:
                    return redirect('dashboard')
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
    cache_key = f"dashboard_stats_{edificio_id or 'all'}_{user.id}"
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
        if edificio_id:
            total_personal = Empleado.objects.filter(
                activo=True,
                edificio_id=edificio_id
            ).count()
            total_asignaciones_pendientes = Asignacion.objects.filter(
                estado='PENDIENTE',
                edificio_id=edificio_id
            ).count()
        else:
            total_personal = Empleado.objects.filter(activo=True).count()
            total_asignaciones_pendientes = Asignacion.objects.filter(estado='PENDIENTE').count()
        
        # Estadísticas financieras
        cuotas_q = Cuota.objects.filter(vivienda__activo=True)
        pagos_q = Pago.objects.all()
        if edificio_id:
            cuotas_q = cuotas_q.filter(vivienda__edificio_id=edificio_id)
            pagos_q = pagos_q.filter(vivienda__edificio_id=edificio_id)

        fin_stats = cuotas_q.aggregate(
            cuotas_pendientes=Count('id', filter=Q(pagada=False)),
            cuotas_vencidas=Count('id', filter=Q(pagada=False, fecha_vencimiento__lt=timezone.now().date())),
            total_por_cobrar=Sum('monto', filter=Q(pagada=False)),
        )
        cuotas_pendientes_count = fin_stats['cuotas_pendientes'] or 0
        cuotas_vencidas_count = fin_stats['cuotas_vencidas'] or 0
        total_por_cobrar = fin_stats['total_por_cobrar'] or 0

        pagos_por_verificar = pagos_q.filter(estado='PENDIENTE').count()

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
            'cuotas_pendientes_count': cuotas_pendientes_count,
            'cuotas_vencidas_count': cuotas_vencidas_count,
            'total_por_cobrar': total_por_cobrar,
            'pagos_por_verificar': pagos_por_verificar,
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
    cuotas_pendientes_count = cached_stats.get('cuotas_pendientes_count', 0)
    cuotas_vencidas_count = cached_stats.get('cuotas_vencidas_count', 0)
    total_por_cobrar = cached_stats.get('total_por_cobrar', 0)
    pagos_por_verificar = cached_stats.get('pagos_por_verificar', 0)
    
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
    if edificio_id:
        ultimas_asignaciones = Asignacion.objects.filter(
            edificio_id=edificio_id
        ).select_related(
            'empleado__usuario', 'edificio', 'vivienda'
        ).order_by('-fecha_asignacion')[:5]
    else:
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
    
    # Pagos pendientes de verificacion (recientes)
    pagos_pendientes_q = Pago.objects.filter(estado='PENDIENTE')
    if edificio_id:
        pagos_pendientes_q = pagos_pendientes_q.filter(vivienda__edificio_id=edificio_id)
    ultimos_pagos_pendientes = (
        pagos_pendientes_q
        .select_related('vivienda', 'residente__usuario')
        .order_by('-fecha_pago', '-id')[:5]
    )

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
        # Financiero
        'cuotas_pendientes_count': cuotas_pendientes_count,
        'cuotas_vencidas_count': cuotas_vencidas_count,
        'total_por_cobrar': total_por_cobrar,
        'pagos_por_verificar': pagos_por_verificar,
        'ultimos_pagos_pendientes': ultimos_pagos_pendientes,
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


@login_required
def forzar_cambio_password(request):
    """
    Vista que obliga al residente a cambiar su contraseña temporal.
    Al completar, limpia las flags y envía email de confirmación.
    """
    if not request.user.debe_cambiar_password:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            user.debe_cambiar_password = False
            user.credenciales_expiran = None
            user.save(update_fields=['debe_cambiar_password', 'credenciales_expiran'])

            # Enviar email de confirmación
            try:
                send_mail(
                    subject='Contraseña actualizada - Torre Segura',
                    message=(
                        f'Hola {user.get_full_name() or user.username},\n\n'
                        'Tu contraseña ha sido actualizada exitosamente.\n'
                        'Ya puedes acceder al sistema con tu nueva contraseña.\n\n'
                        'Si no realizaste este cambio, contacta al administrador de inmediato.\n\n'
                        'Saludos,\nSistema Torre Segura'
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(request, '¡Contraseña actualizada correctamente! Ya puedes usar el sistema.')
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'forzar_cambio_password.html', {'form': form})


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Extiende el reset de contraseña para limpiar las flags de
    credenciales temporales cuando el residente cambia su contraseña.
    """
    template_name = 'password_reset_confirm.html'

    def form_valid(self, form):
        user = form.save()
        # Limpiar flags de credenciales temporales
        if getattr(user, 'debe_cambiar_password', False):
            user.debe_cambiar_password = False
            user.credenciales_expiran = None
            user.save(update_fields=['debe_cambiar_password', 'credenciales_expiran'])
        return super().form_valid(form)

