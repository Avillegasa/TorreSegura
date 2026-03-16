from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse,FileResponse, HttpResponse
from django.db.models import Sum, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

import json
from decimal import Decimal
from datetime import timedelta
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from usuarios.views import AccesoWebPermitidoMixin

from .models import (
    ConceptoCuota, Cuota, Pago, PagoCuota, 
    CategoriaGasto, Gasto, EstadoCuenta
)
from .forms import (
    ConceptoCuotaForm, CuotaForm, GenerarCuotasForm, PagoForm,
    CategoriaGastoForm, GastoForm, EstadoCuentaForm, GenerarEstadosCuentaForm
)
from viviendas.models import Vivienda, Edificio, Residente
from usuarios.models import Usuario

# Vistas para ConceptoCuota
class ConceptoCuotaListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = ConceptoCuota
    template_name = 'financiero/concepto_list.html'
    context_object_name = 'conceptos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por nombre si se proporciona una búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | 
                Q(descripcion__icontains=search)
            )
        
        # Filtrar por activo/inactivo
        activo = self.request.GET.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['activo'] = self.request.GET.get('activo', '')
        return context

class ConceptoCuotaCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = ConceptoCuota
    form_class = ConceptoCuotaForm
    template_name = 'financiero/concepto_form.html'
    success_url = reverse_lazy('concepto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Concepto de cuota creado exitosamente.')
        return super().form_valid(form)

class ConceptoCuotaDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = ConceptoCuota
    template_name = 'financiero/concepto_detail.html'
    context_object_name = 'concepto'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener cuotas asociadas a este concepto
        concepto = self.object
        context['cuotas'] = Cuota.objects.filter(concepto=concepto).order_by('-fecha_emision')[:10]
        context['total_cuotas'] = Cuota.objects.filter(concepto=concepto).count()
        context['cuotas_pendientes'] = Cuota.objects.filter(concepto=concepto, pagada=False).count()
        
        # Calcular cuotas pagadas
        cuotas_pagadas = context['total_cuotas'] - context['cuotas_pendientes']
        context['cuotas_pagadas'] = cuotas_pagadas
        
        return context

class ConceptoCuotaUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = ConceptoCuota
    form_class = ConceptoCuotaForm
    template_name = 'financiero/concepto_form.html'
    success_url = reverse_lazy('concepto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Concepto de cuota actualizado exitosamente.')
        return super().form_valid(form)

class ConceptoCuotaDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = ConceptoCuota
    template_name = 'financiero/concepto_confirm_delete.html'
    success_url = reverse_lazy('concepto-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Concepto de cuota eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si hay cuotas asociadas
        concepto = self.object
        cuotas = Cuota.objects.filter(concepto=concepto).count()
        context['tiene_cuotas'] = cuotas > 0
        context['numero_cuotas'] = cuotas
        return context

# Vistas para Cuota
class CuotaListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Cuota
    template_name = 'financiero/cuota_list.html'
    context_object_name = 'cuotas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por concepto
        concepto_id = self.request.GET.get('concepto')
        if concepto_id:
            queryset = queryset.filter(concepto_id=concepto_id)
        
        # Filtrar por vivienda o edificio
        vivienda_id = self.request.GET.get('vivienda')
        edificio_id = self.request.GET.get('edificio')
        if vivienda_id:
            queryset = queryset.filter(vivienda_id=vivienda_id)
        elif edificio_id:
            queryset = queryset.filter(vivienda__edificio_id=edificio_id)
        
        # Filtrar por estado (pagada/pendiente)
        estado = self.request.GET.get('estado')
        if estado == 'pagada':
            queryset = queryset.filter(pagada=True)
        elif estado == 'pendiente':
            queryset = queryset.filter(pagada=False)
        
        # Filtrar por fecha de emisión
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        if fecha_desde:
            queryset = queryset.filter(fecha_emision__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
        
        # Filtrar por vencimiento
        vencimiento = self.request.GET.get('vencimiento')
        if vencimiento == 'vencidas':
            queryset = queryset.filter(
                fecha_vencimiento__lt=timezone.now().date(),
                pagada=False
            )
        elif vencimiento == 'proximas':
            # Próximas a vencer (en los próximos 15 días)
            hoy = timezone.now().date()
            proxima = hoy + timedelta(days=15)
            queryset = queryset.filter(
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=proxima,
                pagada=False
            )
        
        # Ordenar
        orden = self.request.GET.get('orden', '-fecha_emision')
        queryset = queryset.order_by(orden)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar filtros al contexto
        context['conceptos'] = ConceptoCuota.objects.filter(activo=True)
        context['edificios'] = Edificio.objects.all()
        context['viviendas'] = Vivienda.objects.filter(activo=True)
        
        # Valores actuales de filtros
        context['concepto_id'] = self.request.GET.get('concepto', '')
        context['edificio_id'] = self.request.GET.get('edificio', '')
        context['vivienda_id'] = self.request.GET.get('vivienda', '')
        context['estado'] = self.request.GET.get('estado', '')
        context['vencimiento'] = self.request.GET.get('vencimiento', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        context['orden'] = self.request.GET.get('orden', '-fecha_emision')
        
        # Calcular totales
        cuotas = self.object_list
        # CÓDIGO CORREGIDO
        from django.db.models import DecimalField

        context['total_monto'] = cuotas.aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_recargo'] = cuotas.aggregate(
            total=Coalesce(Sum('recargo', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_general'] = context['total_monto'] + context['total_recargo']
        
        return context

class CuotaCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Cuota
    form_class = CuotaForm
    template_name = 'financiero/cuota_form.html'
    success_url = reverse_lazy('cuota-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Cuota creada exitosamente.')
        return super().form_valid(form)

class CuotaDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = Cuota
    template_name = 'financiero/cuota_detail.html'
    context_object_name = 'cuota'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener pagos asociados a esta cuota
        cuota = self.object
        context['pagos_cuota'] = PagoCuota.objects.filter(cuota=cuota)
        return context

class CuotaUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Cuota
    form_class = CuotaForm
    template_name = 'financiero/cuota_form.html'
    success_url = reverse_lazy('cuota-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Cuota actualizada exitosamente.')
        return super().form_valid(form)

@login_required
def generar_cuotas(request):
    """Vista para generar cuotas masivamente"""
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        raise PermissionDenied
    
    if request.method == 'POST':
        form = GenerarCuotasForm(request.POST)
        if form.is_valid():
            concepto = form.cleaned_data['concepto']
            edificio = form.cleaned_data['edificio']
            viviendas_seleccionadas = form.cleaned_data['viviendas']
            aplicar_a_todas = form.cleaned_data['aplicar_a_todas']
            fecha_emision = form.cleaned_data['fecha_emision']
            fecha_vencimiento = form.cleaned_data['fecha_vencimiento']
            monto_personalizado = form.cleaned_data['monto_personalizado']
            
            # Determinar las viviendas a las que aplicar
            if aplicar_a_todas:
                viviendas = Vivienda.objects.filter(activo=True)
            elif edificio:
                viviendas = Vivienda.objects.filter(edificio=edificio, activo=True)
            else:
                viviendas = viviendas_seleccionadas
            
            # Monto a aplicar
            monto = monto_personalizado if monto_personalizado else concepto.monto_base
            
            # Crear cuotas para cada vivienda
            cuotas_creadas = 0
            for vivienda in viviendas:
                # Verificar si ya existe una cuota para esta vivienda con este concepto en la misma fecha
                existe = Cuota.objects.filter(
                    concepto=concepto,
                    vivienda=vivienda,
                    fecha_emision=fecha_emision
                ).exists()
                
                if not existe:
                    Cuota.objects.create(
                        concepto=concepto,
                        vivienda=vivienda,
                        monto=monto,
                        fecha_emision=fecha_emision,
                        fecha_vencimiento=fecha_vencimiento
                    )
                    cuotas_creadas += 1
            
            messages.success(request, f'Se han generado {cuotas_creadas} cuotas exitosamente.')
            return redirect('cuota-list')
    else:
        form = GenerarCuotasForm()
    
    return render(request, 'financiero/cuota_generar.html', {'form': form})

# Vistas para Pago
class PagoListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = 'financiero/pago_list.html'
    context_object_name = 'pagos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # ✅ FILTRAR POR ROL DEL USUARIO
        if hasattr(user, 'residente') and user.rol and user.rol.nombre == 'Residente':
            # Residentes solo ven sus propios pagos
            queryset = queryset.filter(vivienda=user.residente.vivienda)
        elif hasattr(user, 'gerente') and user.rol and user.rol.nombre == 'Gerente':
            # Gerentes solo ven pagos de su edificio
            queryset = queryset.filter(vivienda__edificio=user.gerente.edificio)
        elif not (user.rol and user.rol.nombre == 'Administrador'):
            # Si no es admin, gerente o residente, no ve nada
            queryset = queryset.none()
        
        # ✅ APLICAR FILTROS SOLO SI EL USUARIO TIENE PERMISOS
        # Solo permitir filtros a administradores y gerentes
        if user.rol and user.rol.nombre in ['Administrador', 'Gerente']:
            vivienda_id = self.request.GET.get('vivienda')
            edificio_id = self.request.GET.get('edificio')
            
            # Solo administradores pueden filtrar por cualquier edificio
            if user.rol.nombre == 'Administrador':
                if vivienda_id:
                    queryset = queryset.filter(vivienda_id=vivienda_id)
                elif edificio_id:
                    queryset = queryset.filter(vivienda__edificio_id=edificio_id)
            # Gerentes ya están limitados a su edificio
        
        # Filtros generales disponibles para todos
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        metodo = self.request.GET.get('metodo')
        if metodo:
            queryset = queryset.filter(metodo_pago=metodo)
        
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        if fecha_desde:
            queryset = queryset.filter(fecha_pago__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_pago__lte=fecha_hasta)
        
        orden = self.request.GET.get('orden', '-fecha_pago')
        queryset = queryset.order_by(orden)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # ✅ CONFIGURAR OPCIONES DE FILTRO SEGÚN EL ROL
        if user.rol and user.rol.nombre == 'Administrador':
            context['edificios'] = Edificio.objects.all()
            context['viviendas'] = Vivienda.objects.filter(activo=True)
        elif user.rol and user.rol.nombre == 'Gerente' and hasattr(user, 'gerente'):
            context['edificios'] = Edificio.objects.filter(pk=user.gerente.edificio.pk)
            context['viviendas'] = Vivienda.objects.filter(
                edificio=user.gerente.edificio, 
                activo=True
            )
        else:
            # Residentes no ven filtros de edificio/vivienda
            context['edificios'] = Edificio.objects.none()
            context['viviendas'] = Vivienda.objects.none()
        
        context['estados_pago'] = Pago.ESTADO_CHOICES
        context['metodos_pago'] = Pago.METODO_PAGO_CHOICES
        
        # Valores actuales de filtros
        context['edificio_id'] = self.request.GET.get('edificio', '')
        context['vivienda_id'] = self.request.GET.get('vivienda', '')
        context['estado'] = self.request.GET.get('estado', '')
        context['metodo'] = self.request.GET.get('metodo', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        context['orden'] = self.request.GET.get('orden', '-fecha_pago')
        
        # Calcular totales
        pagos = self.object_list
        context['total_pagos'] = pagos.aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_verificados'] = pagos.filter(estado='VERIFICADO').aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_pendientes'] = pagos.filter(estado='PENDIENTE').aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        
        return context

class PagoCreateView(LoginRequiredMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = 'financiero/pago_form.html'
    success_url = reverse_lazy('pago-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        
        # ✅ FILTRAR VIVIENDAS SEGÚN EL ROL
        if hasattr(user, 'residente') and user.rol and user.rol.nombre == 'Residente':
            # Residentes solo pueden crear pagos para su vivienda
            form.fields['vivienda'].queryset = Vivienda.objects.filter(
                id=user.residente.vivienda.id
            )
            form.fields['vivienda'].initial = user.residente.vivienda
            form.fields['vivienda'].widget.attrs['readonly'] = True
            
            # También filtrar residentes a solo el usuario actual
            form.fields['residente'].queryset = Residente.objects.filter(
                usuario=user
            )
            form.fields['residente'].initial = user.residente
            
        elif hasattr(user, 'gerente') and user.rol and user.rol.nombre == 'Gerente':
            # Gerentes solo para su edificio
            form.fields['vivienda'].queryset = Vivienda.objects.filter(
                edificio=user.gerente.edificio,
                activo=True
            )
        # Administradores pueden ver todas (se mantiene el queryset original)
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Pago registrado exitosamente.')
        return super().form_valid(form)

class PagoDetailView(LoginRequiredMixin, DetailView):
    model = Pago
    template_name = 'financiero/pago_detail.html'
    context_object_name = 'pago'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener cuotas asociadas a este pago
        pago = self.object
        context['cuotas_pago'] = PagoCuota.objects.filter(pago=pago)
        
        # Calcular cuotas pendientes de la vivienda
        cuotas_pendientes = Cuota.objects.filter(
            vivienda=pago.vivienda,
            pagada=False
        )
        context['cuotas_pendientes_count'] = cuotas_pendientes.count()
        
        # Calcular monto pendiente total
        monto_total = sum(cuota.total_a_pagar() for cuota in cuotas_pendientes)
        context['monto_pendiente_total'] = Decimal(str(monto_total))
        
        return context

class PagoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pago
    form_class = PagoForm
    template_name = 'financiero/pago_form.html'
    success_url = reverse_lazy('pago-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Pago actualizado exitosamente.')
        return super().form_valid(form)

@login_required
def verificar_pago(request, pk):
    """Vista para verificar un pago - PERMISOS CORREGIDOS"""
    pago = get_object_or_404(Pago, pk=pk)
    
    # ✅ VERIFICACIÓN DE PERMISOS MEJORADA
    user = request.user
    
    # Solo Administradores y Gerentes pueden verificar pagos
    if not (hasattr(user, 'rol') and user.rol and 
            user.rol.nombre in ['Administrador', 'Gerente']):
        messages.error(request, 'No tienes permisos para verificar pagos.')
        return redirect('pago-detail', pk=pk)
    
    # Gerentes solo pueden verificar pagos de su edificio
    if (user.rol.nombre == 'Gerente' and 
        hasattr(user, 'gerente') and
        pago.vivienda.edificio != user.gerente.edificio):
        messages.error(request, 'Solo puedes verificar pagos de tu edificio.')
        return redirect('pago-detail', pk=pk)
    
    if pago.estado != 'PENDIENTE':
        messages.error(request, 'Este pago ya ha sido verificado o rechazado.')
        return redirect('pago-detail', pk=pk)
    
    # Verificar el pago
    pago.verificar_pago(request.user)
    messages.success(request, 'Pago verificado exitosamente.')
    
    return redirect('pago-detail', pk=pk)

@login_required
def rechazar_pago(request, pk):
    """Vista para rechazar un pago - PERMISOS CORREGIDOS"""
    pago = get_object_or_404(Pago, pk=pk)
    
    # ✅ VERIFICACIÓN DE PERMISOS MEJORADA
    user = request.user
    
    # Solo Administradores y Gerentes pueden rechazar pagos
    if not (hasattr(user, 'rol') and user.rol and 
            user.rol.nombre in ['Administrador', 'Gerente']):
        messages.error(request, 'No tienes permisos para rechazar pagos.')
        return redirect('pago-detail', pk=pk)
    
    # Gerentes solo pueden rechazar pagos de su edificio
    if (user.rol.nombre == 'Gerente' and 
        hasattr(user, 'gerente') and
        pago.vivienda.edificio != user.gerente.edificio):
        messages.error(request, 'Solo puedes rechazar pagos de tu edificio.')
        return redirect('pago-detail', pk=pk)
    
    if pago.estado != 'PENDIENTE':
        messages.error(request, 'Este pago ya ha sido verificado o rechazado.')
        return redirect('pago-detail', pk=pk)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        pago.rechazar_pago(request.user, motivo)
        messages.success(request, 'Pago rechazado exitosamente.')
        return redirect('pago-detail', pk=pk)
    
    return render(request, 'financiero/pago_rechazar.html', {'pago': pago})

# Vistas para CategoriaGasto
class CategoriaGastoListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = CategoriaGasto
    template_name = 'financiero/categoria_gasto_list.html'
    context_object_name = 'categorias'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por nombre si se proporciona una búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | 
                Q(descripcion__icontains=search)
            )
        
        # Filtrar por activo/inactivo
        activo = self.request.GET.get('activo')
        if activo == 'true':
            queryset = queryset.filter(activo=True)
        elif activo == 'false':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['activo'] = self.request.GET.get('activo', '')
        
        # Calcular gastos totales por categoría
        for categoria in context['categorias']:
            categoria.total_gastos = Gasto.objects.filter(
                categoria=categoria, 
                estado='PAGADO'
            ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
        
        return context

class CategoriaGastoCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'financiero/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria-gasto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoría de gasto creada exitosamente.')
        return super().form_valid(form)

class CategoriaGastoDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = CategoriaGasto
    template_name = 'financiero/categoria_gasto_detail.html'
    context_object_name = 'categoria'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener gastos asociados a esta categoría
        categoria = self.object
        context['gastos'] = Gasto.objects.filter(categoria=categoria).order_by('-fecha')[:10]
        context['total_gastos'] = Gasto.objects.filter(categoria=categoria).count()
        
        # Calcular porcentaje de presupuesto utilizado
        total_mes = categoria.total_gastado_mes_actual()
        if categoria.presupuesto_mensual > 0:
            porcentaje = (total_mes / categoria.presupuesto_mensual) * 100
        else:
            porcentaje = 0
        context['porcentaje_utilizado'] = porcentaje
        context['total_mes'] = total_mes
        
        return context

class CategoriaGastoUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'financiero/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria-gasto-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoría de gasto actualizada exitosamente.')
        return super().form_valid(form)

class CategoriaGastoDeleteView(LoginRequiredMixin, AccesoWebPermitidoMixin, DeleteView):
    model = CategoriaGasto
    template_name = 'financiero/categoria_gasto_confirm_delete.html'
    success_url = reverse_lazy('categoria-gasto-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Categoría de gasto eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si hay gastos asociados
        categoria = self.object
        gastos = Gasto.objects.filter(categoria=categoria).count()
        context['tiene_gastos'] = gastos > 0
        context['numero_gastos'] = gastos
        return context

# Vistas para Gasto
class GastoListView(LoginRequiredMixin, AccesoWebPermitidoMixin, ListView):
    model = Gasto
    template_name = 'financiero/gasto_list.html'
    context_object_name = 'gastos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por categoría
        categoria_id = self.request.GET.get('categoria')
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        
        # Filtrar por estado
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtrar por tipo de gasto
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_gasto=tipo)
        
        # Filtrar por fecha
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=fecha_hasta)
        
        # Filtrar por monto
        monto_min = self.request.GET.get('monto_min')
        monto_max = self.request.GET.get('monto_max')
        if monto_min:
            queryset = queryset.filter(monto__gte=monto_min)
        if monto_max:
            queryset = queryset.filter(monto__lte=monto_max)
        
        # Filtrar por presupuestado/recurrente
        presupuestado = self.request.GET.get('presupuestado')
        if presupuestado == 'true':
            queryset = queryset.filter(presupuestado=True)
        elif presupuestado == 'false':
            queryset = queryset.filter(presupuestado=False)
        
        recurrente = self.request.GET.get('recurrente')
        if recurrente == 'true':
            queryset = queryset.filter(recurrente=True)
        elif recurrente == 'false':
            queryset = queryset.filter(recurrente=False)
        
        # Ordenar
        orden = self.request.GET.get('orden', '-fecha')
        queryset = queryset.order_by(orden)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar filtros al contexto
        context['categorias'] = CategoriaGasto.objects.filter(activo=True)
        context['estados_gasto'] = Gasto.ESTADO_CHOICES
        context['tipos_gasto'] = Gasto.TIPO_GASTO_CHOICES
        
        # Valores actuales de filtros
        context['categoria_id'] = self.request.GET.get('categoria', '')
        context['estado'] = self.request.GET.get('estado', '')
        context['tipo'] = self.request.GET.get('tipo', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        context['monto_min'] = self.request.GET.get('monto_min', '')
        context['monto_max'] = self.request.GET.get('monto_max', '')
        context['presupuestado'] = self.request.GET.get('presupuestado', '')
        context['recurrente'] = self.request.GET.get('recurrente', '')
        context['orden'] = self.request.GET.get('orden', '-fecha')
        
        # Calcular totales
        gastos = self.object_list
        # CÓDIGO CORREGIDO
        context['total_monto'] = gastos.aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_pagados'] = gastos.filter(estado='PAGADO').aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        context['total_pendientes'] = gastos.filter(estado='PENDIENTE').aggregate(
            total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0'))
        )['total']
        
        return context

class GastoCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = Gasto
    form_class = GastoForm
    template_name = 'financiero/gasto_form.html'
    success_url = reverse_lazy('gasto-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Gasto registrado exitosamente.')
        return super().form_valid(form)

class GastoDetailView(LoginRequiredMixin, AccesoWebPermitidoMixin, DetailView):
    model = Gasto
    template_name = 'financiero/gasto_detail.html'
    context_object_name = 'gasto'

class GastoUpdateView(LoginRequiredMixin, AccesoWebPermitidoMixin, UpdateView):
    model = Gasto
    form_class = GastoForm
    template_name = 'financiero/gasto_form.html'
    success_url = reverse_lazy('gasto-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Gasto actualizado exitosamente.')
        return super().form_valid(form)

@login_required
def marcar_gasto_pagado(request, pk):
    """Vista para marcar un gasto como pagado"""
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        raise PermissionDenied
    
    gasto = get_object_or_404(Gasto, pk=pk)
    
    if gasto.estado != 'PENDIENTE':
        messages.error(request, 'Este gasto ya ha sido pagado o cancelado.')
        return redirect('gasto-detail', pk=pk)
    
    if request.method == 'POST':
        fecha_pago = request.POST.get('fecha_pago')
        fecha = timezone.now().date()
        if fecha_pago:
            try:
                fecha = timezone.datetime.strptime(fecha_pago, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        gasto.marcar_como_pagado(fecha)
        messages.success(request, 'Gasto marcado como pagado exitosamente.')
        return redirect('gasto-detail', pk=pk)
    
    return render(request, 'financiero/gasto_marcar_pagado.html', {'gasto': gasto})

@login_required
def cancelar_gasto(request, pk):
    """Vista para cancelar un gasto"""
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        raise PermissionDenied
    
    gasto = get_object_or_404(Gasto, pk=pk)
    
    if gasto.estado != 'PENDIENTE':
        messages.error(request, 'Este gasto ya ha sido pagado o cancelado.')
        return redirect('gasto-detail', pk=pk)
    
    if request.method == 'POST':
        gasto.cancelar()
        messages.success(request, 'Gasto cancelado exitosamente.')
        return redirect('gasto-detail', pk=pk)
    
    return render(request, 'financiero/gasto_cancelar.html', {'gasto': gasto})

# Vistas para EstadoCuenta
class EstadoCuentaListView(LoginRequiredMixin, ListView):
    model = EstadoCuenta
    template_name = 'financiero/estado_cuenta_list.html'
    context_object_name = 'estados_cuenta'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por vivienda o edificio
        vivienda_id = self.request.GET.get('vivienda')
        edificio_id = self.request.GET.get('edificio')
        if vivienda_id:
            queryset = queryset.filter(vivienda_id=vivienda_id)
        elif edificio_id:
            queryset = queryset.filter(vivienda__edificio_id=edificio_id)
        
        # Filtrar por período
        periodo = self.request.GET.get('periodo')
        if periodo:
            # Calcular fechas según el período
            hoy = timezone.now().date()
            primer_dia_mes = hoy.replace(day=1)
            
            if periodo == 'mes_actual':
                queryset = queryset.filter(
                    fecha_inicio__year=hoy.year,
                    fecha_inicio__month=hoy.month
                )
            elif periodo == 'mes_anterior':
                mes_anterior = primer_dia_mes - timedelta(days=1)
                queryset = queryset.filter(
                    fecha_inicio__year=mes_anterior.year,
                    fecha_inicio__month=mes_anterior.month
                )
            elif periodo == 'anio_actual':
                queryset = queryset.filter(
                    fecha_inicio__year=hoy.year
                )
        
        # Filtrar por enviado
        enviado = self.request.GET.get('enviado')
        if enviado == 'true':
            queryset = queryset.filter(enviado=True)
        elif enviado == 'false':
            queryset = queryset.filter(enviado=False)
        
        # Ordenar
        orden = self.request.GET.get('orden', '-fecha_fin')
        queryset = queryset.order_by(orden)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar filtros al contexto
        context['edificios'] = Edificio.objects.all()
        context['viviendas'] = Vivienda.objects.filter(activo=True)
        
        # Valores actuales de filtros
        context['edificio_id'] = self.request.GET.get('edificio', '')
        context['vivienda_id'] = self.request.GET.get('vivienda', '')
        context['periodo'] = self.request.GET.get('periodo', '')
        context['enviado'] = self.request.GET.get('enviado', '')
        context['orden'] = self.request.GET.get('orden', '-fecha_fin')
        
        return context

class EstadoCuentaCreateView(LoginRequiredMixin, AccesoWebPermitidoMixin, CreateView):
    model = EstadoCuenta
    form_class = EstadoCuentaForm
    template_name = 'financiero/estado_cuenta_form.html'
    success_url = reverse_lazy('estado-cuenta-list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        estado_cuenta = self.object
        # Calcular totales después de guardar
        estado_cuenta.calcular_totales()
        messages.success(self.request, 'Estado de cuenta creado exitosamente.')
        return response

class EstadoCuentaDetailView(LoginRequiredMixin, DetailView):
    model = EstadoCuenta
    template_name = 'financiero/estado_cuenta_detail.html'
    context_object_name = 'estado_cuenta'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener detalles de cuotas y pagos
        estado_cuenta = self.object
        context['cuotas'] = estado_cuenta.obtener_detalle_cuotas()
        context['pagos'] = estado_cuenta.obtener_detalle_pagos()
        return context

@login_required
def estado_cuenta_pdf(request, pk):
    """Vista para generar PDF de estado de cuenta"""
    estado_cuenta = get_object_or_404(EstadoCuenta, pk=pk)
    
    # Verificar permisos
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        # Si no es admin, verificar que sea el residente de la vivienda
        if not Residente.objects.filter(usuario=request.user, vivienda=estado_cuenta.vivienda).exists():
            raise PermissionDenied
    
    # Crear un buffer para el PDF
    buffer = io.BytesIO()
    
    # Crear el PDF
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(30, height - 50, "Estado de Cuenta")
    
    # Información básica
    p.setFont("Helvetica", 12)
    p.drawString(30, height - 80, f"Vivienda: {estado_cuenta.vivienda}")
    p.drawString(30, height - 100, f"Período: {estado_cuenta.fecha_inicio.strftime('%d/%m/%Y')} - {estado_cuenta.fecha_fin.strftime('%d/%m/%Y')}")
    p.drawString(30, height - 120, f"Generado el: {estado_cuenta.fecha_generacion.strftime('%d/%m/%Y %H:%M')}")
    
    # Detalle de saldos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 160, "Resumen de Saldos")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 180, f"Saldo Anterior: ${estado_cuenta.saldo_anterior}")
    p.drawString(50, height - 200, f"Total Cuotas: ${estado_cuenta.total_cuotas}")
    p.drawString(50, height - 220, f"Total Recargos: ${estado_cuenta.total_recargos}")
    p.drawString(50, height - 240, f"Total Pagos: ${estado_cuenta.total_pagos}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 270, f"Saldo Final: ${estado_cuenta.saldo_final}")
    
    # Detalle de cuotas
    y_pos = height - 320
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y_pos, "Detalle de Cuotas")
    y_pos -= 20
    
    p.setFont("Helvetica", 10)
    cuotas = estado_cuenta.obtener_detalle_cuotas()
    if cuotas:
        # Cabecera
        p.drawString(30, y_pos, "Concepto")
        p.drawString(200, y_pos, "Emisión")
        p.drawString(280, y_pos, "Vencimiento")
        p.drawString(380, y_pos, "Monto")
        p.drawString(450, y_pos, "Estado")
        y_pos -= 20
        
        # Detalle
        for cuota in cuotas:
            if y_pos < 50:  # Nueva página si no hay espacio
                p.showPage()
                y_pos = height - 50
                
                # Cabecera nueva página
                p.setFont("Helvetica-Bold", 14)
                p.drawString(30, y_pos, "Detalle de Cuotas (continuación)")
                y_pos -= 20
                
                p.setFont("Helvetica", 10)
                p.drawString(30, y_pos, "Concepto")
                p.drawString(200, y_pos, "Emisión")
                p.drawString(280, y_pos, "Vencimiento")
                p.drawString(380, y_pos, "Monto")
                p.drawString(450, y_pos, "Estado")
                y_pos -= 20
            
            p.drawString(30, y_pos, str(cuota.concepto)[:30])
            p.drawString(200, y_pos, cuota.fecha_emision.strftime('%d/%m/%Y'))
            p.drawString(280, y_pos, cuota.fecha_vencimiento.strftime('%d/%m/%Y'))
            p.drawString(380, y_pos, f"${cuota.monto}")
            p.drawString(450, y_pos, "Pagada" if cuota.pagada else "Pendiente")
            y_pos -= 15
    else:
        p.drawString(30, y_pos, "No hay cuotas en este período")
        y_pos -= 15
    
    # Detalle de pagos
    y_pos -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, y_pos, "Detalle de Pagos")
    y_pos -= 20
    
    p.setFont("Helvetica", 10)
    pagos = estado_cuenta.obtener_detalle_pagos()
    if pagos:
        # Cabecera
        p.drawString(30, y_pos, "Fecha")
        p.drawString(100, y_pos, "Monto")
        p.drawString(170, y_pos, "Método")
        p.drawString(250, y_pos, "Referencia")
        p.drawString(400, y_pos, "Estado")
        y_pos -= 20
        
        # Detalle
        for pago in pagos:
            if y_pos < 50:  # Nueva página si no hay espacio
                p.showPage()
                y_pos = height - 50
                
                # Cabecera nueva página
                p.setFont("Helvetica-Bold", 14)
                p.drawString(30, y_pos, "Detalle de Pagos (continuación)")
                y_pos -= 20
                
                p.setFont("Helvetica", 10)
                p.drawString(30, y_pos, "Fecha")
                p.drawString(100, y_pos, "Monto")
                p.drawString(170, y_pos, "Método")
                p.drawString(250, y_pos, "Referencia")
                p.drawString(400, y_pos, "Estado")
                y_pos -= 20
            
            p.drawString(30, y_pos, pago.fecha_pago.strftime('%d/%m/%Y'))
            p.drawString(100, y_pos, f"${pago.monto}")
            p.drawString(170, y_pos, pago.get_metodo_pago_display())
            p.drawString(250, y_pos, pago.referencia[:30])
            p.drawString(400, y_pos, pago.get_estado_display())
            y_pos -= 15
    else:
        p.drawString(30, y_pos, "No hay pagos en este período")
    
    # Pie de página
    p.setFont("Helvetica", 8)
    p.drawString(30, 30, f"Sistema Torre Segura - Estado de Cuenta #{estado_cuenta.id}")
    p.drawString(width - 150, 30, f"Página 1")
    
    # Guardar el PDF
    p.showPage()
    p.save()
    
    # Crear respuesta
    buffer.seek(0)
    
    # Generar nombre del archivo
    filename = f"Estado_Cuenta_{estado_cuenta.vivienda.numero}_{estado_cuenta.fecha_inicio.strftime('%Y%m%d')}.pdf"
    
    # Actualizar el archivo en el modelo si no existe
    if not estado_cuenta.pdf_generado:
        # Guardar el PDF en el modelo
        from django.core.files.base import ContentFile
        estado_cuenta.pdf_generado.save(filename, ContentFile(buffer.getvalue()), save=True)
    
    # Devolver el PDF como respuesta
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def enviar_estado_cuenta(request, pk):
    """Vista para enviar estado de cuenta por email"""
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        raise PermissionDenied
    
    estado_cuenta = get_object_or_404(EstadoCuenta, pk=pk)
    
    # Verificar si hay un PDF generado
    if not estado_cuenta.pdf_generado:
        messages.error(request, 'Debe generar el PDF antes de enviarlo.')
        return redirect('estado-cuenta-detail', pk=pk)
    
    # Verificar si hay residentes con correo electrónico
    residentes = Residente.objects.filter(vivienda=estado_cuenta.vivienda, activo=True)
    destinatarios = [r.usuario.email for r in residentes if r.usuario.email]
    
    if not destinatarios:
        messages.error(request, 'No hay residentes con correo electrónico registrado.')
        return redirect('estado-cuenta-detail', pk=pk)
    
    if request.method == 'POST':
        # Simular envío de correo (en un entorno real se usaría Django Mail)
        # from django.core.mail import EmailMessage
        # message = EmailMessage(
        #     subject=f'Estado de Cuenta - {estado_cuenta.vivienda.numero}',
        #     body='Adjunto encontrará su estado de cuenta.',
        #     from_email='admin@torresegura.com',
        #     to=destinatarios,
        # )
        # message.attach_file(estado_cuenta.pdf_generado.path)
        # message.send()
        
        # Marcar como enviado
        estado_cuenta.marcar_como_enviado()
        messages.success(request, f'Estado de cuenta enviado a {len(destinatarios)} destinatarios.')
        return redirect('estado-cuenta-detail', pk=pk)
    
    return render(request, 'financiero/estado_cuenta_enviar.html', {
        'estado_cuenta': estado_cuenta,
        'residentes': residentes,
        'destinatarios': destinatarios
    })

@login_required
def generar_estados_cuenta(request):
    """Vista para generar estados de cuenta masivamente"""
    if not request.user.rol or request.user.rol.nombre != 'Administrador':
        raise PermissionDenied
    
    if request.method == 'POST':
        form = GenerarEstadosCuentaForm(request.POST)
        if form.is_valid():
            edificio = form.cleaned_data['edificio']
            viviendas_seleccionadas = form.cleaned_data['viviendas']
            aplicar_a_todas = form.cleaned_data['aplicar_a_todas']
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_fin = form.cleaned_data['fecha_fin']
            
            # Determinar las viviendas a las que aplicar
            if aplicar_a_todas:
                viviendas = Vivienda.objects.filter(activo=True)
            elif edificio:
                viviendas = Vivienda.objects.filter(edificio=edificio, activo=True)
            else:
                viviendas = viviendas_seleccionadas
            
            # Crear estados de cuenta para cada vivienda
            estados_creados = 0
            for vivienda in viviendas:
                # Verificar si ya existe un estado de cuenta para esta vivienda en el mismo período
                existe = EstadoCuenta.objects.filter(
                    vivienda=vivienda,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                ).exists()
                
                if not existe:
                    # Obtener el saldo anterior (último estado de cuenta)
                    saldo_anterior = 0
                    ultimo_estado = EstadoCuenta.objects.filter(
                        vivienda=vivienda,
                        fecha_fin__lt=fecha_inicio
                    ).order_by('-fecha_fin').first()
                    
                    if ultimo_estado:
                        saldo_anterior = ultimo_estado.saldo_final
                    
                    # Crear el estado de cuenta
                    estado = EstadoCuenta.objects.create(
                        vivienda=vivienda,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        saldo_anterior=saldo_anterior
                    )
                    
                    # Calcular totales
                    estado.calcular_totales()
                    estados_creados += 1
            
            messages.success(request, f'Se han generado {estados_creados} estados de cuenta exitosamente.')
            return redirect('estado-cuenta-list')
    else:
        form = GenerarEstadosCuentaForm()
    
    return render(request, 'financiero/estado_cuenta_generar.html', {'form': form})

# Dashboard Financiero

@login_required
def dashboard_financiero(request):
    """Vista para el dashboard financiero - VERSIÓN CORREGIDA"""
    user = request.user
    
    # Verificar permisos
    es_admin = user.rol and user.rol.nombre == 'Administrador'
    es_gerente = user.rol and user.rol.nombre == 'Gerente'
    es_residente = hasattr(user, 'residente') and user.rol and user.rol.nombre == 'Residente'
    
    if not (es_admin or es_gerente or es_residente):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    # Obtener vivienda del residente si aplica
    vivienda = None
    if es_residente:
        vivienda = user.residente.vivienda
    
    # FILTRADO SEGÚN ROL
    vivienda_id = request.GET.get('vivienda')
    edificio_id = request.GET.get('edificio')
    
    # Aplicar restricciones por rol
    if es_residente:
        vivienda_id = vivienda.id if vivienda else None
        edificio_id = None
    elif es_gerente and hasattr(user, 'gerente'):
        # ✅ CORREGIDO: Verificar que el gerente tenga edificio asignado
        if user.gerente and user.gerente.edificio:
            if edificio_id and edificio_id != str(user.gerente.edificio.id):
                edificio_id = str(user.gerente.edificio.id)
            elif not edificio_id:
                edificio_id = str(user.gerente.edificio.id)
            
            if vivienda_id:
                try:
                    vivienda_obj = Vivienda.objects.get(pk=vivienda_id)
                    if vivienda_obj.edificio != user.gerente.edificio:
                        vivienda_id = None
                except Vivienda.DoesNotExist:
                    vivienda_id = None
        else:
            # Si el gerente no tiene edificio asignado, no puede ver nada
            messages.error(request, 'Tu usuario gerente no tiene un edificio asignado.')
            return redirect('dashboard')
    
    # Período de tiempo
    hoy = timezone.now().date()
    
    # Calcular inicio y fin del mes actual
    inicio_mes_actual = hoy.replace(day=1)
    if hoy.month == 12:
        fin_mes_actual = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        fin_mes_actual = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
    
    # Mes anterior
    if hoy.month == 1:
        inicio_mes_anterior = hoy.replace(year=hoy.year - 1, month=12, day=1)
        fin_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
    else:
        inicio_mes_anterior = hoy.replace(month=hoy.month - 1, day=1)
        fin_mes_anterior = inicio_mes_actual - timedelta(days=1)
    
    # APLICAR FILTROS SEGÚN PERMISOS
    filters_pagos = {'estado': 'VERIFICADO'}
    filters_gastos = {'estado': 'PAGADO'}
    filters_cuotas = {'pagada': False}
    
    if vivienda_id:
        filters_pagos['vivienda_id'] = vivienda_id
        filters_cuotas['vivienda_id'] = vivienda_id
    elif edificio_id:
        filters_pagos['vivienda__edificio_id'] = edificio_id
        filters_cuotas['vivienda__edificio_id'] = edificio_id
    
    # CÁLCULOS FINANCIEROS DEL MES ACTUAL
    
    # Ingresos del mes actual
    ingresos_mes_actual = Pago.objects.filter(
        fecha_pago__gte=inicio_mes_actual,
        fecha_pago__lte=fin_mes_actual,
        **filters_pagos
    ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    # Gastos del mes actual (solo para admin/gerente)
    gastos_mes_actual = Decimal('0')
    if es_admin or es_gerente:
        gastos_filters = filters_gastos.copy()
        if edificio_id and not es_admin:
            gastos_filters['edificio_id'] = edificio_id
            
        gastos_mes_actual = Gasto.objects.filter(
            fecha__gte=inicio_mes_actual,
            fecha__lte=fin_mes_actual,
            **gastos_filters
        ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    # Balance del mes
    balance_mes_actual = ingresos_mes_actual - gastos_mes_actual
    
    # CÁLCULOS DEL MES ANTERIOR PARA TENDENCIAS
    ingresos_mes_anterior = Pago.objects.filter(
        fecha_pago__gte=inicio_mes_anterior,
        fecha_pago__lte=fin_mes_anterior,
        **filters_pagos
    ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    gastos_mes_anterior = Decimal('0')
    if es_admin or es_gerente:
        gastos_filters = filters_gastos.copy()
        if edificio_id and not es_admin:
            gastos_filters['edificio_id'] = edificio_id
            
        gastos_mes_anterior = Gasto.objects.filter(
            fecha__gte=inicio_mes_anterior,
            fecha__lte=fin_mes_anterior,
            **gastos_filters
        ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    # Calcular tendencias
    if ingresos_mes_anterior > 0:
        tendencia_ingresos = float((ingresos_mes_actual - ingresos_mes_anterior) / ingresos_mes_anterior * 100)
    else:
        tendencia_ingresos = 100.0 if ingresos_mes_actual > 0 else 0.0
        
    if gastos_mes_anterior > 0:
        tendencia_gastos = float((gastos_mes_actual - gastos_mes_anterior) / gastos_mes_anterior * 100)
    else:
        tendencia_gastos = 100.0 if gastos_mes_actual > 0 else 0.0
    
    # CUOTAS PENDIENTES Y VENCIDAS
    cuotas_pendientes = Cuota.objects.filter(**filters_cuotas).count()
    cuotas_vencidas = Cuota.objects.filter(
        fecha_vencimiento__lt=hoy,
        **filters_cuotas
    ).count()
    
    # Total por cobrar
    total_pendiente = Cuota.objects.filter(**filters_cuotas).aggregate(
        total=Coalesce(Sum(F('monto') + F('recargo')), Decimal('0'))
    )['total']
    
    # DATOS PARA GRÁFICOS - ÚLTIMOS 6 MESES
    datos_meses = []
    colores_categorias = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ]
    
    for i in range(5, -1, -1):  # Últimos 6 meses
        if hoy.month - i <= 0:
            mes_calculo = hoy.replace(year=hoy.year - 1, month=12 + (hoy.month - i))
        else:
            mes_calculo = hoy.replace(month=hoy.month - i)
        
        inicio_mes = mes_calculo.replace(day=1)
        if mes_calculo.month == 12:
            fin_mes = mes_calculo.replace(year=mes_calculo.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fin_mes = mes_calculo.replace(month=mes_calculo.month + 1, day=1) - timedelta(days=1)
        
        # Ingresos del mes
        ingresos = Pago.objects.filter(
            fecha_pago__gte=inicio_mes,
            fecha_pago__lte=fin_mes,
            **filters_pagos
        ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
        
        # Gastos del mes
        gastos = Decimal('0')
        if es_admin or es_gerente:
            gastos_filters = filters_gastos.copy()
            if edificio_id and not es_admin:
                gastos_filters['edificio_id'] = edificio_id
                
            gastos = Gasto.objects.filter(
                fecha__gte=inicio_mes,
                fecha__lte=fin_mes,
                **gastos_filters
            ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
        
        datos_meses.append({
            'mes': mes_calculo.strftime('%b %Y'),
            'ingresos': float(ingresos),
            'gastos': float(gastos),
            'balance': float(ingresos - gastos)
        })
    
    # DATOS PARA GRÁFICO DE GASTOS POR CATEGORÍA
    datos_categorias = []
    if es_admin or es_gerente:
        gastos_filters = filters_gastos.copy()
        if edificio_id and not es_admin:
            gastos_filters['edificio_id'] = edificio_id
            
        categorias_gastos = Gasto.objects.filter(
            fecha__gte=inicio_mes_actual,
            fecha__lte=fin_mes_actual,
            **gastos_filters
        ).values('categoria__nombre').annotate(
            total=Sum('monto')
        ).order_by('-total')
        
        for i, categoria in enumerate(categorias_gastos):
            datos_categorias.append({
                'categoria': categoria['categoria__nombre'],
                'monto': float(categoria['total']),
                'color': colores_categorias[i % len(colores_categorias)]
            })
    
    # ÚLTIMOS PAGOS Y GASTOS
    ultimos_pagos = Pago.objects.filter(**filters_pagos).select_related(
        'vivienda', 'vivienda__edificio'
    ).order_by('-fecha_pago')[:5]
    
    ultimos_gastos = []
    if es_admin or es_gerente:
        gastos_filters = filters_gastos.copy()
        if edificio_id and not es_admin:
            gastos_filters['edificio_id'] = edificio_id
            
        ultimos_gastos = Gasto.objects.filter(**gastos_filters).select_related(
            'categoria'
        ).order_by('-fecha')[:5]
    
    # OPCIONES PARA FILTROS
    edificios = Edificio.objects.all().order_by('nombre')  # ✅ CORREGIDO: Edificio no tiene campo 'activo'
    viviendas = Vivienda.objects.filter(activo=True)
    
    if es_gerente and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
        edificios = edificios.filter(id=user.gerente.edificio.id)  
        viviendas = viviendas.filter(edificio=user.gerente.edificio)
    elif es_residente:
        edificios = edificios.filter(id=vivienda.edificio.id) if vivienda else Edificio.objects.none()
        viviendas = Vivienda.objects.filter(id=vivienda.id) if vivienda else Vivienda.objects.none()
    
    # Información del edificio/vivienda seleccionado
    edificio_nombre = None
    vivienda_nombre = None
    
    if edificio_id:
        try:
            edificio_obj = Edificio.objects.get(pk=edificio_id)
            edificio_nombre = edificio_obj.nombre
        except Edificio.DoesNotExist:
            pass
    
    if vivienda_id:
        try:
            vivienda_obj = Vivienda.objects.get(pk=vivienda_id)
            vivienda_nombre = f"{vivienda_obj.numero} - {vivienda_obj.edificio.nombre}"
        except Vivienda.DoesNotExist:
            pass
    
    context = {
        'ingresos_mes_actual': ingresos_mes_actual,
        'gastos_mes_actual': gastos_mes_actual,
        'balance_mes_actual': balance_mes_actual,
        'tendencia_ingresos': tendencia_ingresos,
        'tendencia_gastos': tendencia_gastos,
        'cuotas_pendientes': cuotas_pendientes,
        'cuotas_vencidas': cuotas_vencidas,
        'total_pendiente': total_pendiente,
        'datos_meses': json.dumps(datos_meses),  # ✅ CORREGIDO: Convertir a JSON
        'datos_categorias': json.dumps(datos_categorias),  # ✅ CORREGIDO: Convertir a JSON
        'ultimos_pagos': ultimos_pagos,
        'ultimos_gastos': ultimos_gastos,
        'edificios': edificios,
        'viviendas': viviendas,
        'edificio_seleccionado': edificio_id,
        'vivienda_seleccionada': vivienda_id,
        'edificio_nombre': edificio_nombre,
        'vivienda_nombre': vivienda_nombre,
        'es_admin': es_admin,
        'es_gerente': es_gerente,
        'es_residente': es_residente,
    }
    
    return render(request, 'financiero/dashboard.html', context)

# APIs
@login_required
def api_cuotas_por_vivienda(request, vivienda_id):
    """API para obtener cuotas por vivienda - PERMISOS CORREGIDOS"""
    user = request.user
    
    # ✅ VERIFICAR PERMISOS
    es_admin = user.rol and user.rol.nombre == 'Administrador'
    es_gerente = user.rol and user.rol.nombre == 'Gerente'
    es_residente = hasattr(user, 'residente') and user.rol and user.rol.nombre == 'Residente'
    
    # Verificar acceso a la vivienda específica
    if es_residente:
        if user.residente.vivienda_id != vivienda_id:
            return JsonResponse({"error": "No tienes permisos para ver estas cuotas"}, status=403)
    elif es_gerente and hasattr(user, 'gerente'):
        try:
            vivienda = Vivienda.objects.get(pk=vivienda_id)
            if vivienda.edificio != user.gerente.edificio:
                return JsonResponse({"error": "No tienes permisos para ver estas cuotas"}, status=403)
        except Vivienda.DoesNotExist:
            return JsonResponse({"error": "Vivienda no encontrada"}, status=404)
    elif not es_admin:
        return JsonResponse({"error": "No tienes permisos para ver estas cuotas"}, status=403)
    
    # Obtener estado (todas, pendientes, vencidas)
    estado = request.GET.get('estado', 'pendientes')
    
    # Filtrar cuotas
    cuotas = Cuota.objects.filter(vivienda_id=vivienda_id)
    if estado == 'pendientes':
        cuotas = cuotas.filter(pagada=False)
    elif estado == 'vencidas':
        cuotas = cuotas.filter(pagada=False, fecha_vencimiento__lt=timezone.now().date())
    elif estado == 'pagadas':
        cuotas = cuotas.filter(pagada=True)
    
    # Ordenar
    cuotas = cuotas.order_by('-fecha_vencimiento')
    
    # Preparar datos
    data = []
    for cuota in cuotas:
        data.append({
            'id': cuota.id,
            'concepto': cuota.concepto.nombre,
            'monto': float(cuota.monto),
            'recargo': float(cuota.recargo),
            'total': float(cuota.total_a_pagar()),
            'fecha_emision': cuota.fecha_emision.strftime('%Y-%m-%d'),
            'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d'),
            'pagada': cuota.pagada,
            'vencida': timezone.now().date() > cuota.fecha_vencimiento and not cuota.pagada
        })
    
    return JsonResponse({"cuotas": data})

@login_required
def api_resumen_financiero(request):
    """API para obtener resumen financiero"""
    # Verificar permisos
    es_admin = request.user.rol and request.user.rol.nombre == 'Administrador'
    es_residente = hasattr(request.user, 'residente')
    
    if not (es_admin or es_residente):
        return JsonResponse({"error": "No tienes permisos para ver esta información"}, status=403)
    
    # Filtrar por vivienda si es residente
    vivienda_id = None
    if es_residente:
        vivienda_id = request.user.residente.vivienda_id
    else:
        vivienda_id = request.GET.get('vivienda')
    
    edificio_id = request.GET.get('edificio') if es_admin else None
    
    # Período
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    if hoy.month == 12:
        fin_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        fin_mes = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
    
    # Filtros
    filters_pagos = {'estado': 'VERIFICADO'}
    filters_cuotas = {'pagada': False}
    
    if vivienda_id:
        filters_pagos['vivienda_id'] = vivienda_id
        filters_cuotas['vivienda_id'] = vivienda_id
    elif edificio_id:
        filters_pagos['vivienda__edificio_id'] = edificio_id
        filters_cuotas['vivienda__edificio_id'] = edificio_id
    
    # Calcular ingresos del mes
    ingresos_mes = Pago.objects.filter(
        fecha_pago__gte=inicio_mes,
        fecha_pago__lte=fin_mes,
        **filters_pagos
    ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    # Calcular gastos del mes (solo para administradores)
    gastos_mes = Decimal('0')
    if es_admin:
        gastos_mes = Gasto.objects.filter(
            fecha__gte=inicio_mes,
            fecha__lte=fin_mes,
            estado='PAGADO'
        ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
    
    # Calcular balance
    balance_mes = ingresos_mes - gastos_mes
    
    # Calcular cuotas pendientes y vencidas
    cuotas_pendientes = Cuota.objects.filter(**filters_cuotas).count()
    cuotas_vencidas = Cuota.objects.filter(
        fecha_vencimiento__lt=hoy,
        **filters_cuotas
    ).count()
    
    # Calcular total por cobrar
    total_por_cobrar = Cuota.objects.filter(**filters_cuotas).aggregate(
        total=Coalesce(Sum(F('monto') + F('recargo')), Decimal('0'))
    )['total']
    
    data = {
        "ingresos_mes": float(ingresos_mes),
        "gastos_mes": float(gastos_mes),
        "balance_mes": float(balance_mes),
        "cuotas_pendientes": cuotas_pendientes,
        "cuotas_vencidas": cuotas_vencidas,
        "total_por_cobrar": float(total_por_cobrar)
    }
    
    return JsonResponse(data)

@login_required
def dashboard_financiero_api(request):
    """API específica para obtener datos de gráficos del dashboard"""
    user = request.user
    
    # Verificar permisos
    es_admin = user.rol and user.rol.nombre == 'Administrador'
    es_gerente = user.rol and user.rol.nombre == 'Gerente'
    es_residente = hasattr(user, 'residente') and user.rol and user.rol.nombre == 'Residente'
    
    if not (es_admin or es_gerente or es_residente):
        return JsonResponse({"error": "Sin permisos"}, status=403)
    
    # Obtener filtros
    vivienda_id = request.GET.get('vivienda')
    edificio_id = request.GET.get('edificio')
    
    # Aplicar restricciones por rol
    if es_residente:
        vivienda_id = user.residente.vivienda.id if hasattr(user, 'residente') and user.residente.vivienda else None
        edificio_id = None
    elif es_gerente and hasattr(user, 'gerente') and user.gerente and user.gerente.edificio:
        if edificio_id and edificio_id != str(user.gerente.edificio.id):
            edificio_id = str(user.gerente.edificio.id)
        elif not edificio_id:
            edificio_id = str(user.gerente.edificio.id)
    
    # Período de tiempo
    hoy = timezone.now().date()
    
    # Filtros base
    filters_pagos = {'estado': 'VERIFICADO'}
    filters_gastos = {'estado': 'PAGADO'}
    
    if vivienda_id:
        filters_pagos['vivienda_id'] = vivienda_id
    elif edificio_id:
        filters_pagos['vivienda__edificio_id'] = edificio_id
    
    # DATOS PARA GRÁFICOS - ÚLTIMOS 6 MESES
    datos_meses = []
    colores_categorias = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ]
    
    for i in range(5, -1, -1):  # Últimos 6 meses
        if hoy.month - i <= 0:
            mes_calculo = hoy.replace(year=hoy.year - 1, month=12 + (hoy.month - i))
        else:
            mes_calculo = hoy.replace(month=hoy.month - i)
        
        inicio_mes = mes_calculo.replace(day=1)
        if mes_calculo.month == 12:
            fin_mes = mes_calculo.replace(year=mes_calculo.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fin_mes = mes_calculo.replace(month=mes_calculo.month + 1, day=1) - timedelta(days=1)
        
        # Ingresos del mes
        ingresos = Pago.objects.filter(
            fecha_pago__gte=inicio_mes,
            fecha_pago__lte=fin_mes,
            **filters_pagos
        ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
        
        # Gastos del mes
        gastos = Decimal('0')
        if es_admin or es_gerente:
            gastos_filters = filters_gastos.copy()
            if edificio_id and not es_admin:
                gastos_filters['edificio_id'] = edificio_id
                
            gastos = Gasto.objects.filter(
                fecha__gte=inicio_mes,
                fecha__lte=fin_mes,
                **gastos_filters
            ).aggregate(total=Coalesce(Sum('monto', output_field=DecimalField()), Decimal('0')))['total']
        
        datos_meses.append({
            'mes': mes_calculo.strftime('%b %Y'),
            'ingresos': float(ingresos),
            'gastos': float(gastos),
            'balance': float(ingresos - gastos)
        })
    
    # DATOS PARA GRÁFICO DE GASTOS POR CATEGORÍA DEL MES ACTUAL
    inicio_mes_actual = hoy.replace(day=1)
    if hoy.month == 12:
        fin_mes_actual = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        fin_mes_actual = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
    
    datos_categorias = []
    if es_admin or es_gerente:
        gastos_filters = filters_gastos.copy()
        if edificio_id and not es_admin:
            gastos_filters['edificio_id'] = edificio_id
            
        categorias_gastos = Gasto.objects.filter(
            fecha__gte=inicio_mes_actual,
            fecha__lte=fin_mes_actual,
            **gastos_filters
        ).values('categoria__nombre').annotate(
            total=Sum('monto')
        ).order_by('-total')
        
        for i, categoria in enumerate(categorias_gastos):
            datos_categorias.append({
                'categoria': categoria['categoria__nombre'],
                'monto': float(categoria['total']),
                'color': colores_categorias[i % len(colores_categorias)]
            })
    
    return JsonResponse({
        'datos_meses': datos_meses,
        'datos_categorias': datos_categorias
    })