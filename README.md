# 🏢 Sistema de Administración de Condominios

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white)

**Torre Segura** - Sistema web desarrollado con Django para la administración integral de condominios verticales (edificios). Solución completa que incluye gestión de residentes, control de accesos, módulo financiero y sistema de reportes avanzado.

---

## 🌟 Características Principales

### 👥 Gestión de Usuarios y Roles
- 🔐 Control de acceso basado en roles (Administrador, Vigilante, Residente, Gerente)
- 👤 Perfiles personalizados por tipo de usuario
- 🔄 Sistema de cambio de roles dinámico
- 🌐 **Autenticación con Google** integrada

### 🏠 Gestión de Viviendas
- 🏢 Administración de edificios y sus características
- 🏠 Gestión completa de departamentos/viviendas
- 👨‍👩‍👧‍👦 Registro detallado de propietarios e inquilinos
- 📊 Estados de vivienda (ocupada, vacía, en mantenimiento)

### 🚪 Control de Accesos
- ⏰ Registro de entradas y salidas en tiempo real
- 👥 Control de visitantes con datos completos
- 🚗 Registro de vehículos residentes y de visita
- 📱 Interface optimizada para vigilantes

### 💰 Módulo Financiero (¡NUEVO!)
- 🧾 Gestión de cuotas de mantenimiento
- 📈 Control de pagos y estados financieros
- 🔔 Sistema de notificaciones de vencimientos
- 📊 Reportes financieros detallados
- 💳 Manejo de múltiples tipos de pago

### 📊 Sistema de Reportes Avanzado
- 📈 Generación de reportes dinámicos con filtros
- 📄 Exportación múltiple: PDF, Excel, CSV, HTML
- 📉 Gráficos interactivos y dashboards
- 🔍 Filtros personalizables por módulo

---

## 💻 Requisitos del Sistema

### Software Requerido
- **Python**: 3.10+ (recomendado: 3.12.x)
- **Django**: 4.2+
- **Node.js**: (opcional, para desarrollo de frontend)
- **Git**: Para control de versiones

### Dependencias Principales
- Django AllAuth (autenticación con Google)
- WeasyPrint (generación de PDFs)
- Pillow (manejo de imágenes)
- django-crispy-forms (formularios estilizados)
- python-decouple (variables de entorno)

---

## 🚀 Instalación Rápida

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Avillegasa/pilinmaster.git
cd pilinmaster/condominio_app
```

### 2. Configurar Entorno Virtual
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (.env)
Este proyecto lee variables desde el archivo `.env` en la raíz del backend.

1. Crea tu archivo `.env` desde el ejemplo:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env
```

2. Edita `.env` y asegúrate de definir al menos:
- `SECRET_KEY`
- `DEBUG=True`

### 5. Configuración de Base de Datos
```bash
# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales
python scripts/setup.py
```

### 6. Crear Superusuario
```bash
python manage.py createsuperuser
```

### 7. Iniciar Servidor de Desarrollo
```bash
python manage.py runserver
```

**🌐 Acceder al sistema**: http://127.0.0.1:8000/

---

## 👤 Usuarios por Defecto

El script de configuración crea los siguientes usuarios de prueba:

| 👤 Usuario    | 🔑 Contraseña     | 🎭 Rol          | 📧 Email                  |
|---------------|------------------|-----------------|---------------------------|
| admin         | admin123         | Administrador   | admin@condominio.com      |
| vigilante     | vigilante123     | Vigilante       | vigilante@condominio.com  |
| carlos        | carlos123        | Residente       | carlos@condominio.com     |
| maria         | maria123         | Residente       | maria@condominio.com      |
| jorge         | jorge123         | Residente       | jorge@condominio.com      |
| ana           | ana123           | Residente       | ana@condominio.com        |
| pedro         | pedro123         | Residente       | pedro@condominio.com      |

> **💡 Importante**: Cambia estas contraseñas antes del despliegue en producción.

---

## 📁 Estructura del Proyecto

