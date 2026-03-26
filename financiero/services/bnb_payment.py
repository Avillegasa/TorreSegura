"""
Servicio de integración con la API QR Simple de BNB (Banco Nacional de Bolivia).

Flujo:
  1. Autenticarse con accountId + authorizationId → obtener Bearer token
  2. Generar QR de pago con monto, moneda, glosa y expiración
  3. Consultar estado del QR (1=No usado, 2=Pagado, 3=Expirado, 4=Error)

Configuración requerida en .env:
  BNB_ACCOUNT_ID=<proporcionado por BNB>
  BNB_AUTHORIZATION_ID=<proporcionado por BNB>
  BNB_SANDBOX=True  (False para producción)
"""

import base64
import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ─── URLs del sandbox y producción ────────────────────────────────────

SANDBOX_AUTH_URL = "https://clientauthenticationapiv2.azurewebsites.net/api/v1/auth/token"
SANDBOX_QR_BASE = "https://qrsimpleapiv2.azurewebsites.net/api/v1/main"

# TODO: Reemplazar con URLs reales de producción cuando BNB las proporcione
PROD_AUTH_URL = "https://api.bnb.com.bo/ClientAuthentication/api/v1/auth/token"
PROD_QR_BASE = "https://api.bnb.com.bo/QRSimple/api/v1/main"

# Cache key para el token (expira en 50 min para renovar antes de los 60)
TOKEN_CACHE_KEY = "bnb_api_token"
TOKEN_CACHE_TTL = 50 * 60  # 50 minutos

# Status codes del QR
QR_STATUS_NOT_USED = 1
QR_STATUS_PAID = 2
QR_STATUS_EXPIRED = 3
QR_STATUS_ERROR = 4


class BNBPaymentError(Exception):
    """Error genérico de la integración BNB."""
    pass


class BNBPaymentService:
    """Cliente para la API QR Simple v2 de BNB."""

    def __init__(self, account_id=None, authorization_id=None):
        """
        Args:
            account_id: Credencial BNB (si None, usa settings globales como fallback)
            authorization_id: Credencial BNB (si None, usa settings globales como fallback)
        """
        self.sandbox = getattr(settings, "BNB_SANDBOX", True)
        self.account_id = account_id or getattr(settings, "BNB_ACCOUNT_ID", "")
        self.authorization_id = authorization_id or getattr(settings, "BNB_AUTHORIZATION_ID", "")

        if self.sandbox:
            self.auth_url = SANDBOX_AUTH_URL
            self.qr_base_url = SANDBOX_QR_BASE
        else:
            self.auth_url = PROD_AUTH_URL
            self.qr_base_url = PROD_QR_BASE

    # ── Autenticación ─────────────────────────────────────────────────

    def _get_token(self) -> str:
        """
        Obtiene un Bearer token de BNB. Usa cache para evitar
        pedir uno nuevo en cada llamada.
        """
        # Cache key único por credenciales para soportar múltiples edificios
        cache_key = f"{TOKEN_CACHE_KEY}_{hash(self.account_id)}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        if not self.account_id or not self.authorization_id:
            raise BNBPaymentError(
                "Credenciales BNB no configuradas. "
                "Agrega BNB_ACCOUNT_ID y BNB_AUTHORIZATION_ID en .env"
            )

        payload = {
            "accountId": self.account_id,
            "authorizationId": self.authorization_id,
        }

        try:
            resp = requests.post(
                self.auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("BNB auth request failed: %s", e)
            raise BNBPaymentError(f"Error de conexión con BNB: {e}")

        if not data.get("success"):
            msg = data.get("message", "Error desconocido")
            logger.error("BNB auth failed: %s", msg)
            raise BNBPaymentError(f"Autenticación BNB fallida: {msg}")

        token = data["message"]
        cache.set(cache_key, token, TOKEN_CACHE_TTL)
        return token

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_token()}",
        }

    # ── Generar QR ────────────────────────────────────────────────────

    def generar_qr(
        self,
        monto: str,
        glosa: str,
        moneda: str = "BOB",
        uso_unico: bool = True,
        dias_expiracion: int = 3,
    ) -> dict:
        """
        Genera un QR de pago simple.

        Args:
            monto: Monto a cobrar (string, ej: "350.00")
            glosa: Descripción del pago (ej: "Expensa Depto 4A - Marzo 2026")
            moneda: Código de moneda ("BOB" o "USD")
            uso_unico: Si el QR solo puede usarse una vez
            dias_expiracion: Días hasta que expire el QR

        Returns:
            dict con keys: qr_id, qr_image_base64, expiration_date, success
        """
        expiration = (datetime.now() + timedelta(days=dias_expiracion)).strftime("%Y-%m-%d")

        payload = {
            "currency": moneda,
            "gloss": glosa,
            "amount": str(monto),
            "singleUse": str(uso_unico).lower(),
            "expirationDate": expiration,
        }

        url = f"{self.qr_base_url}/getQRWithImageAsync"

        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("BNB generar QR failed: %s", e)
            raise BNBPaymentError(f"Error al generar QR: {e}")

        if not data.get("success"):
            msg = data.get("message", "Error desconocido")
            raise BNBPaymentError(f"BNB rechazó la generación de QR: {msg}")

        # La imagen viene como byte array; convertir a base64 para enviar al frontend
        qr_image_bytes = data.get("qr") or data.get("image") or []
        if isinstance(qr_image_bytes, list):
            qr_image_base64 = base64.b64encode(bytes(qr_image_bytes)).decode("utf-8")
        elif isinstance(qr_image_bytes, str):
            qr_image_base64 = qr_image_bytes
        else:
            qr_image_base64 = ""

        return {
            "qr_id": str(data.get("id", "")),
            "qr_image_base64": qr_image_base64,
            "expiration_date": expiration,
            "success": True,
        }

    # ── Consultar estado del QR ───────────────────────────────────────

    def consultar_estado(self, qr_id: str) -> dict:
        """
        Consulta el estado de un QR generado.

        Returns:
            dict con keys: qr_id, status (int), status_display, expiration_date, success
            Status: 1=No usado, 2=Pagado, 3=Expirado, 4=Error
        """
        url = f"{self.qr_base_url}/getQRStatusAsync"
        payload = {"qrId": str(qr_id)}

        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("BNB consultar estado failed: %s", e)
            raise BNBPaymentError(f"Error al consultar estado QR: {e}")

        if not data.get("success"):
            msg = data.get("message", "Error desconocido")
            raise BNBPaymentError(f"BNB error al consultar QR: {msg}")

        status_code = data.get("qrId", QR_STATUS_ERROR)
        status_map = {
            QR_STATUS_NOT_USED: "No usado",
            QR_STATUS_PAID: "Pagado",
            QR_STATUS_EXPIRED: "Expirado",
            QR_STATUS_ERROR: "Error",
        }

        return {
            "qr_id": str(data.get("id", qr_id)),
            "status": status_code,
            "status_display": status_map.get(status_code, "Desconocido"),
            "expiration_date": data.get("expirationDate", ""),
            "success": True,
        }

    # ── Listar QRs por fecha ─────────────────────────────────────────

    def listar_qrs_por_fecha(self, fecha: str) -> dict:
        """
        Lista los QRs generados en una fecha específica.

        Args:
            fecha: Fecha en formato "YYYY-MM-DD"
        """
        url = f"{self.qr_base_url}/getQRbyGenerationDateAsync"
        payload = {"generationDate": fecha}

        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("BNB listar QRs failed: %s", e)
            raise BNBPaymentError(f"Error al listar QRs: {e}")

        return data
