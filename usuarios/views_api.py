from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, serializers
from .models import Usuario
from .serializers import UsuarioSerializer
from rest_framework.permissions import IsAuthenticated
from usuarios.validaciones_movil import validar_rol_para_api
from rest_framework.exceptions import APIException
from django.contrib.auth import authenticate, get_user_model
from allauth.account.utils import send_email_confirmation
from django.db.models import Q
from allauth.account.models import EmailAddress
User = get_user_model()
# Excepción personalizada para devolver un mensaje con estructura clara
class CustomLoginRoleException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = {"error": "Su rol debe ingresar desde la web"}
    default_code = "invalid_login"

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        login_input = attrs.get("username")  # Aquí puede ser username o email
        password = attrs.get("password")

        if not login_input or not password:
            raise serializers.ValidationError({"error": "Se requieren todos los campos"})

        try:
            user = User.objects.get(Q(username=login_input) | Q(email=login_input))
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "Credenciales incorrectas"})

        if not user.check_password(password):
            raise serializers.ValidationError({"error": "Credenciales incorrectas"})

        if not validar_rol_para_api(user):
            raise serializers.ValidationError({"error": "Su rol debe ingresar desde la web"})

        # Si las credenciales temporales expiraron, bloquear
        if getattr(user, 'debe_cambiar_password', False) and user.credenciales_expiradas:
            raise serializers.ValidationError({"error": "Tus credenciales temporales han expirado. Contacta al administrador."})

        # Si debe cambiar contraseña, permitir login pero con flag
        if getattr(user, 'debe_cambiar_password', False):
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UsuarioSerializer(user).data,
                "debe_cambiar_password": True,
                "mensaje": "Debes cambiar tu contraseña. Revisa tu correo electrónico y usa el enlace para crear tu contraseña definitiva."
            }

        # Crear o actualizar el objeto EmailAddress para asegurar que sea primario
        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": False}
        )
        # Si ya existía, asegurar que sea primario
        if not email_address.primary:       
            email_address.primary = True
            email_address.save()

        # Enviar confirmación si no está verificado
        if not email_address.verified:
            send_email_confirmation(self.context['request'], user)
            raise serializers.ValidationError({"error": "Debe verificar su correo electrónico. Se le envió un correo con el enlace de confirmación."})

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UsuarioSerializer(user).data,
            "debe_cambiar_password": False
        }

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuario_actual(request):
    usuario = request.user
    serializer = UsuarioSerializer(usuario)
    return Response(serializer.data)


