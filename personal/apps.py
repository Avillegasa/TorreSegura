from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class PersonalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'personal'

    def ready(self):
        try:
            from .models import Puesto
            puestos_definidos = [
                ("Jardinero", "Encargado del mantenimiento de areas verdes"),
                ("Electricista", "Responsable de instalaciones electricas"),
                ("Pintor", "Realiza trabajos de pintura"),
                ("Otro", "Puesto personalizado"),
            ]
            for nombre, descripcion in puestos_definidos:
                Puesto.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion})

            # Desactivar puestos eliminados
            Puesto.objects.filter(
                nombre__in=['Auxiliar Administrativo', 'Conserje', 'Fontanero']
            ).update(activo=False)
        except (OperationalError, ProgrammingError):
            pass
