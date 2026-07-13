# Torre Segura - Sistema de Administracion de Condominios

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white)

Sistema web Django para la administracion integral de condominios verticales. Incluye gestion de residentes, control de accesos, modulo financiero completo (con pagos QR vía BNB), areas comunes y reportes avanzados.

Este repositorio es la API + aplicacion web Django. La app movil (React Native/Expo) que consume `/api/v1/` vive en un repositorio separado — ver su `README.md`/`CLAUDE.md` para esa parte.

---

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Django 4.2.10 + Django REST Framework 3.16 |
| Auth web | Django AllAuth (Google OAuth) |
| Auth API movil | SimpleJWT |
| Base de datos | PostgreSQL (produccion) / SQLite (desarrollo) |
| Pagos QR | Integracion con API QR Simple de BNB (Banco Nacional de Bolivia) |
| PDF | WeasyPrint + ReportLab |
| Excel | Pandas + openpyxl |
| Graficos | Matplotlib (backend) + Chart.js (frontend) |
| Servidor prod | Gunicorn + WhiteNoise |
| Hosting prod | Railway |

---

## Inicio Rapido para Desarrollo

### Requisitos previos

- Python 3.10+ (recomendado 3.12)
- Git

### 1. Clonar y entrar al proyecto

```bash
git clone https://github.com/Avillegasa/TorreSegura.git
cd TorreSegura
```

### 2. Crear y activar entorno virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y define al menos:

```env
SECRET_KEY=una-clave-secreta-larga-y-aleatoria
DEBUG=True
USE_LOCAL_DB=True
```

> Con `USE_LOCAL_DB=True` se usa SQLite local. Sin esa variable (o en `False`) se intenta conectar a PostgreSQL via `DATABASE_URL`, y Django falla al arrancar si esta no esta configurada.

### 5. Aplicar migraciones y cargar datos de prueba

```bash
python manage.py migrate
python scripts/setup.py
```

`scripts/setup.py` crea roles base, un edificio de ejemplo con viviendas, el superusuario `admin`, un usuario `vigilante` y 5 residentes de prueba (ver tabla abajo). Es idempotente: se puede volver a correr sin duplicar datos.

Alternativa: `python manage.py setup_local_dev [--create-superuser]` configura el `Site` de Django (necesario para AllAuth) apuntando a `127.0.0.1:8000` y opcionalmente crea un superusuario.

### 6. Levantar el servidor

```bash
# Solo localhost
python manage.py runserver

# Accesible por LAN (necesario para la app movil)
python manage.py runserver 0.0.0.0:8000
```

Acceder en: http://localhost:8000

---

## Usuarios de prueba

El script `setup.py` crea estos usuarios (patron de contrasena: `{username}123`):

| Usuario | Contrasena | Rol | Descripcion |
|---|---|---|---|
| `admin` | `admin123` | Administrador | Acceso total, panel admin Django |
| `vigilante` | `vigilante123` | Vigilante | Control de accesos |
| `carlos` | `carlos123` | Residente | Propietario vivienda 101 |
| `maria` | `maria123` | Residente | Propietaria vivienda 102 |
| `jorge` | `jorge123` | Residente | Propietario vivienda 201 |
| `ana` | `ana123` | Residente | Propietaria vivienda 301 |
| `pedro` | `pedro123` | Residente | Inquilino vivienda 102 |

Panel admin Django: http://localhost:8000/admin/ (usuario `admin`)

Los roles **Vigilante**, **Residente** y **Personal** solo tienen acceso a la app movil, no a la web (ver tabla de Roles y permisos).

---

## Arquitectura

### Aplicaciones Django (8 apps)

| App | Ruta web | Descripcion |
|---|---|---|
| `usuarios` | `/usuarios/` | Usuarios, roles, autenticacion, OAuth Google, credenciales temporales |
| `viviendas` | `/viviendas/` | Edificios, departamentos, residentes |
| `accesos` | `/accesos/` | Visitas, movimientos, QR firmados |
| `personal` | `/personal/` | Empleados, puestos, departamentos |
| `financiero` | `/financiero/` | Cuentas bancarias BNB, cuotas, pagos (incl. QR), gastos, estados de cuenta |
| `areas_comunes` | `/areas-comunes/` | Areas comunes, reservas |
| `reportes` | `/reportes/` | Reportes multi-formato con graficos |
| `alertas` | `/alertas/` | Alertas de emergencia |

La mayoria de estas apps tienen **dos capas de vistas** que hay que mantener sincronizadas al cambiar reglas de negocio: vistas web con templates Django (`views.py`, `forms.py`) para Administrador/Gerente, y endpoints DRF para la app movil (`api.py` y/o `api_v1_urls.py` + `serializers.py`). En `accesos`, el CRUD de visitantes vive aparte en `api_v1_visitantes.py` (router DRF).

### API Movil (`/api/v1/`)

Endpoints JWT para la app React Native, enrutados desde `condominio_app/api_v1_urls.py`:

