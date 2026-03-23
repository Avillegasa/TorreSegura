from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Cuota, Pago, PagoCuota
from .serializers import CuotaSerializer, PagoSerializer, RegistrarPagoSerializer


def _get_residente(user):
    """Obtiene el residente asociado al usuario, o None."""
    return getattr(user, "residente", None)


def _get_vivienda(user):
    """Obtiene la vivienda del residente autenticado."""
    residente = _get_residente(user)
    if residente and residente.vivienda:
        return residente.vivienda
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_cuotas_pendientes(request):
    """Cuotas pendientes (no pagadas) de la vivienda del residente."""
    vivienda = _get_vivienda(request.user)
    if not vivienda:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Actualizar recargos antes de devolver
    cuotas = Cuota.objects.filter(
        vivienda=vivienda, pagada=False
    ).select_related("concepto").order_by("fecha_vencimiento")

    for c in cuotas:
        c.actualizar_recargo()

    serializer = CuotaSerializer(cuotas, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_cuotas_pagadas(request):
    """Cuotas ya pagadas de la vivienda del residente."""
    vivienda = _get_vivienda(request.user)
    if not vivienda:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cuotas = (
        Cuota.objects.filter(vivienda=vivienda, pagada=True)
        .select_related("concepto")
        .order_by("-fecha_vencimiento")[:50]
    )
    serializer = CuotaSerializer(cuotas, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_pagos(request):
    """Historial de pagos realizados por el residente."""
    vivienda = _get_vivienda(request.user)
    if not vivienda:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pagos = (
        Pago.objects.filter(vivienda=vivienda)
        .prefetch_related("pagocuota_set__cuota__concepto")
        .order_by("-fecha_pago", "-id")[:50]
    )
    serializer = PagoSerializer(pagos, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def registrar_pago(request):
    """
    El residente registra un pago para una o varias cuotas.
    El pago queda en estado PENDIENTE hasta que el gerente lo verifique.
    """
    vivienda = _get_vivienda(request.user)
    residente = _get_residente(request.user)
    if not vivienda or not residente:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = RegistrarPagoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Verificar que las cuotas pertenecen a la vivienda y estan pendientes
    cuotas = Cuota.objects.filter(
        id__in=data["cuota_ids"],
        vivienda=vivienda,
        pagada=False,
    ).select_related("concepto")

    if cuotas.count() != len(data["cuota_ids"]):
        return Response(
            {"error": "Algunas cuotas no existen o ya fueron pagadas."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Calcular monto total
    monto_total = sum(c.total_a_pagar() for c in cuotas)

    # Crear el pago
    pago = Pago.objects.create(
        vivienda=vivienda,
        residente=residente,
        monto=monto_total,
        metodo_pago=data["metodo_pago"],
        referencia=data.get("referencia", ""),
        estado="PENDIENTE",
        notas=data.get("notas", ""),
        registrado_por=request.user,
    )

    # Crear relaciones PagoCuota
    for cuota in cuotas:
        PagoCuota.objects.create(
            pago=pago,
            cuota=cuota,
            monto_aplicado=cuota.total_a_pagar(),
        )

    return Response(
        {
            "mensaje": "Pago registrado exitosamente. Queda pendiente de verificacion.",
            "pago_id": pago.id,
            "monto": str(pago.monto),
            "estado": "PENDIENTE",
        },
        status=status.HTTP_201_CREATED,
    )
