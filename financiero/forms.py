# financiero/forms.py - VERSIÓN CORREGIDA CON VALIDACIONES MEJORADAS
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import (
    ConceptoCuota, Cuota, Pago, PagoCuota, 
    CategoriaGasto, Gasto, EstadoCuenta
)
from viviendas.models import Vivienda, Residente, Edificio

class ConceptoCuotaForm(forms.ModelForm):
    class Meta:
        model = ConceptoCuota
        fields = ['nombre', 'descripcion', 'monto_base', 'periodicidad', 'aplica_recargo', 'porcentaje_recargo', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'monto_base': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'porcentaje_recargo': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            if field_name not in ['aplica_recargo', 'activo']:
                field.widget.attrs['class'] = 'form-control'
        
        self.fields['aplica_recargo'].widget.attrs['class'] = 'form-check-input'
        self.fields['activo'].widget.attrs['class'] = 'form-check-input'
        
        # Mejorar help_text
        self.fields['monto_base'].help_text = 'Monto base en la moneda local'
        self.fields['porcentaje_recargo'].help_text = 'Porcentaje mensual de recargo por mora (0-100)'
    
    def clean_monto_base(self):
        monto = self.cleaned_data.get('monto_base')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto base debe ser mayor a cero.')
        return monto
    
    def clean_porcentaje_recargo(self):
        porcentaje = self.cleaned_data.get('porcentaje_recargo')
        if porcentaje is not None:
            if porcentaje < 0 or porcentaje > 100:
                raise ValidationError('El porcentaje debe estar entre 0 y 100.')
        return porcentaje

class CuotaForm(forms.ModelForm):
    class Meta:
        model = Cuota
        fields = ['concepto', 'vivienda', 'monto', 'fecha_emision', 'fecha_vencimiento', 'notas']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
            'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar campos
        self.fields['concepto'].queryset = ConceptoCuota.objects.filter(activo=True)
        self.fields['vivienda'].queryset = Vivienda.objects.filter(activo=True).select_related('edificio')
        
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Si es una cuota nueva, establecer fechas predeterminadas
        if not kwargs.get('instance'):
            self.fields['fecha_emision'].initial = timezone.now().date()
            self.fields['fecha_vencimiento'].initial = timezone.now().date() + timezone.timedelta(days=30)
        
        # Mejorar labels
        self.fields['concepto'].help_text = 'Tipo de cuota a generar'
        self.fields['vivienda'].help_text = 'Vivienda a la que se asigna la cuota'
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_emision = cleaned_data.get('fecha_emision')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')
        vivienda = cleaned_data.get('vivienda')
        
        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise ValidationError({'fecha_vencimiento': _('La fecha de vencimiento debe ser posterior a la fecha de emisión.')})
        
        # Validar que la vivienda esté activa
        if vivienda and not vivienda.activo:
            raise ValidationError({'vivienda': 'No se pueden generar cuotas para viviendas dadas de baja.'})
        
        return cleaned_data
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        return monto

class GenerarCuotasForm(forms.Form):
    concepto = forms.ModelChoiceField(
        queryset=ConceptoCuota.objects.filter(activo=True),
        label="Concepto de Cuota",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    edificio = forms.ModelChoiceField(
        queryset=Edificio.objects.all(),
        label="Edificio",
        required=False,
        empty_label="Seleccionar edificio",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    viviendas = forms.ModelMultipleChoiceField(
        queryset=Vivienda.objects.filter(activo=True),
        label="Viviendas específicas",
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': 10})
    )
    aplicar_a_todas = forms.BooleanField(
        label="Aplicar a todas las viviendas activas",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    fecha_emision = forms.DateField(
        label="Fecha de emisión",
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_vencimiento = forms.DateField(
        label="Fecha de vencimiento",
        initial=timezone.now().date() + timezone.timedelta(days=30),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    monto_personalizado = forms.DecimalField(
        label="Monto personalizado (opcional)",
        required=False,
        help_text="Dejar en blanco para usar el monto base del concepto",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        aplicar_a_todas = cleaned_data.get('aplicar_a_todas')
        viviendas = cleaned_data.get('viviendas')
        edificio = cleaned_data.get('edificio')
        fecha_emision = cleaned_data.get('fecha_emision')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')
        
        if not aplicar_a_todas and not viviendas and not edificio:
            raise ValidationError(_('Debe seleccionar viviendas específicas, un edificio, o marcar "Aplicar a todas"'))
        
        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise ValidationError({'fecha_vencimiento': _('La fecha de vencimiento debe ser posterior a la fecha de emisión.')})
        
        return cleaned_data

class PagoForm(forms.ModelForm):
    aplicar_a_cuotas = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Pago
        fields = ['vivienda', 'residente', 'monto', 'fecha_pago', 'metodo_pago', 'referencia', 'comprobante', 'notas']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
            'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Configurar campos
        self.fields['vivienda'].queryset = Vivienda.objects.filter(activo=True).select_related('edificio')
        self.fields['residente'].queryset = Residente.objects.filter(activo=True).select_related('usuario', 'vivienda')
        
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            if field_name not in ['aplicar_a_cuotas', 'comprobante']:
                field.widget.attrs['class'] = 'form-control'
        
        # Si es un pago nuevo, establecer fecha predeterminada
        if not kwargs.get('instance'):
            self.fields['fecha_pago'].initial = timezone.now().date()
        
        # Configurar cuotas pendientes si hay vivienda
        self._setup_cuotas_pendientes(kwargs)
        
        # Mejoras en help_text
        self.fields['referencia'].help_text = 'Número de transferencia, cheque o referencia del pago'
        self.fields['comprobante'].help_text = 'Imagen o PDF del comprobante de pago'
    
    def _setup_cuotas_pendientes(self, kwargs):
        """Configurar las cuotas pendientes para aplicar el pago"""
        vivienda_id = None
        
        # Obtener vivienda del objeto existente o de los datos POST
        if kwargs.get('instance') and kwargs['instance'].vivienda:
            vivienda_id = kwargs['instance'].vivienda.id
        elif hasattr(self, 'data') and self.data.get('vivienda'):
            vivienda_id = self.data.get('vivienda')
        
        if vivienda_id:
            try:
                vivienda = Vivienda.objects.get(pk=vivienda_id)
                cuotas_pendientes = Cuota.objects.filter(
                    vivienda=vivienda, 
                    pagada=False
                ).order_by('fecha_vencimiento')
                
                choices = []
                for cuota in cuotas_pendientes:
                    total_pagar = cuota.total_a_pagar()
                    vencida = " (VENCIDA)" if cuota.fecha_vencimiento < timezone.now().date() else ""
                    label = f"{cuota.concepto.nombre} - Vence: {cuota.fecha_vencimiento.strftime('%d/%m/%Y')} - ${total_pagar}{vencida}"
                    choices.append((cuota.id, label))
                
                self.fields['aplicar_a_cuotas'].choices = choices
                
                # Filtrar residentes de esa vivienda
                self.fields['residente'].queryset = Residente.objects.filter(
                    vivienda=vivienda, 
                    activo=True
                ).select_related('usuario')
                
            except Vivienda.DoesNotExist:
                self.fields['aplicar_a_cuotas'].choices = []
        else:
            self.fields['aplicar_a_cuotas'].choices = []
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        return monto
    
    def clean(self):
        cleaned_data = super().clean()
        vivienda = cleaned_data.get('vivienda')
        residente = cleaned_data.get('residente')
        
        # Validar que el residente pertenezca a la vivienda
        if vivienda and residente and residente.vivienda != vivienda:
            raise ValidationError({'residente': 'El residente seleccionado no pertenece a la vivienda indicada.'})
        
        # Validar que la vivienda esté activa
        if vivienda and not vivienda.activo:
            raise ValidationError({'vivienda': 'No se pueden registrar pagos para viviendas dadas de baja.'})
        
        return cleaned_data
    
    def save(self, commit=True):
        pago = super().save(commit=False)
        
        if self.usuario:
            pago.registrado_por = self.usuario
        
        if commit:
            pago.save()
            
            # Aplicar el pago a las cuotas seleccionadas
            cuotas_ids = self.cleaned_data.get('aplicar_a_cuotas', [])
            if cuotas_ids:
                self._aplicar_pago_a_cuotas(pago, cuotas_ids)
        
        return pago
    
    def _aplicar_pago_a_cuotas(self, pago, cuotas_ids):
        """Aplicar el pago a las cuotas seleccionadas"""
        monto_restante = pago.monto
        
        for cuota_id in cuotas_ids:
            if monto_restante <= 0:
                break
                
            try:
                cuota = Cuota.objects.get(pk=cuota_id, pagada=False)
                monto_aplicado = min(monto_restante, cuota.total_a_pagar())
                
                if monto_aplicado > 0:
                    PagoCuota.objects.create(
                        pago=pago,
                        cuota=cuota,
                        monto_aplicado=monto_aplicado
                    )
                    monto_restante -= monto_aplicado
                    
            except Cuota.DoesNotExist:
                continue

class CategoriaGastoForm(forms.ModelForm):
    class Meta:
        model = CategoriaGasto
        fields = ['nombre', 'descripcion', 'presupuesto_mensual', 'color', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'}),
            'presupuesto_mensual': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            if field_name != 'activo':
                field.widget.attrs['class'] = 'form-control'
        self.fields['activo'].widget.attrs['class'] = 'form-check-input'
        
        # Mejoras
        self.fields['presupuesto_mensual'].help_text = 'Presupuesto mensual estimado para esta categoría'
        self.fields['color'].help_text = 'Color para identificar la categoría en gráficos'
    
    def clean_presupuesto_mensual(self):
        presupuesto = self.cleaned_data.get('presupuesto_mensual')
        if presupuesto is not None and presupuesto < 0:
            raise ValidationError('El presupuesto no puede ser negativo.')
        return presupuesto

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['categoria', 'concepto', 'descripcion', 'monto', 'fecha', 
                 'proveedor', 'factura', 'comprobante', 'estado', 'tipo_gasto', 
                 'presupuestado', 'recurrente', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'notas': forms.Textarea(attrs={'rows': 2}),
            'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Configurar campos
        self.fields['categoria'].queryset = CategoriaGasto.objects.filter(activo=True)
        
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            if field_name not in ['comprobante', 'presupuestado', 'recurrente']:
                field.widget.attrs['class'] = 'form-control'
        
        self.fields['presupuestado'].widget.attrs['class'] = 'form-check-input'
        self.fields['recurrente'].widget.attrs['class'] = 'form-check-input'
        
        # Si es un gasto nuevo, establecer fecha predeterminada
        if not kwargs.get('instance'):
            self.fields['fecha'].initial = timezone.now().date()
        
        # Mejoras en help_text
        self.fields['factura'].help_text = 'Número de factura o recibo'
        self.fields['proveedor'].help_text = 'Nombre del proveedor o empresa'
        self.fields['presupuestado'].help_text = 'Marcar si este gasto estaba en el presupuesto'
        self.fields['recurrente'].help_text = 'Marcar si es un gasto que se repite mensualmente'
    
    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        return monto
    
    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha del gasto no puede ser futura.')
        return fecha
    
    def save(self, commit=True):
        gasto = super().save(commit=False)
        
        if self.usuario and not gasto.registrado_por:
            gasto.registrado_por = self.usuario
        
        if commit:
            gasto.save()
        
        return gasto

class EstadoCuentaForm(forms.ModelForm):
    class Meta:
        model = EstadoCuenta
        fields = ['vivienda', 'fecha_inicio', 'fecha_fin', 'saldo_anterior']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
            'saldo_anterior': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar campos
        self.fields['vivienda'].queryset = Vivienda.objects.filter(activo=True).select_related('edificio')
        
        # Agregar clases de Bootstrap
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Si es un estado de cuenta nuevo, establecer fechas predeterminadas
        if not kwargs.get('instance'):
            hoy = timezone.now().date()
            primer_dia_mes = hoy.replace(day=1)
            if hoy.month == 12:
                ultimo_dia_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timezone.timedelta(days=1)
            else:
                ultimo_dia_mes = hoy.replace(month=hoy.month + 1, day=1) - timezone.timedelta(days=1)
            
            self.fields['fecha_inicio'].initial = primer_dia_mes
            self.fields['fecha_fin'].initial = ultimo_dia_mes
        
        # Mejoras
        self.fields['saldo_anterior'].help_text = 'Saldo pendiente del período anterior'
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        vivienda = cleaned_data.get('vivienda')
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError({'fecha_fin': _('La fecha de fin debe ser posterior a la fecha de inicio.')})
        
        # Validar que la vivienda esté activa
        if vivienda and not vivienda.activo:
            raise ValidationError({'vivienda': 'No se pueden generar estados de cuenta para viviendas dadas de baja.'})
        
        # Verificar que no exista ya un estado de cuenta para el mismo período
        if vivienda and fecha_inicio and fecha_fin:
            existing = EstadoCuenta.objects.filter(
                vivienda=vivienda,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Ya existe un estado de cuenta para esta vivienda en el período seleccionado.')
        
        return cleaned_data

class GenerarEstadosCuentaForm(forms.Form):
    edificio = forms.ModelChoiceField(
        queryset=Edificio.objects.all(),
        label="Edificio",
        required=False,
        empty_label="Seleccionar edificio",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    viviendas = forms.ModelMultipleChoiceField(
        queryset=Vivienda.objects.filter(activo=True),
        label="Viviendas específicas",
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': 10})
    )
    aplicar_a_todas = forms.BooleanField(
        label="Aplicar a todas las viviendas activas",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        label="Fecha de fin",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar fechas predeterminadas del mes anterior
        hoy = timezone.now().date()
        primer_dia_mes_anterior = (hoy.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
        ultimo_dia_mes_anterior = hoy.replace(day=1) - timezone.timedelta(days=1)
        
        self.fields['fecha_inicio'].initial = primer_dia_mes_anterior
        self.fields['fecha_fin'].initial = ultimo_dia_mes_anterior
    
    def clean(self):
        cleaned_data = super().clean()
        aplicar_a_todas = cleaned_data.get('aplicar_a_todas')
        viviendas = cleaned_data.get('viviendas')
        edificio = cleaned_data.get('edificio')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if not aplicar_a_todas and not viviendas and not edificio:
            raise ValidationError(_('Debe seleccionar viviendas específicas, un edificio, o marcar "Aplicar a todas"'))
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError({'fecha_fin': _('La fecha de fin debe ser posterior a la fecha de inicio.')})
        
        return cleaned_data

# ===== FORMULARIOS ADICIONALES PARA FILTROS =====

class CuotaFiltroForm(forms.Form):
    """Formulario para filtrar cuotas"""
    concepto = forms.ModelChoiceField(
        queryset=ConceptoCuota.objects.filter(activo=True),
        required=False,
        empty_label="Todos los conceptos"
    )
    edificio = forms.ModelChoiceField(
        queryset=Edificio.objects.all(),
        required=False,
        empty_label="Todos los edificios"
    )
    vivienda = forms.ModelChoiceField(
        queryset=Vivienda.objects.filter(activo=True),
        required=False,
        empty_label="Todas las viviendas"
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todas'), ('pagada', 'Pagadas'), ('pendiente', 'Pendientes')],
        required=False
    )
    vencimiento = forms.ChoiceField(
        choices=[('', 'Todas'), ('vencidas', 'Vencidas'), ('proximas', 'Próximas a vencer')],
        required=False
    )

class PagoFiltroForm(forms.Form):
    """Formulario para filtrar pagos"""
    edificio = forms.ModelChoiceField(
        queryset=Edificio.objects.all(),
        required=False,
        empty_label="Todos los edificios"
    )
    vivienda = forms.ModelChoiceField(
        queryset=Vivienda.objects.filter(activo=True),
        required=False,
        empty_label="Todas las viviendas"
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Pago.ESTADO_CHOICES),
        required=False
    )
    metodo = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Pago.METODO_PAGO_CHOICES),
        required=False
    )