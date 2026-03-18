from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field, user_username
from usuarios.models import Rol


class CustomAccountAdapter(DefaultAccountAdapter):
    \"\"\"
    Adaptador que restringe el login web solo a roles Admin/Gerente.
    Los demás roles deben usar la app móvil.
    \"\"\"
    def is_open_for_signup(self, request):
        return False  # No permitir registro vía allauth web

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptador personalizado para manejar la creación y configuración de usuarios 
    cuando se autentican a través de proveedores sociales como Google.
    """
    
    def populate_user(self, request, sociallogin, data):
        """
        Poblar los campos del usuario con los datos del proveedor social.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Asignar un rol por defecto (generalmente 'Residente' para nuevos usuarios)
        # Este rol puede ser cambiado posteriormente por un administrador
        try:
            rol_residente = Rol.objects.get(nombre='Residente')
            user.rol = rol_residente
        except Rol.DoesNotExist:
            # Si no existe el rol, se deja sin asignar
            pass
        
        # Asignar otros campos adicionales si están disponibles
        if 'picture' in data:
            # La imagen de perfil se maneja normalmente a través de URL, 
            # pero podría implementarse su descarga e importación
            # user.foto_url = data.get('picture')
            pass
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Guardar el usuario y realizar acciones adicionales después de su creación.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Aquí podríamos enviar un correo de bienvenida, crear registros asociados, etc.
        
        return user
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Determina si un usuario puede registrarse a través de una cuenta social.
        Por defecto está permitido, pero podría restringirse según ciertas condiciones.
        """
        # Por ejemplo, solo permitir usuarios con correos de dominio específico
        email = sociallogin.user.email
        allowed_domains = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com']
        
        if email:
            domain = email.split('@')[1]
            if domain not in allowed_domains:
                return False
        
        return True