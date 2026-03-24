# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Django backend.

See also: `../CLAUDE.md` for the monorepo overview and mobile app details.

## Key Models by App

- **usuarios**: `Usuario` (extends AbstractUser), `Rol`, `ClientePotencial` (lead tracking)
- **viviendas**: `Edificio`, `Vivienda`, `Residente` — soft-delete via inactive status + date
- **accesos**: `Visita`, `MovimientoResidente` — has both template views (`views.py`) and API views (`api_views.py`, `api_v1_visitantes.py`)
- **personal**: `Empleado`, `Puesto`, `Departamento`
- **financiero**: `ConceptoCuota`, `Cuota`, `Pago`, `PagoCuota`, `Gasto`, `CategoriaGasto`, `EstadoCuenta` — late penalty logic (recargo) in signals
- **reportes**: Multi-format export (PDF/Excel/CSV/HTML) with Matplotlib graphs. Custom template tags in `templatetags/`
- **alertas**: Alert types (fire, earthquake, security, health, etc.) via DRF ModelViewSets

## Mobile API (`/api/v1/`)

The v1 API is the clean, JWT-authenticated layer consumed by the mobile app. Defined in `condominio_app/api_v1_urls.py`:
- Auth endpoints: `usuarios/api_v1_urls.py`
- Alert endpoints: `alertas/api_v1_urls.py`
- Access endpoints: `accesos/api_v1_urls.py`
- Visitor CRUD: DRF router in `accesos/api_v1_visitantes.py`

QR code signing uses `QR_SECRET_KEY` env var (falls back to `SECRET_KEY`). Logic in `accesos/qr_firma_utils.py`.

## Configuration

Settings in `condominio_app/settings.py` using `django-environ`. Key env vars: `DEBUG`, `SECRET_KEY`, `USE_LOCAL_DB`, `DATABASE_URL`, `QR_SECRET_KEY`, `EMAIL_*`, `ALLOWED_HOSTS`.

When `DEBUG=True`, `ALLOWED_HOSTS` automatically includes `*` for LAN testing with mobile devices.

## Patterns

- Generic class-based views with role-based mixins
- Model-level validation via `full_clean()`
- Django signals for automatic date/status updates (`financiero/signals.py`, `usuarios/signals.py`)
- Custom context processors for user-specific data (`usuarios/context_processors.py`)
