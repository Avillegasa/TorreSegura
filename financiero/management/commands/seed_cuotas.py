"""
Crea cuotas de prueba para todas las viviendas que tengan residentes activos.
Uso: python manage.py seed_cuotas
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from financiero.models import ConceptoCuota, Cuota
from viviendas.models import Vivienda


class Command(BaseCommand):
    help = "Genera cuotas de prueba para las viviendas con residentes activos"

    def handle(self, *args, **options):
        # Crear concepto si no existe
        concepto, created = ConceptoCuota.objects.get_or_create(
            nombre="Cuota de mantenimiento",
            defaults={
                "descripcion": "Cuota mensual de mantenimiento del edificio",
                "monto_base": 500,
                "periodicidad": "MENSUAL",
                "aplica_recargo": True,
                "porcentaje_recargo": 2,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Concepto creado: {concepto}"))

        concepto_extra, created = ConceptoCuota.objects.get_or_create(
            nombre="Fondo de reserva",
            defaults={
                "descripcion": "Aporte al fondo de reserva del edificio",
                "monto_base": 150,
                "periodicidad": "MENSUAL",
                "aplica_recargo": False,
                "porcentaje_recargo": 0,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Concepto creado: {concepto_extra}"))

        viviendas = Vivienda.objects.filter(
            residentes__activo=True,
        ).distinct()

        if not viviendas.exists():
            self.stdout.write(self.style.WARNING("No hay viviendas con residentes activos."))
            return

        hoy = timezone.now().date()
        count = 0

        for viv in viviendas:
            for i in range(4):  # Ultimos 4 meses
                mes = hoy.month - i
                anio = hoy.year
                if mes <= 0:
                    mes += 12
                    anio -= 1
                fecha_emision = date(anio, mes, 1)
                fecha_vencimiento = date(anio, mes, 15)

                # Cuota de mantenimiento
                _, created = Cuota.objects.get_or_create(
                    concepto=concepto,
                    vivienda=viv,
                    fecha_emision=fecha_emision,
                    defaults={
                        "monto": concepto.monto_base,
                        "fecha_vencimiento": fecha_vencimiento,
                        "pagada": i >= 2,  # Los 2 mas viejos marcados como pagados
                    },
                )
                if created:
                    count += 1

            # Una cuota extra de fondo de reserva pendiente
            _, created = Cuota.objects.get_or_create(
                concepto=concepto_extra,
                vivienda=viv,
                fecha_emision=date(hoy.year, hoy.month, 1),
                defaults={
                    "monto": concepto_extra.monto_base,
                    "fecha_vencimiento": date(hoy.year, hoy.month, 20),
                    "pagada": False,
                },
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Se crearon {count} cuotas de prueba."))
