import hmac
import hashlib
from django.conf import settings

SECRET_QR_KEY = getattr(settings, "QR_SECRET_KEY", None) or getattr(settings, "SECRET_KEY")

def generar_firma_qr(id_visita: int, nonce: str | None = None) -> str:
    msg = f"visita:{id_visita}" if not nonce else f"visita:{id_visita}:{nonce}"
    return hmac.new(SECRET_QR_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()

def verificar_firma_qr(id_visita: int, firma_recibida: str, nonce: str | None = None) -> bool:
    firma_valida = generar_firma_qr(id_visita, nonce=nonce)
    return hmac.compare_digest(firma_valida, firma_recibida)
