from __future__ import annotations

from rest_framework import serializers

from .models import Visita


class VisitanteSerializer(serializers.ModelSerializer):
    # Campos "mobile" solicitados
    name = serializers.CharField(source="nombre_visitante", read_only=True)
    document = serializers.CharField(source="documento_visitante", read_only=True)
    purpose = serializers.CharField(source="motivo", read_only=True)
    entryDate = serializers.DateTimeField(source="fecha_hora_entrada", read_only=True)
    exitDate = serializers.DateTimeField(source="fecha_hora_salida", read_only=True)
    departmentNumber = serializers.SerializerMethodField()
    whoAuthorizes = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Visita
        fields = [
            "id",
            "name",
            "document",
            "purpose",
            "entryDate",
            "exitDate",
            "departmentNumber",
            "whoAuthorizes",
            "status",
        ]

    def get_departmentNumber(self, obj: Visita):
        vivienda = getattr(obj, "vivienda_destino", None)
        return getattr(vivienda, "numero", None) if vivienda else None

    def get_whoAuthorizes(self, obj: Visita):
        residente = getattr(obj, "residente_autoriza", None)
        usuario = getattr(residente, "usuario", None) if residente else None
        if not usuario:
            return None
        full_name = f"{usuario.first_name} {usuario.last_name}".strip()
        return full_name or getattr(usuario, "username", None)

    def get_status(self, obj: Visita):
        if getattr(obj, "fecha_hora_salida", None):
            return "departed"
        if getattr(obj, "qr_usado", False):
            return "scanned"
        return "pending"
