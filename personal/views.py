# personal/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from uuid import uuid4
from usuarios.models import Usuario
from django.contrib.auth.mixins import UserPassesTestMixin
from .forms import PersonalCompleteForm
from usuarios.views import AccesoWebPermitidoMixin
from .models import Puesto, Empleado, Asignacion, ComentarioAsignacion
from .forms import PuestoForm, EmpleadoForm, AsignacionForm, ComentarioAsignacionForm, AsignacionFiltroForm
from viviendas.models import Vivienda
from django.core.exceptions import ValidationError

class PuestoListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Puesto
    template_name = 'personal/puesto_list.html'
    context_object_name = 'puestos'

class PuestoCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Puesto
    form_class = PuestoForm
    template_name = 'personal/puesto_form.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Puesto creado exitosamente.')
        return super().form_valid(form)

class PuestoUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Puesto
    form_class = PuestoForm
    template_name = 'personal/puesto_form.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Puesto actualizado exitosamente.')
        return super().form_valid(form)

class PuestoDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = Puesto
    template_name = 'personal/puesto_confirm_delete.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, 'Puesto eliminado exitosamente.')
        except Exception as e:
            messages.error(self.request, f'No se pudo eliminar el puesto: {str(e)}')
            return redirect('puesto-list')
        return redirect(self.success_url)

# Vistas para Empleados
class EmpleadoListView(LoginRequiredMixin, ListView):
    model = Empleado
    template_name = 'personal/empleado_list.html'
    context_object_name = 'empleados'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('usuario', 'puesto')
        
        # Filtrar por puesto si se especifica
        puesto_id = self.request.GET.get('puesto')
        if puesto_id:
            try:
                queryset = queryset.filter(puesto_id=int(puesto_id))
            except (ValueError, TypeError):
                pass
        
        # Filtrar por estado (activo/inactivo)
        estado = self.request.GET.get('estado')
        if estado:
            activo = estado == 'activo'
            queryset = queryset.filter(activo=activo)
            
        # Filtrar por búsqueda de texto
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(usuario__first_name__icontains=query) | 
                Q(usuario__last_name__icontains=query) |
                Q(puesto__nombre__icontains=query)
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['puestos'] = Puesto.objects.all()
        context['filtro_puesto'] = self.request.GET.get('puesto', '')
        context['filtro_estado'] = self.request.GET.get('estado', '')
        context['query'] = self.request.GET.get('q', '')
        return context


class EmpleadoCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'personal/empleado_form.html'
    success_url = reverse_lazy('empleado-list')
    def form_valid(self, form):
        puesto = form.cleaned_data.get('puesto')

        if puesto and puesto.nombre.lower() == "personal":
            # Crear un usuario fantasma para personal (sin acceso al sistema)
            nombres = form.cleaned_data.get('usuario').first_name
            apellidos = form.cleaned_data.get('usuario').last_name
            usuario = Usuario.objects.create(
                username=f"personal_{uuid4().hex[:6]}",
                first_name=nombres or "Empleado",
                last_name=apellidos or "Condominio",
                is_active=False
            )
            usuario.set_unusable_password()
            usuario.save()
            form.instance.usuario = usuario

        messages.success(self.request, 'Empleado creado exitosamente.')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

class EmpleadoUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'personal/empleado_form.html'
    success_url = reverse_lazy('empleado-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Empleado actualizado exitosamente.')
        return super().form_valid(form)

class EmpleadoDetailView(LoginRequiredMixin, DetailView):
    model = Empleado
    template_name = 'personal/empleado_detail.html'
    context_object_name = 'empleado'
    
    def get_queryset(self):
        return super().get_queryset().select_related('usuario', 'puesto')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener las asignaciones del empleado con optimización
        empleado = self.get_object()
        context['asignaciones'] = Asignacion.objects.filter(
            empleado=empleado
        ).select_related('edificio', 'vivienda').order_by('-fecha_asignacion')[:10]
        
        # Estadísticas optimizadas
        asignaciones_qs = Asignacion.objects.filter(empleado=empleado)
        context['total_asignaciones'] = asignaciones_qs.count()
        context['asignaciones_pendientes'] = asignaciones_qs.filter(estado='PENDIENTE').count()
        context['asignaciones_en_progreso'] = asignaciones_qs.filter(estado='EN_PROGRESO').count()
        context['asignaciones_completadas'] = asignaciones_qs.filter(estado='COMPLETADA').count()
        
        return context

