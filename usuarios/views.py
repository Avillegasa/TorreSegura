#views.py de usuarios
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from .models import Usuario, Rol
from alertas.models import Alerta 



from .forms import UsuarioCreationForm, UsuarioEditForm, RolForm
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from viviendas.models import Edificio, Residente,Vivienda
from usuarios.models import Gerente, Vigilante
from uuid import uuid4
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, AllowAny
from rest_framework.response import Response
from .serializers import ClientePotencialSerializer
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from .models import ClientePotencial
from django.db.models import Q
# Agregar estas importaciones al inicio de tu views.py
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from personal.models import Empleado
import logging
logger = logging.getLogger(__name__)
@api_view(['GET'])
@permission_classes([IsAuthenticated, DjangoModelPermissions])
def api_clientes_potenciales(request):
    clientes = ClientePotencial.objects.all().order_by('-fecha_contacto')
    serializer = ClientePotencialSerializer(clientes, many=True)
    return Response(serializer.data)
# ====== OPCIÓN 1: Usando Django REST Framework (Recomendado) ======
@api_view(['POST'])
@permission_classes([AllowAny])  # Permite acceso sin autenticación
def crear_cliente_potencial(request):
    """
    API endpoint para crear un cliente potencial desde NextJS
    """
    try:
        # Obtener datos del request
        data = request.data
        
        # Validar campos requeridos
        campos_requeridos = ['nombre_completo', 'email']
        for campo in campos_requeridos:
            if not data.get(campo):
                return Response({
                    'error': f'El campo {campo} es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar formato de email básico
        email = data.get('email')
        if not '@' in email or not '.' in email:
            return Response({
                'error': 'El formato del email no es válido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear el cliente potencial
        cliente = ClientePotencial.objects.create(
            nombre_completo=data.get('nombre_completo', '').strip(),
            telefono=data.get('telefono', '').strip(),
            email=email.strip().lower(),
            ubicacion=data.get('ubicacion', '').strip(),
            mensaje=data.get('mensaje', '').strip()
        )
        
        return Response({
            'success': True,
            'message': f"Gracias {cliente.nombre_completo}, hemos recibido tu mensaje correctamente. ¡Pronto nos pondremos en contacto!",
            'cliente_id': cliente.id,
            'fecha': cliente.fecha_contacto.strftime('%Y-%m-%d %H:%M:%S')
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Error interno del servidor',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ====== OPCIÓN 2: Usando Django Views tradicionales ======
@require_http_methods(["POST"])
def crear_cliente_potencial_simple(request):
    """
    Vista simple para crear cliente potencial sin DRF
    """
    try:
        # Parsear JSON del request
        data = json.loads(request.body)
        
        # Validar campos requeridos
        if not data.get('nombre_completo') or not data.get('email'):
            return JsonResponse({
                'success': False,
                'error': 'Los campos nombre_completo y email son requeridos'
            }, status=400)
        
        # Crear cliente potencial
        cliente = ClientePotencial.objects.create(
            nombre_completo=data.get('nombre_completo', '').strip(),
            telefono=data.get('telefono', '').strip(),
            email=data.get('email', '').strip().lower(),
            ubicacion=data.get('ubicacion', '').strip(),
            mensaje=data.get('mensaje', '').strip()
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Cliente potencial creado exitosamente',
            'id': cliente.id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)

# ====== Vista para listar clientes potenciales (ya existente, mejorada) ======
@method_decorator([login_required, permission_required('usuarios.ver_cliente_potencial', raise_exception=True)], name='dispatch')
class ClientePotencialListView(ListView):
    model = ClientePotencial
    template_name = 'usuarios/clientes_potenciales.html'
    context_object_name = 'clientes'
    ordering = ['-fecha_contacto']
    paginate_by = 20  # Paginación para mejor rendimiento
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtro por búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre_completo__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['total_clientes'] = self.get_queryset().count()
        return context

# ====== API para obtener estadísticas (opcional) ======
@api_view(['GET'])
@permission_classes([IsAuthenticated, DjangoModelPermissions])
def estadisticas_clientes_potenciales(request):
    """
    Obtener estadísticas de clientes potenciales
    """
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Estadísticas básicas
    total_clientes = ClientePotencial.objects.count()
    
    # Clientes de los últimos 30 días
    hace_30_dias = timezone.now() - timedelta(days=30)
    clientes_mes = ClientePotencial.objects.filter(
        fecha_contacto__gte=hace_30_dias
    ).count()
    
    # Clientes de la última semana
    hace_7_dias = timezone.now() - timedelta(days=7)
    clientes_semana = ClientePotencial.objects.filter(
        fecha_contacto__gte=hace_7_dias
    ).count()
    
    return Response({
        'total_clientes': total_clientes,
        'clientes_ultimo_mes': clientes_mes,
        'clientes_ultima_semana': clientes_semana,
        'crecimiento_semanal': clientes_semana,
        'crecimiento_mensual': clientes_mes
    })
# Función auxiliar para comprobar si es administrador
def tiene_acceso_web(user):
    return (
        user.is_authenticated and
        hasattr(user, 'rol') and
        user.rol is not None and
        user.rol.nombre in ['Administrador', 'Gerente']
    )

@login_required
def cargar_viviendas(request):
    edificio_id = request.GET.get('edificio_id')
    viviendas = Vivienda.objects.filter(edificio_id=edificio_id, estado='DESOCUPADO', activo=True).order_by('numero')
    viviendas_json = [{"id": v.id, "nombre": f"{v.numero} - Piso {v.piso}"} for v in viviendas]
    return JsonResponse(viviendas_json, safe=False)

class AccesoWebPermitidoMixin(UserPassesTestMixin):
    def test_func(self):
        return tiene_acceso_web(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Debe ingresar desde la aplicación móvil.",extra_tags='danger')
        return redirect('login')  # Puedes redirigir a otra vista si lo deseas


class UsuarioListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Usuario
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('rol').filter(rol__isnull=False)
        user = self.request.user
        query = self.request.GET.get("q", "").strip()
        rol_id = self.request.GET.get("rol", "").strip()
        edificio_id = self.request.GET.get("edificio", "").strip()

        # Gerente solo ve usuarios de su edificio
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            edificio = user.gerente.edificio
            queryset = queryset.filter(
                Q(gerente__edificio=edificio) |
                Q(vigilante__edificio=edificio) |
                Q(residente__vivienda__edificio=edificio) |
                Q(empleado__edificio=edificio)
            ).distinct()
        elif edificio_id and edificio_id.isdigit():
            queryset = queryset.filter(
                Q(gerente__edificio_id=edificio_id) |
                Q(vigilante__edificio_id=edificio_id) |
                Q(residente__vivienda__edificio_id=edificio_id) |
                Q(empleado__edificio_id=edificio_id)
            )

        # Filtro de búsqueda por texto
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )

        # Filtro por rol
        if rol_id and rol_id.isdigit():
            queryset = queryset.filter(rol_id=int(rol_id))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Parámetros de búsqueda
        context["q"] = self.request.GET.get("q", "")
        
        # Parámetros de rol - necesitamos tanto el string como el entero
        rol_str = self.request.GET.get("rol", "").strip()
        context["rol"] = rol_str  # Para el template
        context["rol_id"] = int(rol_str) if rol_str.isdigit() else None
        
        # Todos los roles disponibles
        context["roles"] = Rol.objects.all()
        edificio_str = self.request.GET.get("edificio", "").strip()
        context["edificio"] = edificio_str
        context["edificio_id"] = int(edificio_str) if edificio_str.isdigit() else None

        # Gerente solo ve su edificio en los filtros
        user = self.request.user
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            context["edificios"] = Edificio.objects.filter(pk=user.gerente.edificio.pk)
        else:
            context["edificios"] = Edificio.objects.all()
        return context


class UsuarioCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Usuario
    form_class = UsuarioCreationForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')

    def form_valid(self, form):
        rol = form.cleaned_data.get("rol")

        if rol and rol.nombre == "Personal":
            usuario = form.save(commit=False)
            usuario.is_active = True
            
            # Generar username a partir del nombre si está vacío
            if not usuario.username:
                base = f"{usuario.first_name.lower().replace(' ', '')}_{usuario.last_name.lower().replace(' ', '')}"
                usuario.username = base
                # Asegurar unicidad
                counter = 1
                while Usuario.objects.filter(username=usuario.username).exists():
                    usuario.username = f"{base}_{counter}"
                    counter += 1

            # Guardar la contraseña en texto plano para mostrarla una sola vez
            password_plano = form.cleaned_data.get('password1')
            usuario.save()
            
            # Crear el empleado
            Empleado.objects.create(
                usuario=usuario,
                puesto=form.cleaned_data.get("puesto"),
                edificio=form.cleaned_data.get("edificio"),
                fecha_contratacion=form.cleaned_data.get("fecha_contratacion"),
                tipo_contrato=form.cleaned_data.get("tipo_contrato"),
                salario=form.cleaned_data.get("salario"),
                contacto_emergencia=form.cleaned_data.get("contacto_emergencia"),
                telefono_emergencia=form.cleaned_data.get("telefono_emergencia"),
                especialidad=form.cleaned_data.get("especialidad"),
                creado_por=self.request.user
            )

            # Marcar email como verificado para acceso móvil sin verificación
            try:
                from allauth.account.models import EmailAddress
                EmailAddress.objects.get_or_create(
                    user=usuario,
                    email=usuario.email,
                    defaults={'primary': True, 'verified': True}
                )
            except Exception:
                pass

            self.object = usuario
            # Guardar credenciales en sesión para mostrarlas una sola vez
            self.request.session['credenciales_creadas'] = {
                'nombre_completo': usuario.get_full_name(),
                'username': usuario.username,
                'password': password_plano,
                'rol': rol.nombre,
                'puesto': str(form.cleaned_data.get('puesto', '')),
            }
            return redirect('usuario-credenciales')

        
        
        
        usuario = form.save(commit=False)
        usuario.is_active = True
        usuario.save()

        if usuario.rol and usuario.rol.nombre == "Residente":
            edificio = form.cleaned_data.get("edificio")
            vivienda = form.cleaned_data.get("vivienda")

            if hasattr(usuario, "residente"):
                form.add_error(None, "Este usuario ya está asignado como residente.")
                return self.form_invalid(form)

            # Crear el residente
            Residente.objects.create(usuario=usuario, vivienda=vivienda)
    
            # ✅ ACTUALIZAR EL ESTADO DE LA VIVIENDA A OCUPADO
            vivienda.estado = 'OCUPADO'
            vivienda.save()
        
        if usuario.rol and usuario.rol.nombre == "Gerente":
            edificio = form.cleaned_data.get("edificio")

            # Verificar si el usuario ya tiene Gerente
            if hasattr(usuario, "gerente"):
                form.add_error(None, "Este usuario ya está asignado como gerente.")
                return self.form_invalid(form)

            # Crear el gerente
            Gerente.objects.create(usuario=usuario, edificio=edificio)
            
        
        if usuario.rol and usuario.rol.nombre == "Vigilante":
            edificio = form.cleaned_data.get("edificio")

            if hasattr(usuario, "vigilante"):
                form.add_error(None, "Este usuario ya está asignado como vigilante.")
                return self.form_invalid(form)

            Vigilante.objects.create(usuario=usuario, edificio=edificio)
        messages.success(self.request, "Usuario creado correctamente.")
        logger = logging.getLogger(__name__)
        logger.warning(f"POST para crear {rol.nombre} recibido correctamente.")
        logger.warning(f"Datos: {form.cleaned_data}")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ FORMULARIO INVÁLIDO")
        logger.warning(form.errors.as_json())  # Esto te mostrará qué campos fallaron
        logger.warning(form.cleaned_data)
        messages.error(self.request, "Ocurrió un error al registrar el usuario. Revisa los datos.",extra_tags='danger')
        return super().form_invalid(form)
  
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user  # <- Esto es esencial
        return kwargs


class CustomLoginView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form):
        user = form.get_user()

        # Cargar rol (si hay problemas de BD, usar el usuario ya autenticado por el form)
        try:
            user_with_rol = Usuario.objects.select_related('rol').get(pk=user.pk)
        except Exception:
            user_with_rol = user

        if user_with_rol.rol is None or user_with_rol.rol.nombre not in ['Administrador', 'Gerente']:
            messages.error(self.request, "Debe ingresar desde la aplicación móvil.", extra_tags='danger')
            return redirect('login')

        # Para Administrador/Gerente: bloquear si no verificó su correo
        if user_with_rol.rol.nombre in ['Administrador', 'Gerente'] and not user_with_rol.email_confirmado:
            self.enviar_verificacion_email(user_with_rol)
            messages.warning(self.request, "Tu cuenta aún no ha sido verificada. Revisa tu correo para activarla.")
            return redirect('login')

        return super().form_valid(form)

    def enviar_verificacion_email(self, user):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        url = self.request.build_absolute_uri(reverse('verificar-email', kwargs={'uidb64': uid, 'token': token}))
        subject = 'Verificación de correo para TorreSegura'
        message = f'Hola {user.first_name},\n\nPor favor verifica tu cuenta haciendo clic en el siguiente enlace:\n\n{url}'

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:
            logger.exception("Error enviando correo de verificación a %s", user.email)
            messages.error(
                self.request,
                "No se pudo enviar el correo de verificación (revisa configuración SMTP).",
                extra_tags='danger',
            )


class VerificarEmailView(View):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.email_confirmado = True
            user.save()
            messages.success(request, "Correo verificado correctamente. Ahora puedes iniciar sesión.")
        else:
            messages.error(request, "El enlace de verificación no es válido o ha expirado.")
        return redirect('login')


@login_required
def usuario_credenciales(request):
    """Muestra las credenciales generadas una sola vez después de crear un usuario."""
    credenciales = request.session.pop('credenciales_creadas', None)
    if not credenciales:
        return redirect('usuario-list')
    return render(request, 'usuarios/usuario_credenciales.html', {'credenciales': credenciales})


class UsuarioUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Usuario
    form_class = UsuarioEditForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Se modificó correctamente la información del usuario: {self.object.username}")
        return response

# Reemplazo de la vista DeleteView por una vista personalizada para cambiar estado
class UsuarioChangeStateView(LoginRequiredMixin, AccesoWebPermitidoMixin, View):
    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        return render(request, 'usuarios/usuario_change_state.html', {'usuario': usuario})
    
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)

        if usuario == request.user:
            messages.add_message(request, messages.ERROR, "No puedes cambiar tu propio estado...", extra_tags='danger')
            return HttpResponseRedirect(reverse_lazy('usuario-list'))

        # Bloquear si el usuario tiene rol de alta seguridad
        if usuario.rol and usuario.rol.nombre in ['Administrador', 'Gerente']:
            messages.add_message(request, messages.ERROR, f"No puedes desactivar a un usuario con rol '{usuario.rol.nombre}'.", extra_tags='danger')
            return HttpResponseRedirect(reverse_lazy('usuario-list'))

        # Gerente solo puede cambiar estado de usuarios de su edificio
        if request.user.rol and request.user.rol.nombre == 'Gerente' and hasattr(request.user, 'gerente'):
            edificio = request.user.gerente.edificio
            es_de_mi_edificio = (
                (hasattr(usuario, 'residente') and usuario.residente.vivienda.edificio == edificio) or
                (hasattr(usuario, 'vigilante') and usuario.vigilante.edificio == edificio) or
                (hasattr(usuario, 'empleado') and usuario.empleado.edificio == edificio)
            )
            if not es_de_mi_edificio:
                messages.error(request, 'Solo puedes gestionar usuarios de tu edificio.', extra_tags='danger')
                return HttpResponseRedirect(reverse_lazy('usuario-list'))

        # Alternar estado activo
        usuario.is_active = not usuario.is_active
        usuario.save()

        # ✅ Si es residente y se desactiva, liberar la vivienda
        if not usuario.is_active and usuario.es_residente and hasattr(usuario, 'residente'):
            vivienda = usuario.residente.vivienda
            vivienda.estado = 'DESOCUPADO'
            vivienda.save()

        estado = "activado" if usuario.is_active else "desactivado"
        messages.success(request, f'El usuario {usuario.username} ha sido {estado} correctamente.')

        # ✅ Redirigir según el rol del usuario autenticado
        if request.user.rol and request.user.rol.nombre == "Administrador":
            return HttpResponseRedirect(reverse_lazy('usuario-list'))
        elif request.user.rol and request.user.rol.nombre == "Gerente":
            return HttpResponseRedirect(reverse_lazy('residente-list'))
        else:
            return HttpResponseRedirect(reverse_lazy('dashboard'))

class UsuarioDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = Usuario
    template_name = 'usuarios/usuario_detail.html'
    context_object_name = 'usuario'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        # Gerente solo puede ver detalles de usuarios de su edificio
        if user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente') and user.gerente.edificio:
            edificio = user.gerente.edificio
            queryset = queryset.filter(
                Q(gerente__edificio=edificio) |
                Q(vigilante__edificio=edificio) |
                Q(residente__vivienda__edificio=edificio) |
                Q(empleado__edificio=edificio)
            ).distinct()
        return queryset

# Vistas de Roles - Solo Administrador
class AdministradorRequeridoMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.is_authenticated and
            hasattr(self.request.user, 'rol') and
            self.request.user.rol is not None and
            self.request.user.rol.nombre == 'Administrador'
        )

    def handle_no_permission(self):
        messages.error(self.request, "Solo los administradores pueden gestionar roles.", extra_tags='danger')
        return redirect('dashboard')

class RolListView(LoginRequiredMixin, AdministradorRequeridoMixin, ListView):
    model = Rol
    template_name = 'usuarios/rol_list.html'
    context_object_name = 'roles'

class RolCreateView(LoginRequiredMixin, AdministradorRequeridoMixin, CreateView):
    model = Rol
    form_class = RolForm
    template_name = 'usuarios/rol_form.html'
    success_url = reverse_lazy('rol-list')

class RolUpdateView(LoginRequiredMixin, AdministradorRequeridoMixin, UpdateView):
    model = Rol
    form_class = RolForm
    template_name = 'usuarios/rol_form.html'
    success_url = reverse_lazy('rol-list')

class RolDeleteView(LoginRequiredMixin, AdministradorRequeridoMixin, DeleteView):
    model = Rol
    template_name = 'usuarios/rol_confirm_delete.html'
    success_url = reverse_lazy('rol-list')


#aqui estoy poniendo las alertas 

class AlertaListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Alerta
    template_name = 'alertas/lista_alertas.html'
    context_object_name = 'alertas'
    ordering = ['-fecha_creacion']