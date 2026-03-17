from __future__ import annotations

from django.dispatch import receiver
from django.db.models.signals import post_save

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed


def _set_email_confirmado_true(user) -> None:
    """Marca el flag local si existe y aún no está en True."""
    if not user:
        return
    if hasattr(user, "email_confirmado") and not getattr(user, "email_confirmado"):
        user.email_confirmado = True
        user.save(update_fields=["email_confirmado"])


@receiver(email_confirmed)
def sync_email_confirmado_on_allauth_confirm(request, email_address: EmailAddress, **kwargs):
    """Cuando allauth confirma un email, sincroniza usuarios.Usuario.email_confirmado."""
    _set_email_confirmado_true(email_address.user)


@receiver(post_save, sender=EmailAddress)
def sync_email_confirmado_on_emailaddress_save(sender, instance: EmailAddress, **kwargs):
    """Si el EmailAddress queda verified=True por cualquier vía, sincroniza el flag local."""
    if instance.verified:
        _set_email_confirmado_true(instance.user)
