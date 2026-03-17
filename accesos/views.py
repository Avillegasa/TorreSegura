# accesos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import Visita, MovimientoResidente
from .forms import VisitaForm, MovimientoResidenteEntradaForm, MovimientoResidenteSalidaForm
from viviendas.models import Residente
from usuarios.models import Gerente
class BaseGerenteMixin:
    """
    Mixin base para filtrar contenido por edificio asignado al gerente
    """
    def get_edificio_gerente(self):
        """
        Obtiene el edificio asignado al gerente actual
        Asume que existe un modelo de roles/permisos que relaciona usuario con edificio
        """
        user = self.request.user
        
        # Si es administrador, puede ver todo
        if user.is_superuser or (hasattr(user, 'rol') and user.rol.nombre == 'Administrador'):
            return None
        
        # Si es gerente, obtener su edificio asignado
        if hasattr(user, 'rol') and user.rol.nombre == 'Gerente':
            if hasattr(user, 'gerente') and user.gerente.edificio:
                return user.gerente.edificio
            raise PermissionDenied("No tienes un edificio asignado como Gerente.")

        # Si no tiene permisos
        raise PermissionDenied("No tienes permisos para acceder a esta sección.")

# Vistas de Visitas
class VisitaListView(LoginRequiredMixin, BaseGerenteMixin, ListView):
    model = Visita
    template_name = 'accesos/visita_list.html'
    context_object_name = 'visitas'
    paginate_by = 20
    
    def get_queryset(self):
        # Obtener el edificio del gerente
        edificio_gerente = self.get_edificio_gerente()
        
        # Base queryset - solo visitas activas
        queryset = Visita.objects.filter(
            fecha_hora_salida__isnull=True
        ).select_related(
            'vivienda_destino__edificio',
            'residente_autoriza__usuario',
            'registrado_por'
        )
        
        # Si es gerente, filtrar por edificio
        if edificio_gerente:
            queryset = queryset.filter(vivienda_destino__edificio=edificio_gerente)
        
        return queryset.order_by('-fecha_hora_entrada')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el edificio del gerente para el contexto
        edificio_gerente = self.get_edificio_gerente()
        
        # Contador de visitas históricas filtrado por edificio
        if edificio_gerente:
            context['visitas_historicas'] = Visita.objects.filter(
                fecha_hora_salida__isnull=False,
                vivienda_destino__edificio=edificio_gerente
            ).count()
        else:
            # Si es administrador, mostrar todas
            context['visitas_historicas'] = Visita.objects.filter(
                fecha_hora_salida__isnull=False
            ).count()
        
        # Añadir información del edificio al contexto
        context['edificio_gerente'] = edificio_gerente
        
        return context

