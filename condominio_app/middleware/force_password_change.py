from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import logout


class ForcePasswordChangeMiddleware:
    """
    Middleware que obliga a los usuarios con credenciales temporales
    a cambiar su contraseña antes de poder usar el sistema.
    También bloquea el acceso si las credenciales han expirado.
    """

    ALLOWED_URLS = [
        'forzar_cambio_password',
        'logout',
        'account_logout',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user

            # Verificar si las credenciales temporales han expirado
            if user.credenciales_expiradas and user.debe_cambiar_password:
                # Desactivar la cuenta
                user.is_active = False
                user.save(update_fields=['is_active'])
                logout(request)
                messages.error(
                    request,
                    'Tus credenciales temporales han expirado. Contacta al administrador.',
                    extra_tags='danger'
                )
                return redirect('login')

            # Verificar si debe cambiar la contraseña
            if user.debe_cambiar_password:
                resolved_url = request.resolver_match
                if resolved_url and resolved_url.url_name not in self.ALLOWED_URLS:
                    messages.warning(
                        request,
                        'Debes cambiar tu contraseña antes de continuar.'
                    )
                    return redirect('forzar_cambio_password')

        return self.get_response(request)