| Ruta | Descripcion |
|---|---|
| `/api/v1/auth/` | Login, token, refresh |
| `/api/v1/alertas/` | CRUD alertas |
| `/api/v1/accesos/` | Control de accesos |
| `/api/v1/visitantes/` | CRUD visitantes (DRF router) |
| `/api/v1/areas-comunes/` | Areas comunes y reservas |
| `/api/v1/financiero/` | Cuotas pendientes/pagadas, registrar pagos, generar/consultar QR BNB |

QR de acceso de visitantes: firmados con `QR_SECRET_KEY` (fallback a `SECRET_KEY`), logica en `accesos/qr_firma_utils.py`. QR de pago financiero: generado vía la API BNB (ver seccion Modulo Financiero).

### Roles y permisos

| Rol | Web | App Movil | Alcance |
|---|---|---|---|
| Administrador | Si | No | Todo el sistema |
| Gerente | Si | No | Su edificio asignado |
| Residente | Limitado | Si | Su vivienda |
| Vigilante | No | Si | Control de accesos |
| Personal | No | No | Gestion interna |

Las vistas web de Reportes, Financiero (pagos/estados de cuenta) y el cambio de estado de Alertas estan restringidas a **Administrador** y **Gerente** unicamente (ver `CHANGELOG_SEGURIDAD.md` para el detalle de esta correccion).

### Alta de usuarios y credenciales temporales

El Gerente puede crear usuarios con rol Residente, Vigilante o Personal desde la web (`usuarios/views.py`). Al crear un usuario **Personal**, el sistema genera credenciales reales de acceso movil (username auto-generado si se deja vacio, password real, `EmailAddress` verificado via AllAuth) y las muestra **una sola vez** en `usuario_credenciales.html` para que el Gerente las imprima o anote. `Usuario.debe_cambiar_password` y `Usuario.credenciales_expiran` controlan si esas credenciales son temporales; `ForcePasswordChangeMiddleware` (`condominio_app/middleware/force_password_change.py`) fuerza el cambio de contrasena o desactiva la cuenta si expiraron, redirigiendo a `forzar_cambio_password` en cualquier vista salvo esa y logout. Ver `CHANGELOG_USUARIOS.md` para el detalle completo del flujo.

---

## Modulo Financiero (Detalle)

El modulo mas completo del sistema. Ruta base: `/financiero/`

### Submodulos

| Submodulo | URL | Funcionalidad |
|---|---|---|
| Dashboard | `/financiero/` | Resumen con graficos Chart.js, filtros por edificio/vivienda |
| Cuentas Bancarias | `/financiero/cuentas-bancarias/` | Cuenta BNB por edificio, credenciales API QR Simple (solo Admin) |
| Conceptos de Cuota | `/financiero/conceptos/` | Tipos de cuota (mantenimiento, extraordinaria, etc.) |
| Cuotas | `/financiero/cuotas/` | CRUD + generacion masiva por edificio |
| Pagos | `/financiero/pagos/` | Registro, verificacion, rechazo (efectivo, transferencia o QR BNB) |
| Categorias de Gasto | `/financiero/categorias-gasto/` | Categorias con presupuesto mensual |
| Gastos | `/financiero/gastos/` | CRUD + marcar pagado / cancelar |
| Estados de Cuenta | `/financiero/estados-cuenta/` | Generacion individual/masiva, PDF, envio por email |

### Flujo principal: Cuota -> Pago -> Verificacion

1. Se genera una **cuota** (individual o masiva por edificio)
2. El residente o admin registra un **pago** (estado PENDIENTE) — a mano o pagando el QR BNB generado para la cuota
3. Se vincula el pago con cuotas via **PagoCuota**
4. Un admin/gerente **verifica** el pago -> las cuotas se marcan como pagadas automaticamente (o el pago QR se concilia automaticamente al confirmar BNB el cobro)
5. Si se **rechaza**, las cuotas vuelven a estado pendiente

La logica de recargos por mora, auto-asignacion de pagos a cuotas y actualizacion de fechas vive en signals (`financiero/signals.py`), no en las vistas — es el punto correcto para modificar estas reglas.

### Pagos QR (BNB)

`financiero/services/bnb_payment.py` integra la **API QR Simple de BNB**: autentica con `BNB_ACCOUNT_ID`/`BNB_AUTHORIZATION_ID` (por edificio, guardados en el modelo de Cuenta Bancaria), genera un QR de cobro para una cuota y consulta su estado (no usado / pagado / expirado / error). Usa `BNB_SANDBOX=True` por defecto para el entorno sandbox de BNB. Endpoints relevantes: `financiero/api.py::generar_qr_pago` y `financiero/api_v1_urls.py` (`/api/v1/financiero/pagos/qr/generar/`).

### APIs del dashboard

- `GET /financiero/api/datos-chart/` - Datos para graficos (6 meses, categorias)
- `GET /financiero/api/resumen-financiero/` - Resumen de ingresos/gastos/balance
- `GET /financiero/api/cuotas-por-vivienda/<id>/` - Cuotas filtradas por vivienda

---

## Comandos utiles