```
condominio_app/
│
├── 📁 condominio_app/           # Configuración principal del proyecto
│   ├── settings.py              # Configuraciones del proyecto
│   ├── urls.py                  # URLs principales
│   └── wsgi.py                  # Configuración WSGI
│
├── 📁 usuarios/                 # 👥 Gestión de usuarios y roles
│   ├── models.py                # Modelos de usuario y perfiles
│   ├── views.py                 # Vistas de autenticación
│   └── adapters.py              # Adaptadores para OAuth
│
├── 📁 viviendas/                # 🏠 Gestión de edificios y viviendas
│   ├── models.py                # Modelos de edificios y residentes
│   ├── views.py                 # Vistas de gestión
│   └── admin.py                 # Configuración del admin
│
├── 📁 accesos/                  # 🚪 Control de entradas y salidas
│   ├── models.py                # Modelos de acceso y visitas
│   ├── views.py                 # Vistas de control
│   └── forms.py                 # Formularios de registro
│
├── 📁 financiero/               # 💰 Módulo financiero (NUEVO)
│   ├── models.py                # Modelos de pagos y cuotas
│   ├── views.py                 # Vistas financieras
│   ├── forms.py                 # Formularios de pago
│   └── utils.py                 # Utilidades de cálculo
│
├── 📁 reportes/                 # 📊 Sistema de reportes
│   ├── models.py                # Modelos de reportes
│   ├── views.py                 # Vistas de generación
│   ├── utils.py                 # Utilidades para reportes
│   └── templatetags/            # Filtros personalizados
│
├── 📁 templates/                # 🎨 Plantillas HTML
│   ├── base/                    # Plantillas base
│   ├── usuarios/                # Templates de usuarios
│   ├── viviendas/               # Templates de viviendas
│   ├── accesos/                 # Templates de accesos
│   ├── financiero/              # Templates financieros
│   └── reportes/                # Templates de reportes
│
├── 📁 static/                   # 🎨 Archivos estáticos
│   ├── css/                     # Estilos CSS personalizados
│   ├── js/                      # JavaScript personalizado
│   └── img/                     # Imágenes del sistema
│
├── 📁 media/                    # 📂 Archivos subidos
│   ├── profiles/                # Fotos de perfil
│   └── documents/               # Documentos varios
│
├── 📁 scripts/                  # 🔧 Scripts de utilidad
│   └── setup.py                 # Script de configuración inicial
│
├── manage.py                    # 🚀 Script de gestión de Django
├── requirements.txt             # 📦 Dependencias del proyecto
├── .env.example                 # 🔧 Variables de entorno ejemplo
└── README.md                    # 📚 Documentación (este archivo)
```

---

## 🔧 Configuración Avanzada

### 🔐 Autenticación con Google

Para habilitar el inicio de sesión con Google:

#### 1. Crear Proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Navega a "APIs & Services" > "Credentials"
4. Crea credenciales OAuth 2.0

#### 2. Configurar URLs Autorizadas

En la configuración de OAuth, añade:

**Orígenes autorizados:**
```
http://localhost:8000
https://tu-dominio.com  # Para producción
```

**URIs de redirección:**
```
http://localhost:8000/accounts/google/login/callback/
https://tu-dominio.com/accounts/google/login/callback/  # Para producción
```

#### 3. Configurar Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
# Configuración de Google OAuth
GOOGLE_CLIENT_ID=tu-client-id-aqui
GOOGLE_SECRET=tu-secret-key-aqui

# Configuración de base de datos
DATABASE_URL=sqlite:///db.sqlite3

# Configuración de seguridad
SECRET_KEY=tu-secret-key-django
DEBUG=True
```

#### 4. Configurar en Django Admin

1. Accede al admin: http://localhost:8000/admin/
2. Ve a "Sites" y configura:
   - Domain: `localhost:8000` (desarrollo) o `tu-dominio.com` (producción)
   - Display name: `Torre Segura`
3. Ve a "Social Applications" y crea una nueva aplicación:
   - Provider: Google
   - Name: Google Login
   - Client ID: (del paso 1)
   - Secret key: (del paso 1)
   - Sites: Selecciona el sitio creado

---

### 📊 Configuración de Reportes con WeasyPrint

#### Instalación de GTK (Windows)

1. Descarga el instalador GTK desde:
   [GTK for Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)

2. Instala en: `C:\Program Files\GTK3-Runtime Win64`

3. Añade al PATH del sistema:
   ```
   C:\Program Files\GTK3-Runtime Win64\bin
   ```

4. Reinicia tu terminal/IDE

5. Verifica la instalación:
   ```bash
   where gobject-2.0-0.dll
   ```

#### Configuración Alternativa para Linux

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# CentOS/RHEL
sudo yum install python3-devel python3-pip python3-cffi cairo pango gdk-pixbuf2
```

---

## 🎯 Funcionalidades por Módulo

### 👥 Módulo de Usuarios
- ✅ Registro y autenticación local
- ✅ Integración con Google OAuth
- ✅ Gestión de perfiles por rol
- ✅ Sistema de permisos granular
- ✅ Cambio de contraseñas
- ✅ Recuperación de cuentas

### 🏠 Módulo de Viviendas
- ✅ CRUD completo de edificios
- ✅ Gestión de viviendas/departamentos
- ✅ Registro de propietarios/inquilinos
- ✅ Historial de cambios
- ✅ Estados de ocupación
- ✅ Búsqueda y filtros avanzados

