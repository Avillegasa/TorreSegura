import hmac
import hashlib
import json
import qrcode
import io
import base64
import logging
from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

SECRET_QR_KEY = getattr(settings, "QR_SECRET_KEY", None) or getattr(settings, "SECRET_KEY")


def generar_firma_empleado(empleado_id):
    """Genera firma HMAC para el QR de empleado."""
    msg = f"empleado:{empleado_id}"
    return hmac.new(SECRET_QR_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()


def generar_qr_empleado(empleado):
    """
    Genera un QR de identificacion para un empleado.
    Contiene: id, nombre, puesto, edificio, firma HMAC.
    Retorna la imagen QR como bytes PNG.
    """
    datos = {
        "tipo": "empleado",
        "id": empleado.id,
        "nombre": f"{empleado.usuario.first_name} {empleado.usuario.last_name}",
        "puesto": empleado.puesto.nombre,
        "edificio": empleado.edificio.nombre if empleado.edificio else "Sin asignar",
        "firma": generar_firma_empleado(empleado.id),
    }

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(datos))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


def generar_qr_empleado_base64(empleado):
    """Retorna el QR como string base64."""
    png_bytes = generar_qr_empleado(empleado)
    return base64.b64encode(png_bytes).decode()


def enviar_qr_por_email(empleado):
    """
    Envia el QR de identificacion al email del empleado.
    Retorna True si se envio correctamente, False si fallo.
    """
    email = empleado.usuario.email
    if not email or '@noemail.com' in email:
        return False

    nombre = f"{empleado.usuario.first_name} {empleado.usuario.last_name}"
    edificio_nombre = empleado.edificio.nombre if empleado.edificio else "Sin asignar"

    qr_png = generar_qr_empleado(empleado)

    asunto = 'Torre Segura - Tu codigo QR de identificacion'
    mensaje = (
        f'Hola {nombre},\n\n'
        f'Se ha creado tu registro como empleado en Torre Segura.\n\n'
        f'Puesto: {empleado.puesto.nombre}\n'
        f'Edificio: {edificio_nombre}\n\n'
        f'Adjunto encontraras tu codigo QR de identificacion.\n'
        f'Este codigo sera utilizado para verificar tu identidad en el edificio.\n\n'
        f'Por favor, guarda este codigo en tu telefono o imprimelo.\n\n'
        f'Saludos,\n'
        f'Equipo Torre Segura'
    )

    try:
        email_msg = EmailMessage(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_msg.attach(
            f'qr_empleado_{empleado.id}.png',
            qr_png,
            'image/png'
        )
        email_msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error enviando QR a {email}: {e}")
        return False
