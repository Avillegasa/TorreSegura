# viviendas/forms.py - VERSIÓN FINAL CORREGIDA
from django import forms
from django.utils import timezone
from .models import Edificio, Vivienda, Residente
import re
from usuarios.models import Usuario, Rol
from django.core.exceptions import ObjectDoesNotExist

class EdificioForm(forms.ModelForm):
    class Meta:
        model = Edificio
        fields = '__all__'
        widgets = {
            'fecha_construccion': forms.DateInput(attrs={'type': 'date'})
        }

class ViviendaForm(forms.ModelForm):
    class Meta:
        model = Vivienda
        # Excluir campos de baja para creación/edición normal
        fields = ['edificio', 'numero', 'piso', 'metros_cuadrados', 
                 'habitaciones', 'baños', 'estado']
        
    def __init__(self, *args, **kwargs):
        # ✅ CORRECCIÓN 1: Extraer user_actual antes de llamar super()
        self.user_actual = kwargs.pop('user_actual', None)
        super().__init__(*args, **kwargs)
        
        # ✅ CORRECCIÓN 2: Configurar edificios según el rol del usuario
        if self.user_actual and hasattr(self.user_actual, 'rol'):
            if self.user_actual.rol.nombre == "Gerente":
                if hasattr(self.user_actual, 'gerente') and self.user_actual.gerente.edificio:
                    self.fields['edificio'].queryset = Edificio.objects.filter(pk=self.user_actual.gerente.edificio.pk)
                    self.fields['edificio'].initial = self.user_actual.gerente.edificio
                    self.fields['edificio'].disabled = True  # Opcional: impedir que lo cambie
                else:
                    self.fields['edificio'].queryset = Edificio.objects.none()
            else:
                self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')
        else:
            self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')
        
        self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')
        # Opcional: personalizar el widget del estado para solo mostrar estados válidos
        if not self.instance.pk or self.instance.activo:
            # Para nuevas viviendas o viviendas activas
            self.fields['estado'].choices = [
                ('OCUPADO', 'Ocupado'),
                ('DESOCUPADO', 'Desocupado'), 
                ('MANTENIMIENTO', 'En mantenimiento'),
            ]
         # Mostrar solo el edificio asignado si es gerente
        if self.user_actual and hasattr(self.user_actual, 'rol'):
            if self.user_actual.rol.nombre == "Gerente":
                if hasattr(self.user_actual, 'gerente') and self.user_actual.gerente.edificio:
                    self.fields['edificio'].queryset = Edificio.objects.filter(pk=self.user_actual.gerente.edificio.pk)
                    self.fields['edificio'].initial = self.user_actual.gerente.edificio
                    self.fields['edificio'].disabled = True  # Opcional: impedir que lo cambie
                else:
                    self.fields['edificio'].queryset = Edificio.objects.none()
            else:
                self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')
    def clean_piso(self):
        piso = self.cleaned_data.get('piso')
        edificio = self.cleaned_data.get('edificio')

        if edificio and piso:
            if piso < 1:
                raise forms.ValidationError("El número de piso no puede ser menor a 1.")
            if piso > edificio.pisos:
                raise forms.ValidationError(
                    f"El edificio seleccionado tiene máximo {edificio.pisos} pisos."
                )
        return piso

class ViviendaBajaForm(forms.ModelForm):
    """
    Formulario para dar de baja una vivienda.
    Permite ingresar el motivo y la fecha de la baja.
    """
    fecha_baja = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date(),
        help_text="Fecha en la que se da de baja la vivienda."
    )
    
    motivo_baja = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        help_text="Motivo por el cual se da de baja la vivienda."
    )
    
    confirmar_residentes = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(),
        help_text="Confirmo que he revisado y entiendo que los residentes asociados a esta vivienda perderán su asignación."
    )
    
    class Meta:
        model = Vivienda
        fields = ['fecha_baja', 'motivo_baja']

