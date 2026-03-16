# views.py de viviendas - VERSIÓN CORREGIDA
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from usuarios.views import AccesoWebPermitidoMixin
from .models import Edificio, Vivienda, Residente
from .forms import EdificioForm, ViviendaForm, ViviendaBajaForm, ResidenteCreationForm
# Vistas de Edificios
class EdificioListView(LoginRequiredMixin, ListView):
    model = Edificio
    template_name = 'viviendas/edificio_list.html'
    context_object_name = 'edificios'

class EdificioCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Edificio
    form_class = EdificioForm
    template_name = 'viviendas/edificio_form.html'
    success_url = reverse_lazy('edificio-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Edificio creado exitosamente.')
        return super().form_valid(form)

class EdificioUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Edificio
    form_class = EdificioForm
    template_name = 'viviendas/edificio_form.html'
    success_url = reverse_lazy('edificio-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Edificio actualizado exitosamente.')
        return super().form_valid(form)

class EdificioDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = Edificio
    template_name = 'viviendas/edificio_confirm_delete.html'
    success_url = reverse_lazy('edificio-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Edificio eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

class EdificioDetailView(LoginRequiredMixin, DetailView):
    model = Edificio
    template_name = 'viviendas/edificio_detail.html'
    context_object_name = 'edificio'

# Vistas de Viviendas
class ViviendaListView(LoginRequiredMixin, ListView):
    model = Vivienda
    template_name = 'viviendas/vivienda_list.html'
    context_object_name = 'viviendas'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Si es Gerente: limitar al edificio asignado
        if user.rol and user.rol.nombre == 'Gerente':
            if hasattr(user, 'gerente') and user.gerente.edificio:
                queryset = queryset.filter(edificio=user.gerente.edificio)
            else:
                return Vivienda.objects.none()

        # Aplicar filtros de búsqueda
        edificio_id = self.request.GET.get('edificio')
        if edificio_id:
            queryset = queryset.filter(edificio_id=edificio_id)

        piso = self.request.GET.get('piso')
        if piso:
            queryset = queryset.filter(piso=piso)

        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)

        activo = self.request.GET.get('activo')
        if activo:
            activo_bool = activo.lower() == 'true'
            queryset = queryset.filter(activo=activo_bool)
        else:
            queryset = queryset.filter(activo=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Filtro de edificios según el rol
        if user.rol and user.rol.nombre == 'Gerente':
            if hasattr(user, 'gerente') and user.gerente.edificio:
                context['edificios'] = Edificio.objects.filter(pk=user.gerente.edificio.pk)
            else:
                context['edificios'] = Edificio.objects.none()
        else:
            context['edificios'] = Edificio.objects.all()

        context['filtro_edificio'] = self.request.GET.get('edificio', '')
        context['filtro_piso'] = self.request.GET.get('piso', '')
        context['filtro_estado'] = self.request.GET.get('estado', '')
        context['filtro_activo'] = self.request.GET.get('activo', 'true')

        # Pisos y estados para el formulario de filtro
        context['pisos'] = Vivienda.objects.values_list('piso', flat=True).distinct().order_by('piso')
        context['estados'] = [estado[0] for estado in Vivienda.ESTADOS]

        # Contadores
        context['total_activas'] = Vivienda.objects.filter(activo=True).count()
        context['total_inactivas'] = Vivienda.objects.filter(activo=False).count()

        return context

# ✅ CORRECCIÓN 1: Agregar get_form_kwargs en ViviendaCreateView
class ViviendaCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Vivienda
    form_class = ViviendaForm
    template_name = 'viviendas/vivienda_form.html'
    success_url = reverse_lazy('vivienda-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Vivienda creada exitosamente.')
        return super().form_valid(form)

# ✅ CORRECCIÓN 2: Agregar get_form_kwargs en ViviendaUpdateView
class ViviendaUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Vivienda
    form_class = ViviendaForm
    template_name = 'viviendas/vivienda_form.html'
    success_url = reverse_lazy('vivienda-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Vivienda actualizada exitosamente.')
        return super().form_valid(form)

class ViviendaDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = Vivienda
    template_name = 'viviendas/vivienda_confirm_delete.html'
    success_url = reverse_lazy('vivienda-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Vivienda eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

class ViviendaDetailView(LoginRequiredMixin, DetailView):
    model = Vivienda
    template_name = 'viviendas/vivienda_detail.html'
    context_object_name = 'vivienda'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener estadísticas de residentes
        vivienda = self.get_object()
        
        # Estadísticas de propietarios e inquilinos
        propietarios = vivienda.residentes.filter(es_propietario=True)
        inquilinos = vivienda.residentes.filter(es_propietario=False)
        
        context['propietarios'] = propietarios
        context['inquilinos'] = inquilinos
        context['propietarios_count'] = propietarios.count()
        context['inquilinos_count'] = inquilinos.count()
        context['propietarios_activos_count'] = propietarios.filter(activo=True).count()
        context['propietarios_inactivos_count'] = propietarios.filter(activo=False).count()
        context['inquilinos_activos_count'] = inquilinos.filter(activo=True).count()
        context['inquilinos_inactivos_count'] = inquilinos.filter(activo=False).count()
        
        return context

# Vistas de Residentes - VERSIÓN CORREGIDA
class ResidenteListView(LoginRequiredMixin, ListView):
    model = Residente
    template_name = 'viviendas/residente_list.html'
    context_object_name = 'residentes'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('usuario', 'vivienda', 'vivienda__edificio')

        user = self.request.user
        
        # Aplicar filtro base por rol
        if user.rol and user.rol.nombre == 'Gerente':
            if hasattr(user, 'gerente') and user.gerente.edificio:
                queryset = queryset.filter(vivienda__edificio=user.gerente.edificio)
            else:
                queryset = queryset.none()
        
        # Aplicar filtros adicionales (tanto para Gerente como para Administrador)
        if user.rol and user.rol.nombre in ['Gerente', 'Administrador']:
            # Filtro por edificio (solo disponible para Administrador)
            if user.rol.nombre == 'Administrador':
                edificio_id = self.request.GET.get('edificio')
                if edificio_id:
                    try:
                        edificio_id = int(edificio_id)
                        queryset = queryset.filter(vivienda__edificio_id=edificio_id)
                    except (ValueError, TypeError):
                        pass

            # Filtro por vivienda
            vivienda_id = self.request.GET.get('vivienda')
            if vivienda_id:
                try:
                    vivienda_id = int(vivienda_id)
                    queryset = queryset.filter(vivienda_id=vivienda_id)
                except (ValueError, TypeError):
                    pass

            # Filtro por tipo de residente (propietario/inquilino)
            es_propietario = self.request.GET.get('es_propietario')
            if es_propietario:
                if es_propietario.lower() == 'true':
                    queryset = queryset.filter(es_propietario=True)
                elif es_propietario.lower() == 'false':
                    queryset = queryset.filter(es_propietario=False)

            # Filtro por estado (activo/inactivo)
            estado = self.request.GET.get('estado')
            if estado:
                if estado.lower() == 'activo':
                    queryset = queryset.filter(activo=True)
                elif estado.lower() == 'inactivo':
                    queryset = queryset.filter(activo=False)

        return queryset.order_by('vivienda__edificio__nombre', 'vivienda__piso', 'vivienda__numero', 'usuario__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Configurar opciones de filtro según el rol
        if user.rol and user.rol.nombre == 'Gerente':
            if hasattr(user, 'gerente') and user.gerente.edificio:
                context['edificios'] = Edificio.objects.filter(pk=user.gerente.edificio.pk)
                context['viviendas'] = Vivienda.objects.filter(
                    edificio=user.gerente.edificio, 
                    activo=True
                ).order_by('piso', 'numero')
            else:
                context['edificios'] = Edificio.objects.none()
                context['viviendas'] = Vivienda.objects.none()
        elif user.rol and user.rol.nombre == 'Administrador':
            context['edificios'] = Edificio.objects.all().order_by('nombre')
            edificio_id = self.request.GET.get('edificio')
            if edificio_id:
                try:
                    edificio_id = int(edificio_id)
                    context['viviendas'] = Vivienda.objects.filter(
                        edificio_id=edificio_id, 
                        activo=True
                    ).order_by('piso', 'numero')
                except (ValueError, TypeError):
                    context['viviendas'] = Vivienda.objects.none()
            else:
                context['viviendas'] = Vivienda.objects.filter(activo=True).order_by(
                    'edificio__nombre', 'piso', 'numero'
                )
        else:
            context['edificios'] = Edificio.objects.none()
            context['viviendas'] = Vivienda.objects.none()

        # Mantener valores de filtros en el contexto
        context['filtro_edificio'] = self.request.GET.get('edificio', '')
        context['filtro_vivienda'] = self.request.GET.get('vivienda', '')
        context['filtro_es_propietario'] = self.request.GET.get('es_propietario', '')
        context['filtro_estado'] = self.request.GET.get('estado', '')
        
        # Opciones para los select del formulario
        context['opciones_tipo'] = [
            ('', 'Todos'),
            ('true', 'Propietario'),
            ('false', 'Inquilino'),
        ]
        
        context['opciones_estado'] = [
            ('', 'Todos'),
            ('activo', 'Activo'),
            ('inactivo', 'Inactivo'),
        ]
        
        # Estadísticas adicionales
        queryset_base = self.get_queryset()
        context['total_residentes'] = queryset_base.count()
        context['total_propietarios'] = queryset_base.filter(es_propietario=True).count()
        context['total_inquilinos'] = queryset_base.filter(es_propietario=False).count()
        context['total_activos'] = queryset_base.filter(activo=True).count()
        context['total_inactivos'] = queryset_base.filter(activo=False).count()

        return context

class ResidenteCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Residente
    form_class = ResidenteCreationForm
    template_name = 'viviendas/residente_form.html'
    success_url = reverse_lazy('residente-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Residente creado correctamente.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Por favor corrige los errores en el formulario.")
        return super().form_invalid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user
        return kwargs

# ✅ CORRECCIÓN 3: Agregar get_form_kwargs en ResidenteUpdateView
class ResidenteUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Residente
    form_class = ResidenteCreationForm
    template_name = 'viviendas/residente_form.html'
    success_url = reverse_lazy('residente-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_actual'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Residente actualizado exitosamente.')
        return super().form_valid(form)

class ResidenteDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = Residente
    template_name = 'viviendas/residente_confirm_delete.html'
    success_url = reverse_lazy('residente-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Residente eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

class ResidenteDetailView(LoginRequiredMixin, DetailView):
    model = Residente
    template_name = 'viviendas/residente_detail.html'
    context_object_name = 'residente'

class ViviendaBajaView(LoginRequiredMixin, AccesoWebPermitidoMixin, View):
    """
    Vista para dar de baja una vivienda en lugar de eliminarla.
    Esta vista permite establecer un motivo de baja y la fecha.
    """
    template_name = 'viviendas/vivienda_baja.html'
    
    def get(self, request, pk):
        vivienda = get_object_or_404(Vivienda, pk=pk)
        
        # Verificar si tiene residentes activos
        residentes_activos = vivienda.residentes.filter(activo=True).count()
        
        form = ViviendaBajaForm(instance=vivienda)
        
        return render(request, self.template_name, {
            'vivienda': vivienda,
            'form': form,
            'residentes_activos': residentes_activos
        })
    
    def post(self, request, pk):
        vivienda = get_object_or_404(Vivienda, pk=pk)
        form = ViviendaBajaForm(request.POST, instance=vivienda)
        
        # Verificar si tiene residentes activos
        residentes_activos = vivienda.residentes.filter(activo=True).count()
        
        if residentes_activos > 0 and not request.POST.get('confirmar_residentes'):
            messages.error(request, "No se puede dar de baja una vivienda con residentes activos. Debe reubicarlos primero.")
            return render(request, self.template_name, {
                'vivienda': vivienda,
                'form': form,
                'residentes_activos': residentes_activos
            })
        
        if form.is_valid():
            # Marcar como inactiva y cambiar estado
            vivienda.activo = False
            vivienda.estado = 'BAJA'
            vivienda.fecha_baja = form.cleaned_data.get('fecha_baja') or timezone.now().date()
            vivienda.motivo_baja = form.cleaned_data.get('motivo_baja')
            vivienda.save()
            
            messages.success(request, f"La vivienda {vivienda.numero} ha sido dada de baja correctamente.")
            return redirect('vivienda-list')
        
        return render(request, self.template_name, {
            'vivienda': vivienda,
            'form': form,
            'residentes_activos': residentes_activos
        })