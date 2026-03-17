"""
WSGI config for condominio_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Configurar la variable de entorno para Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condominio_app.settings')

try:
    application = get_wsgi_application()
    print("✅ WSGI application loaded successfully")
except Exception as e:
    print(f"❌ Error loading WSGI application: {e}")
    raise