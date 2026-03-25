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
from usuarios.views import AccesoWebPermitidoMixin, AdministradorRequeridoMixin
from .models import Puesto, Empleado, Asignacion, ComentarioAsignacion
from .forms import PuestoForm, EmpleadoForm, AsignacionForm, ComentarioAsignacionForm, AsignacionFiltroForm
from viviendas.models import Vivienda
from django.core.exceptions import ValidationError

class PuestoListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Puesto
    template_name = 'personal/puesto_list.html'
    context_object_name = 'puestos'

class PuestoCreateView(LoginRequiredMixin, AdministradorRequeridoMixin, CreateView):
    model = Puesto
    form_class = PuestoForm
    template_name = 'personal/puesto_form.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Puesto creado exitosamente.')
        return super().form_valid(form)

class PuestoUpdateView(LoginRequiredMixin, AdministradorRequeridoMixin, UpdateView):
    model = Puesto
    form_class = PuestoForm
    template_name = 'personal/puesto_form.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Puesto actualizado exitosamente.')
        return super().form_valid(form)

class PuestoDeleteView(LoginRequiredMixin, AdministradorRequeridoMixin, DeleteView):
    model = Puesto
    template_name = 'personal/puesto_confirm_delete.html'
    success_url = reverse_lazy('puesto-list')
    
    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, 'Puesto eliminado exitosamente.')
        except Exception:
            messages.error(self.request, 'No se pudo eliminar el puesto. Puede tener empleados asociados.')
            return redirect('puesto-list')
        return redirect(self.success_url)

# Vistas para Empleados
class EmpleadoListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Empleado
    template_name = 'personal/empleado_list.html'
    context_object_name = 'empleados'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('usuario', 'puesto')
        user = self.request.user

        # Gerente solo ve empleados de su edificio
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        
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

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        return queryset

    def form_valid(self, form):
        messages.success(self.request, 'Empleado actualizado exitosamente.')
        return super().form_valid(form)

class EmpleadoDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = Empleado
    template_name = 'personal/empleado_detail.html'
    context_object_name = 'empleado'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('usuario', 'puesto')
        user = self.request.user
        # Gerente solo puede ver empleados de su edificio
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        return queryset
    
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
    
    # ✅ CORRECCIÓN: Verificar permisos de administrador o gerente del edificio
    if not hasattr(request.user, 'rol') or request.user.rol.nombre not in ['Administrador', 'Gerente']:
        messages.error(request, 'No tienes permisos para realizar esta acción.', extra_tags='danger')
        return redirect('empleado-list')
    
    # Gerente solo puede gestionar empleados de su edificio
    if request.user.rol.nombre == 'Gerente' and hasattr(request.user, 'gerente'):
        if empleado.edificio != request.user.gerente.edificio:
            messages.error(request, 'Solo puedes gestionar empleados de tu edificio.', extra_tags='danger')
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
class AsignacionListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Asignacion
    template_name = 'personal/asignacion_list.html'
    context_object_name = 'asignaciones'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'empleado__usuario', 'empleado__puesto', 'edificio', 'vivienda', 'asignado_por'
        )
        user = self.request.user

        # Gerente solo ve asignaciones de su edificio
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        
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

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Asignación actualizada exitosamente.')
        return super().form_valid(form)

class AsignacionDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = Asignacion
    template_name = 'personal/asignacion_detail.html'
    context_object_name = 'asignacion'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'empleado__usuario', 'empleado__puesto', 'edificio', 'vivienda', 'asignado_por'
        ).prefetch_related('comentarios__usuario')
        user = self.request.user
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            queryset = queryset.filter(edificio=user.gerente.edificio)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comentario_form'] = ComentarioAsignacionForm()
        context['comentarios'] = self.object.comentarios.select_related('usuario').order_by('-fecha')
        return context

    def post(self, request, *args, **kwargs):
        """Manejar el envío del formulario de comentarios"""
        self.object = self.get_object()
        # Solo Admin/Gerente pueden comentar
        rol_nombre = getattr(getattr(request.user, 'rol', None), 'nombre', None)
        if rol_nombre not in ['Administrador', 'Gerente']:
            messages.error(request, 'No tienes permisos para agregar comentarios.', extra_tags='danger')
            return redirect('asignacion-detail', pk=self.object.pk)

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
    if not hasattr(request.user, 'rol') or request.user.rol.nombre not in ['Administrador', 'Gerente']:
        # Permitir que el empleado asignado también pueda cambiar algunos estados
        if not (hasattr(request.user, 'empleado') and request.user.empleado == asignacion.empleado):
            messages.error(request, 'No tienes permisos para cambiar el estado de esta asignación.', extra_tags='danger')
            return redirect('asignacion-detail', pk=asignacion.pk)
    
    # Gerente solo puede gestionar asignaciones de su edificio
    if hasattr(request.user, 'rol') and request.user.rol.nombre == 'Gerente' and hasattr(request.user, 'gerente'):
        if asignacion.edificio != request.user.gerente.edificio:
            messages.error(request, 'Solo puedes gestionar asignaciones de tu edificio.', extra_tags='danger')
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
    except Exception:
        return JsonResponse({'error': 'Error al obtener viviendas'}, status=500)
    
    
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
            empleado, credenciales = form.crear_usuario_y_empleado(creado_por=self.request.user)

            if credenciales:
                # Vigilante creado: verificar email en allauth para evitar bloqueo en login
                nombre = f'{empleado.usuario.first_name} {empleado.usuario.last_name}'
                email = empleado.usuario.email
                email_enviado = False

                if email and '@noemail.com' not in email:
                    from allauth.account.models import EmailAddress
                    EmailAddress.objects.get_or_create(
                        user=empleado.usuario,
                        email=email,
                        defaults={'primary': True, 'verified': True}
                    )

                    email_enviado = self._enviar_email_credenciales_vigilante(
                        empleado.usuario, credenciales['password']
                    )

                if email_enviado:
                    messages.success(
                        self.request,
                        f'Vigilante {nombre} creado exitosamente. '
                        f'Se enviaron las credenciales a {email}.'
                    )
                else:
                    messages.success(
                        self.request,
                        f'Vigilante {nombre} creado exitosamente.'
                    )
                    if not email or '@noemail.com' in email:
                        messages.warning(
                            self.request,
                            'No se enviaron credenciales por email porque no tiene correo registrado.'
                        )

                # Guardar credenciales en sesion para mostrarlas una sola vez
                self.request.session['credenciales_vigilante'] = {
                    'nombre': nombre,
                    'username': credenciales['username'],
                    'password': credenciales['password'],
                    'email_enviado': email_enviado,
                }
                return redirect('personal-credenciales')
            else:
                # Personal normal: enviar QR por email
                from personal.qr_utils import enviar_qr_por_email
                email_enviado = enviar_qr_por_email(empleado)

                nombre = f'{empleado.usuario.first_name} {empleado.usuario.last_name}'
                if email_enviado:
                    messages.success(
                        self.request,
                        f'Personal {nombre} creado exitosamente en el puesto de '
                        f'{empleado.puesto.nombre}. Se envio el QR de identificacion a '
                        f'{empleado.usuario.email}.'
                    )
                else:
                    messages.success(
                        self.request,
                        f'Personal {nombre} creado exitosamente en el puesto de '
                        f'{empleado.puesto.nombre}.'
                    )
                    if not empleado.usuario.email or '@noemail.com' in empleado.usuario.email:
                        messages.warning(
                            self.request,
                            'No se envio QR porque el empleado no tiene email registrado.'
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

    def _enviar_email_credenciales_vigilante(self, usuario, password_temporal):
        """Envia email con credenciales y enlace de cambio de contrasena al vigilante."""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        nombre = f'{usuario.first_name} {usuario.last_name}'
        edificio = ''
        if hasattr(usuario, 'vigilante') and usuario.vigilante and usuario.vigilante.edificio:
            edificio = usuario.vigilante.edificio.nombre

        # Generar enlace de cambio de contrasena
        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        reset_url = self.request.build_absolute_uri(
            f'/password-reset/{uid}/{token}/'
        )

        asunto = 'Torre Segura - Credenciales de acceso'
        mensaje = (
            f'Hola {nombre},\n\n'
            f'Se ha creado tu cuenta de vigilante en Torre Segura.\n\n'
            f'{f"Edificio asignado: {edificio}" + chr(10) if edificio else ""}'
            f'Tus credenciales para la aplicacion movil son:\n'
            f'  Usuario: {usuario.username}\n'
            f'  Contrasena: {password_temporal}\n\n'
            f'PASOS PARA ACTIVAR TU CUENTA:\n'
            f'1. Descarga la aplicacion movil Torre Segura\n'
            f'2. Inicia sesion con las credenciales de arriba\n'
            f'3. La app te pedira que cambies tu contrasena\n'
            f'4. Haz clic en el siguiente enlace para crear tu contrasena definitiva:\n\n'
            f'   {reset_url}\n\n'
            f'5. Una vez cambiada, vuelve a la app e inicia sesion con tu nueva contrasena\n\n'
            f'IMPORTANTE: Estas credenciales temporales son validas por 24 horas.\n\n'
            f'Saludos,\n'
            f'Equipo Torre Segura'
        )

        try:
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [usuario.email],
                fail_silently=False,
            )
            return True
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando credenciales a {usuario.email}")
            messages.warning(
                self.request,
                f'No se pudo enviar el email a {usuario.email}. '
                f'Comparta las credenciales manualmente.'
            )
            return False

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


@login_required
def credenciales_vigilante_view(request):
    """
    Muestra las credenciales del vigilante recien creado una sola vez.
    Las credenciales se eliminan de la sesion despues de mostrarlas.
    """
    credenciales = request.session.pop('credenciales_vigilante', None)
    if not credenciales:
        messages.warning(request, "No hay credenciales para mostrar.")
        return redirect('empleado-list')

    return render(request, 'personal/credenciales_vigilante.html', {
        'credenciales': credenciales,
    })