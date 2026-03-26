import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CuentaBancaria, Cuota, Pago, PagoCuota, PagoQR
from .serializers import CuotaSerializer, PagoSerializer, RegistrarPagoSerializer

logger = logging.getLogger(__name__)


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


# ─── Endpoints QR BNB ────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generar_qr_pago(request):
    """
    Genera un QR de pago BNB para una o varias cuotas.

    Body: { "cuota_ids": [1, 2, 3] }

    Flujo:
      1. Valida que las cuotas pertenezcan al residente y estén pendientes
      2. Calcula el monto total
      3. Llama a BNB para generar el QR
      4. Guarda PagoQR con el qr_id y la imagen
      5. Retorna la imagen QR en base64 + qr_id para que la app la muestre
    """
    vivienda = _get_vivienda(request.user)
    residente = _get_residente(request.user)
    if not vivienda or not residente:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cuota_ids = request.data.get("cuota_ids", [])
    if not cuota_ids:
        return Response(
            {"error": "Debes seleccionar al menos una cuota."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validar cuotas
    cuotas = Cuota.objects.filter(
        id__in=cuota_ids, vivienda=vivienda, pagada=False
    ).select_related("concepto")

    if cuotas.count() != len(cuota_ids):
        return Response(
            {"error": "Algunas cuotas no existen o ya fueron pagadas."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verificar que no haya un QR activo para estas mismas cuotas
    qr_activo = PagoQR.objects.filter(
        vivienda=vivienda,
        qr_estado="GENERADO",
        fecha_expiracion__gte=timezone.now().date(),
        cuotas__in=cuotas,
    ).first()

    if qr_activo:
        return Response({
            "qr_id": qr_activo.qr_id,
            "qr_image": qr_activo.qr_image,
            "monto": str(qr_activo.monto),
            "glosa": qr_activo.glosa,
            "fecha_expiracion": str(qr_activo.fecha_expiracion),
            "mensaje": "Ya tienes un QR activo para estas cuotas.",
        })

    # Calcular monto y generar glosa
    for c in cuotas:
        c.actualizar_recargo()

    monto_total = sum(c.total_a_pagar() for c in cuotas)
    conceptos = ", ".join(set(c.concepto.nombre for c in cuotas))
    glosa = f"Expensa {vivienda} - {conceptos}"[:200]

    # Buscar cuenta bancaria del edificio
    edificio = vivienda.edificio if vivienda else None
    if not edificio:
        return Response(
            {"error": "Tu vivienda no tiene un edificio asignado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cuenta = CuentaBancaria.objects.get(edificio=edificio)
    except CuentaBancaria.DoesNotExist:
        return Response(
            {"error": "El edificio no tiene una cuenta bancaria configurada. Contacta al administrador."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not cuenta.esta_lista():
        return Response(
            {"error": "La cuenta bancaria del edificio no está verificada. Contacta al administrador."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Llamar al servicio BNB con las credenciales del edificio
    from .services.bnb_payment import BNBPaymentService, BNBPaymentError

    try:
        bnb = BNBPaymentService(
            account_id=cuenta.bnb_account_id,
            authorization_id=cuenta.bnb_authorization_id,
        )
        resultado = bnb.generar_qr(
            monto=str(monto_total),
            glosa=glosa,
            moneda="BOB",
            uso_unico=True,
            dias_expiracion=3,
        )
    except BNBPaymentError as e:
        logger.error("Error BNB al generar QR: %s", e)
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Guardar PagoQR
    pago_qr = PagoQR.objects.create(
        vivienda=vivienda,
        residente=residente,
        monto=monto_total,
        glosa=glosa,
        qr_id=resultado["qr_id"],
        qr_image=resultado["qr_image_base64"],
        fecha_expiracion=resultado["expiration_date"],
    )
    pago_qr.cuotas.set(cuotas)

    return Response(
        {
            "qr_id": pago_qr.qr_id,
            "qr_image": pago_qr.qr_image,
            "monto": str(pago_qr.monto),
            "glosa": pago_qr.glosa,
            "fecha_expiracion": str(pago_qr.fecha_expiracion),
            "mensaje": "QR generado exitosamente. Escanéalo con tu app bancaria.",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verificar_qr_pago(request, qr_id):
    """
    Consulta el estado de un QR en BNB y actualiza localmente.

    Si BNB reporta que fue pagado:
      1. Crea un Pago verificado automáticamente
      2. Crea los PagoCuota correspondientes
      3. Marca las cuotas como pagadas
    """
    vivienda = _get_vivienda(request.user)
    if not vivienda:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pago_qr = PagoQR.objects.get(qr_id=qr_id, vivienda=vivienda)
    except PagoQR.DoesNotExist:
        return Response(
            {"error": "QR no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Si ya fue procesado, retornar estado actual
    if pago_qr.qr_estado != "GENERADO":
        return Response({
            "qr_id": pago_qr.qr_id,
            "estado": pago_qr.qr_estado,
            "pago_id": pago_qr.pago_id,
            "mensaje": f"QR ya procesado: {pago_qr.get_qr_estado_display()}",
        })

    # Obtener credenciales del edificio
    edificio = pago_qr.vivienda.edificio if pago_qr.vivienda else None
    try:
        cuenta = CuentaBancaria.objects.get(edificio=edificio)
    except CuentaBancaria.DoesNotExist:
        return Response(
            {"error": "Cuenta bancaria no configurada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Consultar BNB
    from .services.bnb_payment import BNBPaymentService, BNBPaymentError, QR_STATUS_PAID, QR_STATUS_EXPIRED

    try:
        bnb = BNBPaymentService(
            account_id=cuenta.bnb_account_id,
            authorization_id=cuenta.bnb_authorization_id,
        )
        resultado = bnb.consultar_estado(qr_id)
    except BNBPaymentError as e:
        logger.error("Error BNB al verificar QR %s: %s", qr_id, e)
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    bnb_status = resultado["status"]

    if bnb_status == QR_STATUS_PAID:
        # Crear Pago verificado automáticamente
        pago = Pago.objects.create(
            vivienda=pago_qr.vivienda,
            residente=pago_qr.residente,
            monto=pago_qr.monto,
            metodo_pago="QR_BNB",
            referencia=f"QR-{pago_qr.qr_id}",
            estado="VERIFICADO",
            notas=f"Pago automático via QR BNB. Glosa: {pago_qr.glosa}",
            registrado_por=request.user,
            verificado_por=request.user,
            fecha_verificacion=timezone.now(),
        )

        # Crear PagoCuota para cada cuota
        for cuota in pago_qr.cuotas.all():
            PagoCuota.objects.create(
                pago=pago,
                cuota=cuota,
                monto_aplicado=cuota.total_a_pagar(),
            )

        pago_qr.marcar_pagado(pago)

        return Response({
            "qr_id": pago_qr.qr_id,
            "estado": "PAGADO",
            "pago_id": pago.id,
            "monto": str(pago.monto),
            "mensaje": "Pago confirmado exitosamente.",
        })

    elif bnb_status == QR_STATUS_EXPIRED:
        pago_qr.marcar_expirado()
        return Response({
            "qr_id": pago_qr.qr_id,
            "estado": "EXPIRADO",
            "mensaje": "El QR ha expirado. Genera uno nuevo.",
        })

    # QR aún no usado
    return Response({
        "qr_id": pago_qr.qr_id,
        "estado": "GENERADO",
        "mensaje": "Pago aún no realizado. Escanea el QR con tu app bancaria.",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_qr_pendientes(request):
    """Lista los QRs activos (no expirados, no pagados) del residente."""
    vivienda = _get_vivienda(request.user)
    if not vivienda:
        return Response(
            {"error": "No tienes una vivienda asignada."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qrs = PagoQR.objects.filter(
        vivienda=vivienda,
        qr_estado="GENERADO",
        fecha_expiracion__gte=timezone.now().date(),
    ).order_by("-fecha_creacion")

    data = []
    for qr in qrs:
        cuotas_names = [c.concepto.nombre for c in qr.cuotas.select_related("concepto")]
        data.append({
            "qr_id": qr.qr_id,
            "monto": str(qr.monto),
            "glosa": qr.glosa,
            "qr_image": qr.qr_image,
            "fecha_expiracion": str(qr.fecha_expiracion),
            "cuotas": cuotas_names,
        })

    return Response(data)
