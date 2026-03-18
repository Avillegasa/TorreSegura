from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Alerta

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

class AlertaSerializer(serializers.ModelSerializer):
    enviado_por_info = UserSerializer(source='enviado_por', read_only=True)
    atendido_por_info = UserSerializer(source='atendido_por', read_only=True)
    
    class Meta:
        model = Alerta
        fields = [
            'id', 'tipo', 'descripcion', 'enviado_por', 'fecha',
            'estado', 'atendido_por', 'fecha_atencion',
            'enviado_por_info', 'atendido_por_info',
            'edificio', 'vivienda',
        ]
        read_only_fields = ['id', 'fecha', 'enviado_por']

class CrearAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = ['tipo', 'descripcion', 'edificio', 'vivienda']