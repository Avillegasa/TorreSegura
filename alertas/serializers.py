from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Alerta, Anuncio, OpcionVoto, Voto

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


# ─── Votación ─────────────────────────────────────────────────────────

class VotoSerializer(serializers.ModelSerializer):
    usuario_info = UserSerializer(source='usuario', read_only=True)

    class Meta:
        model = Voto
        fields = ['id', 'usuario', 'usuario_info', 'fecha']
        read_only_fields = ['id', 'usuario', 'fecha']


class OpcionVotoSerializer(serializers.ModelSerializer):
    cantidad_votos = serializers.IntegerField(read_only=True)
    # votos solo se incluye si la votación NO es anónima
    votos = VotoSerializer(many=True, read_only=True)

    class Meta:
        model = OpcionVoto
        fields = ['id', 'texto', 'orden', 'cantidad_votos', 'votos']


class OpcionVotoAnonimaSerializer(serializers.ModelSerializer):
    """Versión anónima: solo muestra conteo, no quién votó."""
    cantidad_votos = serializers.IntegerField(read_only=True)

    class Meta:
        model = OpcionVoto
        fields = ['id', 'texto', 'orden', 'cantidad_votos']


# ─── Anuncio ──────────────────────────────────────────────────────────

class AnuncioSerializer(serializers.ModelSerializer):
    autor_info = UserSerializer(source='autor', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    opciones = serializers.SerializerMethodField()
    votacion_abierta = serializers.BooleanField(read_only=True)
    total_votos = serializers.IntegerField(read_only=True)
    mi_voto = serializers.SerializerMethodField()

    class Meta:
        model = Anuncio
        fields = [
            'id', 'titulo', 'contenido', 'categoria', 'categoria_display',
            'autor', 'autor_info', 'edificio', 'fijado', 'activo',
            'es_votacion', 'voto_anonimo', 'fecha_cierre_votacion',
            'votacion_abierta', 'total_votos', 'opciones', 'mi_voto',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['id', 'autor', 'edificio', 'fecha_creacion', 'fecha_actualizacion']

    def get_opciones(self, obj):
        if not obj.es_votacion:
            return []
        opciones = obj.opciones.all()
        if obj.voto_anonimo:
            return OpcionVotoAnonimaSerializer(opciones, many=True).data
        return OpcionVotoSerializer(opciones, many=True).data

    def get_mi_voto(self, obj):
        """Devuelve el ID de la opción que el usuario actual votó, o null."""
        if not obj.es_votacion:
            return None
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        voto = Voto.objects.filter(
            opcion__anuncio=obj, usuario=request.user
        ).select_related('opcion').first()
        if voto:
            return voto.opcion_id
        return None


class CrearAnuncioSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    contenido = serializers.CharField()
    categoria = serializers.ChoiceField(choices=Anuncio.CATEGORIA_CHOICES, default='general')
    # Campos de votación (opcionales)
    es_votacion = serializers.BooleanField(default=False)
    voto_anonimo = serializers.BooleanField(default=False)
    fecha_cierre_votacion = serializers.DateTimeField(required=False, allow_null=True)
    opciones = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
    )
