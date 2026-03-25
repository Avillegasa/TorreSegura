from rest_framework import serializers
from .models import Cuota, Pago, PagoCuota, ConceptoCuota


class ConceptoCuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptoCuota
        fields = ["id", "nombre", "periodicidad"]


class CuotaSerializer(serializers.ModelSerializer):
    concepto_nombre = serializers.CharField(source="concepto.nombre", read_only=True)
    total = serializers.SerializerMethodField()
    vivienda_nombre = serializers.SerializerMethodField()
    vencida = serializers.SerializerMethodField()

    class Meta:
        model = Cuota
        fields = [
            "id",
            "concepto_nombre",
            "vivienda_nombre",
            "monto",
            "recargo",
            "total",
            "fecha_emision",
            "fecha_vencimiento",
            "pagada",
            "vencida",
            "notas",
        ]

    def get_total(self, obj):
        return str(obj.total_a_pagar())

    def get_vivienda_nombre(self, obj):
        return str(obj.vivienda) if obj.vivienda else ""

    def get_vencida(self, obj):
        from django.utils import timezone
        return not obj.pagada and obj.fecha_vencimiento < timezone.now().date()


class PagoCuotaSerializer(serializers.ModelSerializer):
    cuota_descripcion = serializers.CharField(source="cuota.concepto.nombre", read_only=True)

    class Meta:
        model = PagoCuota
        fields = ["id", "cuota", "cuota_descripcion", "monto_aplicado"]


class PagoSerializer(serializers.ModelSerializer):
    cuotas_detalle = PagoCuotaSerializer(source="pagocuota_set", many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    metodo_display = serializers.CharField(source="get_metodo_pago_display", read_only=True)
    vivienda_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            "id",
            "vivienda_nombre",
            "monto",
            "fecha_pago",
            "metodo_pago",
            "metodo_display",
            "referencia",
            "estado",
            "estado_display",
            "notas",
            "cuotas_detalle",
        ]

    def get_vivienda_nombre(self, obj):
        return str(obj.vivienda) if obj.vivienda else ""


class RegistrarPagoSerializer(serializers.Serializer):
    """Serializer para que un residente registre un pago desde la app."""
    cuota_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1,
        help_text="Lista de IDs de cuotas a pagar",
    )
    metodo_pago = serializers.ChoiceField(choices=Pago.METODO_PAGO_CHOICES)
    referencia = serializers.CharField(max_length=100, required=False, default="")
    comprobante = serializers.FileField(required=False)
    notas = serializers.CharField(required=False, default="")
