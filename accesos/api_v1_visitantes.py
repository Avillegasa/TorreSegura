from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Visita
from .serializers import VisitanteSerializer


class VisitanteViewSet(viewsets.ModelViewSet):
    """API móvil para gestionar visitantes (visitas).

    Model usado: accesos.Visita

    Roles:
    - Vigilante/Administrador/superuser: ve todas las visitas
    - Residente: solo visitas de su vivienda
    """

    serializer_class = VisitanteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # La app movil no maneja paginacion
    http_method_names = ["get", "delete", "patch", "head", "options"]

    def _rol(self) -> str | None:
        return getattr(getattr(self.request.user, "rol", None), "nombre", None)

    def _es_admin(self) -> bool:
        rol = self._rol()
        return bool(self.request.user.is_superuser or rol == "Administrador")

    def _es_vigilante(self) -> bool:
        return self._rol() == "Vigilante"

    def _es_residente(self) -> bool:
        return self._rol() == "Residente" and hasattr(self.request.user, "residente")

    def get_queryset(self):
        qs = (
            Visita.objects.all()
            .select_related(
                "vivienda_destino",
                "residente_autoriza__usuario",
            )
            .order_by("-fecha_hora_entrada")
        )

        if self._es_admin() or self._es_vigilante():
            pass
        elif self._es_residente():
            vivienda_id = getattr(self.request.user.residente, "vivienda_id", None)
            qs = qs.filter(vivienda_destino_id=vivienda_id)
        else:
            # Otros roles no tienen acceso
            qs = qs.none()

        # Filtro opcional: status=pending|scanned|departed
        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter == "pending":
                qs = qs.filter(qr_usado=False, fecha_hora_salida__isnull=True)
            elif status_filter == "scanned":
                qs = qs.filter(qr_usado=True, fecha_hora_salida__isnull=True)
            elif status_filter == "departed":
                qs = qs.filter(fecha_hora_salida__isnull=False)
            else:
                raise ValueError("status inválido. Use pending|scanned|departed")

        # Filtro por rango de fechas (máximo 1 mes hacia atrás)
        un_mes_atras = timezone.now() - timedelta(days=30)
        qs = qs.filter(fecha_hora_entrada__gte=un_mes_atras)

        # Filtro opcional: search (nombre o documento del visitante)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(nombre_visitante__icontains=search)
                | Q(documento_visitante__icontains=search)
            )

        return qs

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValueError as exc:
            return Response({"mensaje": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        return resp

    def destroy(self, request, *args, **kwargs):
        """Solo el residente puede eliminar sus invitaciones pendientes (QR no usado)."""
        visita = self.get_object()

        if not self._es_residente() and not self._es_admin():
            return Response(
                {"mensaje": "No tienes permisos para eliminar esta invitacion."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if self._es_residente():
            vivienda_id = getattr(request.user.residente, "vivienda_id", None)
            if visita.vivienda_destino_id != vivienda_id:
                return Response(
                    {"mensaje": "No puedes eliminar invitaciones de otra vivienda."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if visita.qr_usado:
            return Response(
                {"mensaje": "No se puede eliminar una invitacion ya escaneada."},
                status=status.HTTP_409_CONFLICT,
            )

        visita.delete()
        return Response(
            {"mensaje": "Invitacion eliminada correctamente."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="mark-exit")
    def mark_exit(self, request, pk=None):
        # Solo seguridad/admin
        rol = self._rol()
        if not (request.user.is_superuser or rol in ["Vigilante", "Administrador"]):
            return Response(
                {"mensaje": "No tienes permisos para marcar salida."},
                status=status.HTTP_403_FORBIDDEN,
            )

        visita = self.get_object()

        if visita.fecha_hora_salida:
            return Response(
                {"mensaje": "La visita ya tiene salida registrada."},
                status=status.HTTP_409_CONFLICT,
            )

        visita.fecha_hora_salida = timezone.now()
        visita.save(update_fields=["fecha_hora_salida"])

        serializer = self.get_serializer(visita)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def handle_exception(self, exc):
        """Normaliza errores a {mensaje: ...} (y opcionalmente errores: ...)."""
        response = super().handle_exception(exc)
        if response is None:
            return response

        data = getattr(response, "data", None)
        if isinstance(data, dict):
            if "mensaje" in data:
                return response
            if "detail" in data:
                response.data = {"mensaje": str(data.get("detail"))}
                return response
            # Errores de validación tipo {field: [..]}
            response.data = {"mensaje": "Datos inválidos", "errores": data}
            return response

        # Listas/strings
        response.data = {"mensaje": "Error", "errores": data}
        return response
