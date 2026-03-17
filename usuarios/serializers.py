from rest_framework import serializers 
from .models import Usuario, Rol,  ClientePotencial
from viviendas.models import Residente
class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion']

class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)
    vivienda_id = serializers.SerializerMethodField() 

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'telefono', 'tipo_documento', 'numero_documento',
            'foto', 'vivienda_id' 
        ]

    def get_vivienda_id(self, obj):
        try:
            return obj.residente.vivienda.id if obj.residente and obj.residente.vivienda else None
        except Exception:
            return None


class ClientePotencialSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ClientePotencial
    """
    fecha_contacto = serializers.DateTimeField(format='%d/%m/%Y %H:%M', read_only=True)
    
    class Meta:
        model = ClientePotencial
        fields = [
            'id',
            'nombre_completo',
            'telefono',
            'email',
            'ubicacion',
            'mensaje',
            'fecha_contacto'
        ]
        read_only_fields = ['id', 'fecha_contacto']
    
    def validate_email(self, value):
        """
        Validar formato de email
        """
        if not '@' in value or not '.' in value:
            raise serializers.ValidationError("El formato del email no es válido")
        return value.lower().strip()
    
    def validate_nombre_completo(self, value):
        """
        Validar nombre completo
        """
        if len(value.strip()) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres")
        return value.strip()
    
    def validate_telefono(self, value):
        """
        Validar teléfono (opcional pero si se proporciona debe ser válido)
        """
        if value and len(value.strip()) < 6:
            raise serializers.ValidationError("El teléfono debe tener al menos 6 dígitos")
        return value.strip()

class ClientePotencialCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para crear ClientePotencial desde el frontend
    """
    class Meta:
        model = ClientePotencial
        fields = [
            'nombre_completo',
            'telefono', 
            'email',
            'ubicacion',
            'mensaje'
        ]
    
    def validate(self, data):
        """
        Validaciones a nivel de objeto
        """
        # Verificar si ya existe un cliente con el mismo email
        email = data.get('email', '').lower().strip()
        if ClientePotencial.objects.filter(email=email).exists():
            # En lugar de error, puedes decidir si actualizar o crear uno nuevo
            pass  # Por ahora permitimos duplicados, pero puedes cambiar esta lógica
        
        return data
    
    def create(self, validated_data):
        """
        Crear cliente potencial con datos limpios
        """
        # Limpiar todos los campos de texto
        for field in ['nombre_completo', 'telefono', 'email', 'ubicacion', 'mensaje']:
            if field in validated_data and validated_data[field]:
                validated_data[field] = validated_data[field].strip()
        
        # Normalizar email
        if 'email' in validated_data:
            validated_data['email'] = validated_data['email'].lower()
        
        return super().create(validated_data)