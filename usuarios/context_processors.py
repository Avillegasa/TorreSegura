from .models import ClientePotencial

def clientes_potenciales_count(request):
    if request.user.is_authenticated and hasattr(request.user, 'rol') and request.user.rol.nombre == 'Administrador':
        return {
            'clientes_potenciales_count': ClientePotencial.objects.count()
        }
    return {}