```bash
# Tests
python manage.py test                                  # Todos
python manage.py test financiero                       # Solo financiero
python manage.py test financiero.tests.ClaseTest.test_metodo  # Un test puntual
python manage.py test financiero -v2                    # Con detalle

# Migraciones
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Datos
python scripts/setup.py                    # Seed inicial (roles, edificio, usuarios de prueba)
python manage.py setup_local_dev            # Configura el Site de AllAuth para desarrollo local
python manage.py seed_cuotas                # Genera cuotas de prueba (financiero)
python manage.py createsuperuser            # Superusuario manual

# Produccion
python manage.py collectstatic --noinput
gunicorn condominio_app.wsgi:application --bind 0.0.0.0:8000
```

---

## Variables de entorno

| Variable | Requerida | Default | Descripcion |
|---|---|---|---|
| `SECRET_KEY` | Si | - | Clave secreta Django |
| `DEBUG` | No | `False` | Modo debug |
| `USE_LOCAL_DB` | No | `False` | `True` = SQLite, `False` = PostgreSQL |
| `DATABASE_URL` | Prod | - | URL de PostgreSQL |
| `QR_SECRET_KEY` | No | `SECRET_KEY` | Clave para firmar QR de visitantes |
| `EMAIL_BACKEND` | No | consola en `DEBUG` | Backend de email; en dev se recomienda dejarlo sin definir (consola) |
| `EMAIL_HOST` | No | - | Host SMTP (ej. `smtp.gmail.com`) |
| `EMAIL_PORT` | No | - | Puerto SMTP (ej. `587`) |
| `EMAIL_USE_TLS` | No | - | `True` para TLS |
| `EMAIL_HOST_USER` | No | - | Email SMTP para notificaciones |
| `EMAIL_HOST_PASSWORD` | No | - | Password SMTP |
| `DEFAULT_FROM_EMAIL` | No | - | Remitente por defecto de los correos del sistema |
| `GOOGLE_CLIENT_ID` | No | - | OAuth Google |
| `GOOGLE_SECRET` | No | - | OAuth Google |
| `BNB_SANDBOX` | No | `True` | `False` para usar la API BNB de produccion |
| `BNB_ACCOUNT_ID` | No | - | accountId de la API QR Simple de BNB (fallback global; normalmente se guarda por edificio) |
| `BNB_AUTHORIZATION_ID` | No | - | authorizationId de la API QR Simple de BNB |

`ALLOWED_HOSTS` no se define por `.env` directamente: en `DEBUG=True` incluye automaticamente `*` (para pruebas por LAN con la app movil), y en Railway agrega `RAILWAY_PUBLIC_DOMAIN`.

---

## Estructura del proyecto

```
TorreSegura/
├── condominio_app/          # Configuracion Django (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   ├── api_v1_urls.py       # Rutas API movil
│   └── middleware/
│       └── force_password_change.py
├── usuarios/                 # Usuarios, roles, auth, credenciales temporales
├── viviendas/                 # Edificios, viviendas, residentes
├── accesos/                   # Visitas, movimientos, QR de acceso
├── personal/                  # Empleados, puestos
├── financiero/                 # Cuentas BNB, cuotas, pagos (QR), gastos, estados de cuenta
│   ├── models.py             # ConceptoCuota, Cuota, Pago, PagoCuota, Gasto, CuentaBancaria, PagoQRBNB, etc.
│   ├── views.py               # Dashboard + CRUD + acciones (vistas web)
│   ├── api.py / api_v1_urls.py # Endpoints API movil, incl. generacion/consulta de QR BNB
│   ├── services/bnb_payment.py # Cliente de la API QR Simple de BNB
│   ├── signals.py             # Auto-asignacion de pagos, recargos por mora, etc.
│   └── management/commands/seed_cuotas.py
├── areas_comunes/              # Areas comunes, reservas
├── reportes/                    # Reportes multi-formato
├── alertas/                     # Alertas de emergencia
├── templates/                   # Templates Django (por app)
├── static/                      # CSS, JS, imagenes
├── media/                       # Archivos subidos (comprobantes, PDFs)
├── scripts/setup.py             # Seed de datos iniciales
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de variables de entorno
├── CLAUDE.md                    # Guia para Claude Code sobre este backend
└── manage.py
```

---

## Despliegue en Railway (produccion actual)

El proyecto esta desplegado en Railway con PostgreSQL. Las variables de entorno de produccion se configuran en el dashboard de Railway. Settings de produccion incluyen:

- `DEBUG=False`
- HTTPS forzado (`SECURE_SSL_REDIRECT=True`)
- HSTS habilitado (1 ano)
- Cookies seguras
- CORS restringido a dominios especificos
Sobre este punto de desplieque ya paso mucho tiempo y posiblemente no este funcionando. pero esta documentado por si se requeire mas adelante

---

## Contribucion

1. Crea tu rama desde `main`: `git checkout -b tu-nombre-dev`
2. Todo el codigo (variables, modelos, UI) va en **espanol**
3. Sigue PEP 8 para Python
4. Agrega tests para funcionalidad nueva
5. Haz PR a `main` con descripcion clara