@login_required
def empleado_change_state(request, pk):
    """Vista para activar/desactivar un empleado"""
    empleado = get_object_or_404(Empleado, pk=pk)
    
    # ✅ CORRECCIÓN: Verificar permisos de administrador
    if not hasattr(request.user, 'rol') or request.user.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para realizar esta acción.', extra_tags='danger')
        return redirect('empleado-list')
    
    if request.method == 'POST':
        # Cambiar el estado del empleado
        empleado.activo = not empleado.activo
        empleado.save()
        
        # Cambiar también el estado del usuario asociado
        empleado.usuario.is_active = empleado.activo
        empleado.usuario.save()
        
        estado = "activado" if empleado.activo else "desactivado"
        messages.success(
            request, 
            f'El empleado {empleado.usuario.first_name} {empleado.usuario.last_name} ha sido {estado} exitosamente.'
        )
        return redirect('empleado-list')
    
    return render(request, 'personal/empleado_change_state.html', {'empleado': empleado})

# Vistas para Asignaciones
class AsignacionListView(LoginRequiredMixin, ListView):
    model = Asignacion
    template_name = 'personal/asignacion_list.html'
    context_object_name = 'asignaciones'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'empleado__usuario', 'empleado__puesto', 'edificio', 'vivienda', 'asignado_por'
        )
        
        # Crear formulario de filtro
        self.filtro_form = AsignacionFiltroForm(self.request.GET or None)
        
        # Aplicar filtros si el formulario es válido
        if self.filtro_form.is_valid():
            data = self.filtro_form.cleaned_data
            
            if data.get('empleado'):
                queryset = queryset.filter(empleado=data['empleado'])
            
            if data.get('tipo'):
                queryset = queryset.filter(tipo=data['tipo'])
            
            if data.get('estado'):
                queryset = queryset.filter(estado=data['estado'])
            
            if data.get('edificio'):
                queryset = queryset.filter(edificio=data['edificio'])
            
            if data.get('fecha_desde'):
                queryset = queryset.filter(fecha_inicio__gte=data['fecha_desde'])
            
            if data.get('fecha_hasta'):
                queryset = queryset.filter(fecha_inicio__lte=data['fecha_hasta'])
        
        # Filtro adicional para usuarios que son empleados (ver solo sus propias asignaciones)
        if hasattr(self.request.user, 'empleado') and self.request.user.rol.nombre != 'Administrador':
            queryset = queryset.filter(empleado=self.request.user.empleado)
        
        return queryset.order_by('-fecha_asignacion')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = self.filtro_form
        
        # Estadísticas para el dashboard
        queryset = self.get_queryset()
        context['total_asignaciones'] = queryset.count()
        context['asignaciones_pendientes'] = queryset.filter(estado='PENDIENTE').count()
        context['asignaciones_en_progreso'] = queryset.filter(estado='EN_PROGRESO').count()
        context['asignaciones_completadas'] = queryset.filter(estado='COMPLETADA').count()
        
        return context

class AsignacionCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Asignacion
    form_class = AsignacionForm
    template_name = 'personal/asignacion_form.html'
    success_url = reverse_lazy('asignacion-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación creada exitosamente.')
        return super().form_valid(form)

class AsignacionUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Asignacion
    form_class = AsignacionForm
    template_name = 'personal/asignacion_form.html'
    success_url = reverse_lazy('asignacion-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación actualizada exitosamente.')
        return super().form_valid(form)