class VisitaCreateView(LoginRequiredMixin, BaseGerenteMixin, CreateView):
    model = Visita
    form_class = VisitaForm
    template_name = 'accesos/visita_form.html'
    success_url = reverse_lazy('visita-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasar el edificio del gerente al formulario
        kwargs['edificio_gerente'] = self.get_edificio_gerente()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Validar que la vivienda pertenezca al edificio del gerente
        edificio_gerente = self.get_edificio_gerente()
        if edificio_gerente and form.instance.vivienda_destino.edificio != edificio_gerente:
            messages.error(self.request, 'No puede registrar visitas para viviendas fuera de su edificio asignado.')
            return self.form_invalid(form)
        
        form.instance.registrado_por = self.request.user
        messages.success(self.request, f'Visita de {form.instance.nombre_visitante} registrada correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija los errores en el formulario.')
        return super().form_invalid(form)

class VisitaDetailView(LoginRequiredMixin, BaseGerenteMixin, DetailView):
    model = Visita
    template_name = 'accesos/visita_detail.html'
    context_object_name = 'visita'
    
    def get_object(self):
        obj = get_object_or_404(
            Visita.objects.select_related(
                'vivienda_destino__edificio',
                'residente_autoriza__usuario',
                'registrado_por'
            ),
            pk=self.kwargs['pk']
        )
        
        # Validar que el gerente solo pueda ver visitas de su edificio
        edificio_gerente = self.get_edificio_gerente()
        if edificio_gerente and obj.vivienda_destino.edificio != edificio_gerente:
            raise PermissionDenied("No tiene permisos para ver esta visita")
        
        return obj

@login_required
def registrar_salida_visita(request, pk):
    visita = get_object_or_404(Visita, pk=pk)
    
    # Validar permisos para gerente
    user = request.user
    if not user.is_superuser and not user.groups.filter(name='Administrador').exists():
        if user.groups.filter(name='Gerente').exists():
            try:
                gerente_edificio = Gerente.objects.get(usuario=user)
                if visita.vivienda_destino.edificio != gerente_edificio.edificio:
                    raise PermissionDenied("No tiene permisos para registrar la salida de esta visita")
            except Gerente.DoesNotExist:
                raise PermissionDenied("No tiene un edificio asignado como gerente")
        else:
            raise PermissionDenied("No tiene permisos para esta acción")
    
    if visita.fecha_hora_salida:
        messages.warning(request, f'La visita de {visita.nombre_visitante} ya tiene salida registrada.')
    else:
        visita.fecha_hora_salida = timezone.now()
        visita.save()
        messages.success(request, f'Salida de {visita.nombre_visitante} registrada correctamente.')
    
    return redirect('visita-list')

# Vistas de Movimientos de Residentes
class MovimientoResidenteListView(LoginRequiredMixin, BaseGerenteMixin, ListView):
    model = MovimientoResidente
    template_name = 'accesos/movimiento_list.html'
    context_object_name = 'movimientos'
    paginate_by = 20
    
    def get_queryset(self):
        edificio_gerente = self.get_edificio_gerente()
        
        # Base queryset con optimización
        queryset = MovimientoResidente.objects.select_related(
            'residente__usuario',
            'residente__vivienda__edificio'
        )
        
        # Filtrar por edificio si es gerente
        if edificio_gerente:
            queryset = queryset.filter(residente__vivienda__edificio=edificio_gerente)
        
        # Filtros opcionales
        residente_id = self.request.GET.get('residente')
        if residente_id:
            queryset = queryset.filter(residente_id=residente_id)
        
        tipo_movimiento = self.request.GET.get('tipo')
        if tipo_movimiento == 'entrada':
            queryset = queryset.filter(fecha_hora_entrada__isnull=False, fecha_hora_salida__isnull=True)
        elif tipo_movimiento == 'salida':
            queryset = queryset.filter(fecha_hora_salida__isnull=False, fecha_hora_entrada__isnull=True)
        
        return queryset.order_by('-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        edificio_gerente = self.get_edificio_gerente()
        
        # Base queryset para contadores
        base_queryset = MovimientoResidente.objects.all()
        if edificio_gerente:
            base_queryset = base_queryset.filter(residente__vivienda__edificio=edificio_gerente)
        
        # Contar entradas y salidas
        context['total_entradas'] = base_queryset.filter(
            fecha_hora_entrada__isnull=False
        ).count()
        context['total_salidas'] = base_queryset.filter(
            fecha_hora_salida__isnull=False
        ).count()
        
        # Residentes para filtro
        if edificio_gerente:
            context['residentes'] = Residente.objects.filter(
                activo=True,
                vivienda__edificio=edificio_gerente
            ).select_related('usuario', 'vivienda')
        else:
            context['residentes'] = Residente.objects.filter(
                activo=True
            ).select_related('usuario', 'vivienda')
        
        context['edificio_gerente'] = edificio_gerente
        return context

class MovimientoResidenteDetailView(LoginRequiredMixin, BaseGerenteMixin, DetailView):
    model = MovimientoResidente
    template_name = 'accesos/movimiento_detail.html'
    context_object_name = 'movimiento'
    
    def get_object(self):
        obj = get_object_or_404(
            MovimientoResidente.objects.select_related(
                'residente__usuario',
                'residente__vivienda__edificio'
            ),
            pk=self.kwargs['pk']
        )
        
        # Validar permisos para gerente
        edificio_gerente = self.get_edificio_gerente()
        if edificio_gerente and obj.residente.vivienda.edificio != edificio_gerente:
            raise PermissionDenied("No tiene permisos para ver este movimiento")
        
        return obj

class MovimientoResidenteEntradaView(LoginRequiredMixin, BaseGerenteMixin, CreateView):
    model = MovimientoResidente
    form_class = MovimientoResidenteEntradaForm
    template_name = 'accesos/movimiento_entrada_form.html'
    success_url = reverse_lazy('movimiento-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasar el edificio del gerente al formulario
        kwargs['edificio_gerente'] = self.get_edificio_gerente()
        return kwargs
    
    def form_valid(self, form):
        # Validar que el residente pertenezca al edificio del gerente
        edificio_gerente = self.get_edificio_gerente()
        if edificio_gerente and form.instance.residente.vivienda.edificio != edificio_gerente:
            messages.error(self.request, 'No puede registrar movimientos para residentes fuera de su edificio asignado.')
            return self.form_invalid(form)
        
        messages.success(self.request, f'Entrada de {form.instance.residente} registrada correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija los errores en el formulario.')
        return super().form_invalid(form)

class MovimientoResidenteSalidaView(LoginRequiredMixin, BaseGerenteMixin, CreateView):
    model = MovimientoResidente
    form_class = MovimientoResidenteSalidaForm
    template_name = 'accesos/movimiento_salida_form.html'
    success_url = reverse_lazy('movimiento-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasar el edificio del gerente al formulario
        kwargs['edificio_gerente'] = self.get_edificio_gerente()
        return kwargs
    
    def form_valid(self, form):
        # Validar que el residente pertenezca al edificio del gerente
        edificio_gerente = self.get_edificio_gerente()
        if edificio_gerente and form.instance.residente.vivienda.edificio != edificio_gerente:
            messages.error(self.request, 'No puede registrar movimientos para residentes fuera de su edificio asignado.')
            return self.form_invalid(form)
        
        messages.success(self.request, f'Salida de {form.instance.residente} registrada correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija los errores en el formulario.')
        return super().form_invalid(form)