### 🚪 Módulo de Accesos
- ✅ Registro de entradas/salidas
- ✅ Control de visitantes
- ✅ Gestión de vehículos
- ✅ Notificaciones automáticas
- ✅ Reportes de acceso
- ✅ Interface móvil-friendly

### 💰 Módulo Financiero
- ✅ Gestión de cuotas mensuales
- ✅ Control de pagos
- ✅ Estados de cuenta
- ✅ Generación de recibos
- ✅ Notificaciones de vencimiento
- ✅ Reportes financieros
- ✅ Dashboard de ingresos

### 📊 Módulo de Reportes
- ✅ Reportes dinámicos con filtros
- ✅ Exportación múltiple (PDF/Excel/CSV/HTML)
- ✅ Gráficos interactivos
- ✅ Dashboards por módulo
- ✅ Programación de reportes
- ✅ Plantillas personalizables

---

## 🔒 Configuración de Seguridad

### Variables de Entorno Importantes

```bash
# Seguridad
SECRET_KEY=tu-clave-secreta-muy-larga-y-compleja
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com

# Base de Datos
DATABASE_URL=postgresql://usuario:password@host:puerto/basededatos

# Email (para notificaciones)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password

# Almacenamiento en la nube (opcional)
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_STORAGE_BUCKET_NAME=tu-bucket
```

### Configuraciones Recomendadas para Producción

```python
# settings.py para producción
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🚀 Despliegue

### Opción 1: Heroku

```bash
# Instalar Heroku CLI
# Crear archivo Procfile
echo "web: gunicorn condominio_app.wsgi" > Procfile

# Configurar Heroku
heroku create tu-app-name
heroku config:set SECRET_KEY=tu-secret-key
heroku config:set DEBUG=False
heroku addons:create heroku-postgresql:hobby-dev

# Desplegar
git push heroku main
heroku run python manage.py migrate
heroku run python scripts/setup.py
```

### Opción 2: VPS con Docker

```dockerfile
# Dockerfile
FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "condominio_app.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=tu-secret-key
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: condominio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 🧪 Testing

### Ejecutar Tests
```bash
# Todos los tests
python manage.py test

# Tests específicos por app
python manage.py test usuarios
python manage.py test viviendas
python manage.py test accesos
python manage.py test financiero
python manage.py test reportes

# Tests con coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Tests Incluidos
- ✅ Tests unitarios para modelos
- ✅ Tests de vistas y formularios
- ✅ Tests de autenticación
- ✅ Tests de permisos
- ✅ Tests de integración

---

## 🤝 Contribución

### Flujo de Contribución

1. **Fork** el repositorio
2. **Crea** una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. **Abre** un Pull Request

### Estándares de Código

- **PEP 8** para Python
- **Documentación** en español
- **Tests** para nuevas funcionalidades
- **Variables** en español
- **Commits** descriptivos

### Reportar Bugs

1. Verifica que el bug no esté ya reportado
2. Crea un issue con:
   - Descripción clara del problema
   - Pasos para reproducir
   - Comportamiento esperado vs actual
   - Screenshots si es necesario
   - Información del entorno

---

## 📚 Documentación Adicional

### APIs Disponibles
- **REST API** para integración móvil (en desarrollo)
- **Webhooks** para notificaciones externas
- **GraphQL** endpoint (plannificado)

### Integraciones
- 📱 **Aplicación móvil** (en desarrollo)
- 🔔 **Notificaciones push**
- 📧 **Sistema de emails automáticos**
- 📊 **Integración con Google Analytics**

### Roadmap
- [ ] Módulo de reservas de áreas comunes
- [ ] Sistema de tickets/soporte
- [ ] Chat interno entre residentes
- [ ] Integración con sistemas de domótica
- [ ] App móvil nativa
- [ ] Dashboard ejecutivo avanzado

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 👨‍💻 Desarrollado por

**Avillegasa** - [GitHub](https://github.com/Avillegasa)

---

## 🆘 Soporte

¿Necesitas ayuda? 

- 📧 **Email**: soporte@torresegura.com
- 🐛 **Reportar bug**: [Issues](https://github.com/Avillegasa/pilinmaster/issues)
- 💬 **Discusiones**: [Discussions](https://github.com/Avillegasa/pilinmaster/discussions)
- 📖 **Wiki**: [Documentación completa](https://github.com/Avillegasa/pilinmaster/wiki)

---

<div align="center">

### ⭐ Si te gusta este proyecto, ¡dale una estrella! ⭐

**Torre Segura - Sistema Integral de Gestión de Condominios**

*Desarrollado con ❤️ por la comunidad*

![GitHub stars](https://img.shields.io/github/stars/Avillegasa/pilinmaster?style=social)
![GitHub forks](https://img.shields.io/github/forks/Avillegasa/pilinmaster?style=social)

</div>