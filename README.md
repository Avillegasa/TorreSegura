# Torre Segura - Sistema de Administracion de Condominios

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white)

Sistema web Django para la administracion integral de condominios verticales. Incluye gestion de residentes, control de accesos, modulo financiero completo, areas comunes y reportes avanzados.

---

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Django 4.2.10 + Django REST Framework 3.16 |
| Auth web | Django AllAuth (Google OAuth) |
| Auth API movil | SimpleJWT |
| Base de datos | PostgreSQL (produccion) / SQLite (desarrollo) |
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
git clone https://github.com/Avillegasa/pilinmaster.git
cd pilinmaster
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

> Con `USE_LOCAL_DB=True` se usa SQLite local. Sin esa variable se intenta conectar a PostgreSQL via `DATABASE_URL`.

### 5. Aplicar migraciones y cargar datos de prueba

```bash
python manage.py migrate
python scripts/setup.py
```

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

---

## Arquitectura

### Aplicaciones Django (7 apps)

| App | Ruta web | Descripcion |
|---|---|---|
| `usuarios` | `/usuarios/` | Usuarios, roles, autenticacion, OAuth Google |
| `viviendas` | `/viviendas/` | Edificios, departamentos, residentes |
| `accesos` | `/accesos/` | Visitas, movimientos, QR firmados |
| `personal` | `/personal/` | Empleados, puestos, departamentos |
| `financiero` | `/financiero/` | Cuotas, pagos, gastos, estados de cuenta |
| `areas_comunes` | `/areas-comunes/` | Areas comunes, reservas |
| `reportes` | `/reportes/` | Reportes multi-formato con graficos |
| `alertas` | `/alertas/` | Alertas de emergencia |

### API Movil (`/api/v1/`)

Endpoints JWT para la app React Native:

| Ruta | Descripcion |
|---|---|
| `/api/v1/auth/` | Login, token, refresh |
| `/api/v1/alertas/` | CRUD alertas |
| `/api/v1/accesos/` | Control de accesos |
| `/api/v1/visitantes/` | CRUD visitantes (DRF router) |
| `/api/v1/areas-comunes/` | Areas comunes y reservas |
| `/api/v1/financiero/` | Cuotas pendientes/pagadas, registrar pagos |

### Roles y permisos

| Rol | Web | App Movil | Alcance |
|---|---|---|---|
| Administrador | Si | No | Todo el sistema |
| Gerente | Si | No | Su edificio asignado |
| Residente | Limitado | Si | Su vivienda |
| Vigilante | No | Si | Control de accesos |
| Personal | No | No | Gestion interna |

---

## Modulo Financiero (Detalle)

El modulo mas completo del sistema. Ruta base: `/financiero/`

### Submodulos

| Submodulo | URL | Funcionalidad |
|---|---|---|
| Dashboard | `/financiero/` | Resumen con graficos Chart.js, filtros por edificio/vivienda |
| Conceptos de Cuota | `/financiero/conceptos/` | Tipos de cuota (mantenimiento, extraordinaria, etc.) |
| Cuotas | `/financiero/cuotas/` | CRUD + generacion masiva por edificio |
| Pagos | `/financiero/pagos/` | Registro, verificacion, rechazo |
| Categorias de Gasto | `/financiero/categorias-gasto/` | Categorias con presupuesto mensual |
| Gastos | `/financiero/gastos/` | CRUD + marcar pagado / cancelar |
| Estados de Cuenta | `/financiero/estados-cuenta/` | Generacion individual/masiva, PDF, envio por email |

### Flujo principal: Cuota -> Pago -> Verificacion

1. Se genera una **cuota** (individual o masiva por edificio)
2. El residente o admin registra un **pago** (estado PENDIENTE)
3. Se vincula el pago con cuotas via **PagoCuota**
4. Un admin/gerente **verifica** el pago -> las cuotas se marcan como pagadas automaticamente
5. Si se **rechaza**, las cuotas vuelven a estado pendiente

### APIs del dashboard

- `GET /financiero/api/datos-chart/` - Datos para graficos (6 meses, categorias)
- `GET /financiero/api/resumen-financiero/` - Resumen de ingresos/gastos/balance
- `GET /financiero/api/cuotas-por-vivienda/<id>/` - Cuotas filtradas por vivienda

---

## Comandos utiles

```bash
# Tests
python manage.py test                      # Todos
python manage.py test financiero           # Solo financiero
python manage.py test financiero -v2       # Con detalle

# Migraciones
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Datos
python scripts/setup.py                    # Seed inicial
python manage.py createsuperuser           # Superusuario manual

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
| `EMAIL_HOST_USER` | No | - | Email SMTP para notificaciones |
| `EMAIL_HOST_PASSWORD` | No | - | Password SMTP |
| `GOOGLE_CLIENT_ID` | No | - | OAuth Google |
| `GOOGLE_SECRET` | No | - | OAuth Google |

---

## Estructura del proyecto

```
TorreSegura/
├── condominio_app/          # Configuracion Django (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── api_v1_urls.py       # Rutas API movil
├── usuarios/                # Usuarios, roles, auth
├── viviendas/               # Edificios, viviendas, residentes
├── accesos/                 # Visitas, movimientos, QR
├── personal/                # Empleados, puestos
├── financiero/              # Cuotas, pagos, gastos, estados de cuenta
│   ├── models.py            # 7 modelos (ConceptoCuota, Cuota, Pago, etc.)
│   ├── views.py             # ~1900 LOC, dashboard + CRUD + acciones
│   ├── signals.py           # Auto-asignacion de pagos, recargos, etc.
│   ├── api.py               # Endpoints API movil
│   └── forms.py             # Formularios con validacion
├── areas_comunes/           # Areas comunes, reservas
├── reportes/                # Reportes multi-formato
├── alertas/                 # Alertas de emergencia
├── templates/               # Templates Django (por app)
├── static/                  # CSS, JS, imagenes
├── media/                   # Archivos subidos (comprobantes, PDFs)
├── scripts/setup.py         # Seed de datos iniciales
├── requirements.txt         # Dependencias Python
├── .env.example             # Plantilla de variables de entorno
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

---

## Contribucion

1. Crea tu rama desde `main`: `git checkout -b tu-nombre-dev`
2. Todo el codigo (variables, modelos, UI) va en **espanol**
3. Sigue PEP 8 para Python
4. Agrega tests para funcionalidad nueva
5. Haz PR a `main` con descripcion clara
