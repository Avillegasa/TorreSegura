from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        # Registrar señales (no depende de DB)
        from . import signals  # noqa: F401

        from .models import Rol
        roles_definidos = [
            ("Administrador", "Rol con acceso completo al sistema."),
            ("Gerente", "Encargado de la gestión del edificio."),
            ("Residente", "Persona que habita una vivienda."),
            ("Visitante", "Visitante autorizado por un residente."),
            ("Vigilante", "Encargado de la seguridad."),
            ("Personal", "Trabajador externo o de mantenimiento.")
        ]
        try:
            for nombre, descripcion in roles_definidos:
                Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion})
        except (OperationalError, ProgrammingError):
            # Se evita error si aún no se han ejecutado las migraciones
            pass