class ResidenteCreationForm(forms.ModelForm):
    # Campos de Usuario (heredados)
    username = forms.CharField(max_length=150, required=True, label="Nombre de usuario")
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    telefono = forms.CharField(required=False)
    numero_documento = forms.CharField(label="CI", required=True)
    # ✅ CORRECCIÓN 3: Hacer contraseñas opcionales por defecto
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña", required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña", required=False)

    # Campos auxiliares
    edificio = forms.ModelChoiceField(queryset=Edificio.objects.all(), required=True)
    vivienda = forms.ModelChoiceField(queryset=Vivienda.objects.none(), required=True)

    class Meta:
        model = Residente
        fields = ['es_propietario', 'vehiculos', 'activo']

    def __init__(self, *args, **kwargs):
        self.user_actual = kwargs.pop('user_actual', None)
        super().__init__(*args, **kwargs)

        # ✅ CORRECCIÓN 4: Detectar si estamos editando
        self.is_editing = self.instance and self.instance.pk
        
        if self.is_editing:
            # En edición, prellenar campos con datos del usuario existente
            usuario = self.instance.usuario
            self.fields['username'].initial = usuario.username
            self.fields['email'].initial = usuario.email
            self.fields['first_name'].initial = usuario.first_name
            self.fields['last_name'].initial = usuario.last_name
            self.fields['telefono'].initial = usuario.telefono
            self.fields['numero_documento'].initial = usuario.numero_documento
            
            # Hacer las contraseñas opcionales en edición
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = "Déjalo vacío si no deseas cambiar la contraseña"
            self.fields['password2'].help_text = "Déjalo vacío si no deseas cambiar la contraseña"
            
            # Preseleccionar edificio y vivienda
            if self.instance.vivienda:
                self.fields['edificio'].initial = self.instance.vivienda.edificio
                self.initial['edificio'] = self.instance.vivienda.edificio.id
        else:
            # En creación, las contraseñas son obligatorias
            self.fields['password1'].required = True
            self.fields['password2'].required = True

        # Configurar queryset de edificios según el rol del usuario
        if self.user_actual and hasattr(self.user_actual, 'rol'):
            if self.user_actual.rol.nombre == 'Gerente':
                if hasattr(self.user_actual, 'gerente') and self.user_actual.gerente.edificio:
                    self.fields['edificio'].queryset = Edificio.objects.filter(pk=self.user_actual.gerente.edificio.pk)
                    self.fields['edificio'].initial = self.user_actual.gerente.edificio
                else:
                    self.fields['edificio'].queryset = Edificio.objects.none()
            else:
                self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')
        else:
            self.fields['edificio'].queryset = Edificio.objects.all().order_by('nombre')

        # Configurar queryset de viviendas
        self._setup_vivienda_queryset()

    
    def _setup_vivienda_queryset(self):
        """
        Configura el queryset de viviendas basado en el edificio seleccionado
        Versión corregida que evita problemas con SQLite y UNION
        """
        edificio_id = None
        
        # Determinar el edificio a usar
        if self.data:
            # Si hay datos POST, usar el edificio seleccionado en el formulario
            edificio_id = self.data.get('edificio')
        elif self.initial.get('edificio'):
            # Si hay datos iniciales, usar el edificio inicial
            edificio_id = self.initial.get('edificio')
        elif self.is_editing and self.instance.vivienda:
            # Si estamos editando, usar el edificio de la vivienda actual
            edificio_id = self.instance.vivienda.edificio_id

        if edificio_id:
            try:
                edificio_id = int(edificio_id)
                
                # ✅ SOLUCIÓN: Usar pk__in en lugar de UNION para evitar problemas con SQLite
                # Obtener IDs de viviendas activas del edificio
                vivienda_ids = list(
                    Vivienda.objects.filter(
                        edificio_id=edificio_id,
                        activo=True
                    ).values_list('id', flat=True)
                )
                
                # Si estamos editando, incluir la vivienda actual aunque esté inactiva
                if self.is_editing and self.instance.vivienda:
                    current_vivienda_id = self.instance.vivienda.id
                    if current_vivienda_id not in vivienda_ids:
                        vivienda_ids.append(current_vivienda_id)
                
                # Crear queryset final usando pk__in (compatible con SQLite)
                if vivienda_ids:
                    queryset = Vivienda.objects.filter(
                        pk__in=vivienda_ids
                    ).order_by('piso', 'numero')
                else:
                    queryset = Vivienda.objects.none()
                
                self.fields['vivienda'].queryset = queryset
                
                # Preseleccionar vivienda si estamos editando
                if self.is_editing and self.instance.vivienda:
                    self.fields['vivienda'].initial = self.instance.vivienda
                
            except (ValueError, TypeError, ObjectDoesNotExist):
                self.fields['vivienda'].queryset = Vivienda.objects.none()
        else:
            self.fields['vivienda'].queryset = Vivienda.objects.none()

    def clean_vivienda(self):
        """Validación personalizada para el campo vivienda"""
        vivienda = self.cleaned_data.get('vivienda')
        edificio = self.cleaned_data.get('edificio')
        
        if vivienda and edificio:
            # Verificar que la vivienda pertenece al edificio seleccionado
            if vivienda.edificio != edificio:
                raise forms.ValidationError("La vivienda seleccionada no pertenece al edificio elegido.")
            
            # Verificar que la vivienda está activa
            if not vivienda.activo:
                raise forms.ValidationError("No se puede asignar una vivienda que está dada de baja.")
        
        return vivienda
    
    def clean_email(self):
        """✅ CORRECCIÓN 5: Validación de email con exclusión en edición"""
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("El email es obligatorio.")
        
        # Verificar que no existe otro usuario con este email
        existing_users = Usuario.objects.filter(email=email)
        if self.is_editing and self.instance.usuario:
            existing_users = existing_users.exclude(pk=self.instance.usuario.pk)
        
        if existing_users.exists():
            raise forms.ValidationError("Ya existe un usuario con este email.")
        
        return email
    
    def clean_username(self):
        """✅ CORRECCIÓN 6: Validación de username con exclusión en edición"""
        username = self.cleaned_data.get('username', '').strip().lower()
        if not username:
            raise forms.ValidationError("Este campo es obligatorio.")
        if ' ' in username:
            raise forms.ValidationError("El nombre de usuario no debe contener espacios.")
        if len(username) > 150:
            raise forms.ValidationError("El nombre de usuario no debe tener más de 150 caracteres.")
        
        # Verificar que no existe otro usuario con este username
        existing_users = Usuario.objects.filter(username=username)
        if self.is_editing and self.instance.usuario:
            existing_users = existing_users.exclude(pk=self.instance.usuario.pk)
        
        if existing_users.exists():
            raise forms.ValidationError("Ya existe un usuario con este nombre de usuario.")
        
        return username

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        # ✅ CORRECCIÓN 7: Permitir teléfonos vacíos
        if telefono and not telefono.isdigit():
            raise forms.ValidationError("El teléfono solo debe contener números.")
        return telefono

    def clean_numero_documento(self):
        ci = self.cleaned_data.get('numero_documento', '').strip()
        if not ci.isdigit():
            raise forms.ValidationError("El CI solo debe contener números.")
        return ci
    
    def clean(self):
        """✅ CORRECCIÓN 8: Validación de contraseñas mejorada"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        # Solo validar contraseñas si estamos creando o si se proporcionaron
        if not self.is_editing:
            # En creación, las contraseñas son obligatorias
            if not password1:
                self.add_error('password1', "La contraseña es obligatoria.")
            if not password2:
                self.add_error('password2', "Debe confirmar la contraseña.")
        
        # Si se proporcionaron contraseñas, validar que coincidan
        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', "Las contraseñas no coinciden.")

        return cleaned_data

    def save(self, commit=True):
        """✅ CORRECCIÓN 9: Manejo completo de creación y edición"""
        if self.is_editing:
            # EDICIÓN: Actualizar usuario existente
            usuario = self.instance.usuario
            usuario.username = self.cleaned_data['username']
            usuario.email = self.cleaned_data['email']
            usuario.first_name = self.cleaned_data['first_name']
            usuario.last_name = self.cleaned_data['last_name']
            usuario.telefono = self.cleaned_data['telefono']
            usuario.numero_documento = self.cleaned_data['numero_documento']
            
            # Solo cambiar contraseña si se proporciona
            if self.cleaned_data.get('password1'):
                usuario.set_password(self.cleaned_data['password1'])
            
            if commit:
                usuario.save()
            
            # Actualizar el residente
            residente = super().save(commit=False)
            vivienda_anterior = self.instance.vivienda
            residente.vivienda = self.cleaned_data['vivienda']
            
            if commit:
                residente.save()
                
                # ✅ CORRECCIÓN 10: Manejar cambio de vivienda correctamente
                if vivienda_anterior != residente.vivienda:
                    # Liberar vivienda anterior si no quedan residentes activos
                    if vivienda_anterior:
                        otros_residentes = Residente.objects.filter(
                            vivienda=vivienda_anterior,
                            activo=True
                        ).exclude(pk=residente.pk).exists()
                        
                        if not otros_residentes:
                            vivienda_anterior.estado = 'DESOCUPADO'
                            vivienda_anterior.save()
                    
                    # Ocupar la nueva vivienda si el residente está activo
                    if residente.activo and residente.vivienda.estado == 'DESOCUPADO':
                        residente.vivienda.estado = 'OCUPADO'
                        residente.vivienda.save()
        else:
            # CREACIÓN: Crear nuevo usuario y residente
            usuario = Usuario.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password1'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                telefono=self.cleaned_data['telefono'],
                numero_documento=self.cleaned_data['numero_documento'],
            )

            # Asignar el rol automáticamente
            rol_residente, _ = Rol.objects.get_or_create(nombre='Residente')
            usuario.rol = rol_residente
            usuario.save()

            # Crear el residente
            residente = super().save(commit=False)
            residente.usuario = usuario
            residente.vivienda = self.cleaned_data['vivienda']

            if commit:
                residente.save()
                # Actualizar el estado de la vivienda si es necesario
                vivienda = residente.vivienda
                if vivienda.estado == 'DESOCUPADO' and residente.activo:
                    vivienda.estado = 'OCUPADO'
                    vivienda.save()

        return residente