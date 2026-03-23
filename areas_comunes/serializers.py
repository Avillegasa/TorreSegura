from rest_framework import serializers
from .models import AreaComun, Reserva


class AreaComunSerializer(serializers.ModelSerializer):
    buildingName = serializers.CharField(source="edificio.nombre", read_only=True)
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = AreaComun
        fields = [
            "id",
            "nombre",
            "descripcion",
            "buildingName",
            "capacidad_maxima",
            "horario_inicio",
            "horario_fin",
            "imageUrl",
            "activo",
        ]

    def get_imageUrl(self, obj):
        if obj.imagen:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None


class ReservaSerializer(serializers.ModelSerializer):
    areaNombre = serializers.CharField(source="area_comun.nombre", read_only=True)
    residenteNombre = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = [
            "id",
            "area_comun",
            "areaNombre",
            "residenteNombre",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "estado",
            "motivo",
            "created_at",
        ]
        read_only_fields = ["id", "areaNombre", "residenteNombre", "created_at"]

    def get_residenteNombre(self, obj):
        usuario = getattr(obj.residente, "usuario", None)
        if not usuario:
            return None
        full_name = f"{usuario.first_name} {usuario.last_name}".strip()
        return full_name or usuario.username