class AsignacionDetailView(LoginRequiredMixin, DetailView):
    model = Asignacion
    template_name = 'personal/asignacion_detail.html'
    context_object_name = 'asignacion'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'empleado__usuario', 'empleado__puesto', 'edificio', 'vivienda', 'asignado_por'
        ).prefetch_related('comentarios__usuario')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Añadir el formulario de comentarios
        context['comentario_form'] = ComentarioAsignacionForm()
        # Obtener los comentarios para esta asignación
        context['comentarios'] = self.object.comentarios.select_related('usuario').order_by('-fecha')
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar el envío del formulario de comentarios"""
        self.object = self.get_object()
        form = ComentarioAsignacionForm(request.POST)
        
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.asignacion = self.object
            comentario.usuario = request.user
            comentario.save()
            messages.success(request, 'Comentario añadido exitosamente.')
        else:
            messages.error(request, 'Error al agregar el comentario.')
        
        return redirect('asignacion-detail', pk=self.object.pk)

@login_required
def cambiar_estado_asignacion(request, pk):
    """Vista para cambiar el estado de una asignación"""
    asignacion = get_object_or_404(Asignacion, pk=pk)
    
    # ✅ CORRECCIÓN: Verificar permisos
    if not hasattr(request.user, 'rol') or request.user.rol.nombre != 'Administrador':
        # Permitir que el empleado asignado también pueda cambiar algunos estados
        if not (hasattr(request.user, 'empleado') and request.user.empleado == asignacion.empleado):
            messages.error(request, 'No tienes permisos para cambiar el estado de esta asignación.', extra_tags='danger')
            return redirect('asignacion-detail', pk=asignacion.pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in [estado[0] for estado in Asignacion.ESTADOS]:
            # Guardar el estado anterior para el mensaje
            estado_anterior = asignacion.get_estado_display()
            
            # Actualizar el estado
            asignacion.estado = nuevo_estado
            asignacion.save()
            
            # Añadir un comentario automático sobre el cambio de estado
            ComentarioAsignacion.objects.create(
                asignacion=asignacion,
                usuario=request.user,
                comentario=f"Estado cambiado de '{estado_anterior}' a '{asignacion.get_estado_display()}'."
            )
            
            messages.success(request, f'Estado de la asignación cambiado a {asignacion.get_estado_display()}.')
        else:
            messages.error(request, 'Estado no válido.')
        
        return redirect('asignacion-detail', pk=asignacion.pk)
    
    return render(request, 'personal/cambiar_estado_asignacion.html', {
        'asignacion': asignacion,
        'estados': Asignacion.ESTADOS,
    })

# CORRECCIÓN: API mejorada con manejo de errores
@login_required
def viviendas_por_edificio_api(request):
    edificio_id = request.GET.get('edificio_id')
    
    if not edificio_id:
        return JsonResponse({'error': 'ID de edificio no proporcionado'}, status=400)
    
    try:
        edificio_id = int(edificio_id)
        viviendas = Vivienda.objects.filter(
            edificio_id=edificio_id, 
            activo=True
        ).values('id', 'numero', 'piso').order_by('piso', 'numero')
        
        return JsonResponse(list(viviendas), safe=False)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'ID de edificio inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    
class GerenteAccesoMixin(UserPassesTestMixin):
    """
    Mixin para verificar que el usuario sea Gerente o Administrador
    """
    def test_func(self):
        return (
            self.request.user.is_authenticated and
            hasattr(self.request.user, 'rol') and
            self.request.user.rol is not None and
            self.request.user.rol.nombre in ['Administrador', 'Gerente']
        )

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permisos para acceder a esta sección.")
        return redirect('empleado-list')

# REEMPLAZA la clase PersonalCreateView en personal/views.py

class PersonalCreateView(LoginRequiredMixin, GerenteAccesoMixin, CreateView):
    """
    Vista específica para que Gerentes puedan crear personal desde cero
    Combina la creación de Usuario y Empleado en una sola operación
    """
    model = Empleado
    form_class = PersonalCompleteForm
    template_name = 'personal/personal_create.html'
    success_url = reverse_lazy('empleado-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user
        # NO pasar 'instance' porque vamos a crear desde cero
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs

    def form_valid(self, form):
        try:
            # Validar que el formulario sea válido antes de proceder
            if not form.is_valid():
                return self.form_invalid(form)
            
            # Usar el método del formulario para crear usuario y empleado
            empleado = form.crear_usuario_y_empleado(creado_por=self.request.user)
            
            # Mensaje de éxito personalizado
            messages.success(
                self.request, 
                f'Personal {empleado.usuario.first_name} {empleado.usuario.last_name} '
                f'creado exitosamente en el puesto de {empleado.puesto.nombre}.'
            )
            
            # Logging para auditoría
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Personal creado por {self.request.user.username}: "
                f"{empleado.usuario.first_name} {empleado.usuario.last_name} "
                f"({empleado.puesto.nombre})"
            )
            
            return redirect(self.success_url)
            
        except ValidationError as e:
            messages.error(self.request, f"Error de validación: {str(e)}")
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al crear personal: {str(e)}")
            
            messages.error(
                self.request, 
                f"Error al crear el personal: {str(e)}"
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, 
            "Por favor corrige los errores en el formulario."
        )
        # Debug: imprimir errores en consola
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Errores del formulario: {form.errors}")
        logger.error(f"Errores no de campo: {form.non_field_errors()}")
        
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Personal'
        context['subtitle'] = 'Registro completo de nuevo empleado'
        
        # Información adicional para el template
        if self.request.user.rol.nombre == 'Gerente':
            context['edificio_asignado'] = self.request.user.gerente.edificio
            context['es_gerente'] = True
        else:
            context['es_gerente'] = False
            
        return context