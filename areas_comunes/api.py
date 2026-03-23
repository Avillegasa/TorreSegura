from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AreaComun, Reserva
from .serializers import AreaComunSerializer, ReservaSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listar_areas(request):
    """Lista todas las areas comunes activas."""
    areas = AreaComun.objects.filter(activo=True).select_related("edificio")
    serializer = AreaComunSerializer(areas, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def crear_reserva(request, area_id):
    """Crea una reserva para un area comun. Solo residentes."""
    if not hasattr(request.user, "residente"):
        return Response(
            {"mensaje": "Solo los residentes pueden hacer reservas."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        area = AreaComun.objects.get(pk=area_id, activo=True)
    except AreaComun.DoesNotExist:
        return Response(
            {"mensaje": "Area comun no encontrada."},
            status=status.HTTP_404_NOT_FOUND,
        )

    fecha = request.data.get("fecha")
    hora_inicio = request.data.get("hora_inicio")
    hora_fin = request.data.get("hora_fin")
    motivo = request.data.get("motivo", "")

    if not fecha or not hora_inicio or not hora_fin:
        return Response(
            {"mensaje": "Fecha, hora de inicio y hora de fin son obligatorios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        reserva = Reserva(
            area_comun=area,
            residente=request.user.residente,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            motivo=motivo,
        )
        reserva.save()
    except ValidationError as e:
        msg = e.message if hasattr(e, "message") else str(e)
        if hasattr(e, "message_dict"):
            msg = " ".join(
                f"{v[0]}" if isinstance(v, list) else str(v)
                for v in e.message_dict.values()
            )
        return Response(
            {"mensaje": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReservaSerializer(reserva, context={"request": request})
    return Response(
        {"mensaje": "Reserva creada correctamente.", "reserva": serializer.data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listar_reservas_area(request, area_id):
    """Lista las reservas futuras de un area (para ver disponibilidad)."""
    hoy = date.today()
    reservas = (
        Reserva.objects.filter(
            area_comun_id=area_id,
            fecha__gte=hoy,
            estado__in=["pendiente", "confirmada"],
        )
        .select_related("residente__usuario", "area_comun")
        .order_by("fecha", "hora_inicio")
    )
    serializer = ReservaSerializer(reservas, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_reservas(request):
    """Lista las reservas del residente autenticado."""
    if not hasattr(request.user, "residente"):
        return Response(
            {"mensaje": "Solo los residentes tienen reservas."},
            status=status.HTTP_403_FORBIDDEN,
        )

    reservas = (
        Reserva.objects.filter(residente=request.user.residente)
        .select_related("area_comun", "residente__usuario")
        .order_by("-fecha", "-hora_inicio")[:50]
    )
    serializer = ReservaSerializer(reservas, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cancelar_reserva(request, reserva_id):
    """Cancela una reserva. Solo el residente dueno o admin."""
    try:
        reserva = Reserva.objects.select_related(
            "residente__usuario", "area_comun"
        ).get(pk=reserva_id)
    except Reserva.DoesNotExist:
        return Response(
            {"mensaje": "Reserva no encontrada."},
            status=status.HTTP_404_NOT_FOUND,
        )

    rol = getattr(getattr(request.user, "rol", None), "nombre", None)
    es_admin = request.user.is_superuser or rol == "Administrador"
    es_dueno = (
        hasattr(request.user, "residente")
        and reserva.residente_id == request.user.residente.pk
    )

    if not es_admin and not es_dueno:
        return Response(
            {"mensaje": "No tienes permisos para cancelar esta reserva."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if reserva.estado == "cancelada":
        return Response(
            {"mensaje": "La reserva ya esta cancelada."},
            status=status.HTTP_409_CONFLICT,
        )

    if reserva.estado == "completada":
        return Response(
            {"mensaje": "No se puede cancelar una reserva completada."},
            status=status.HTTP_409_CONFLICT,
        )

    reserva.estado = "cancelada"
    reserva.save(update_fields=["estado", "updated_at"])

    serializer = ReservaSerializer(reserva, context={"request": request})
    return Response(
        {"mensaje": "Reserva cancelada correctamente.", "reserva": serializer.data}
    )
