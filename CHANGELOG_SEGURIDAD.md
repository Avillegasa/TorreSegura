# Registro de Cambios - Correcciones de Seguridad
**Fecha:** 17 de marzo de 2026

---

## Resumen
Se corrigieron **3 problemas de seguridad** relacionados con control de acceso por roles en los módulos: Reportes, Financiero y Alertas.

---

## 1. Módulo REPORTES — Sin autenticación ni autorización

**Archivo:** `reportes/views.py`

**Problema:** Todas las vistas del módulo de reportes no tenían ningún tipo de protección. Cualquier persona (incluso sin cuenta) podía acceder, crear, editar, eliminar y descargar reportes accediendo directamente a las URLs.

**Cambios realizados:**

| Vista | Antes | Después |
|-------|-------|---------|
| `ReporteListView` | Sin protección | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `ReporteCreateView` | Sin protección | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `ReporteUpdateView` | Sin protección | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `ReporteDeleteView` | Sin protección | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `reporte_preview` | Sin protección | `@login_required` |
| `reporte_toggle_favorito` | Sin protección | `@login_required` |
| `reporte_duplicar` | Sin protección | `@login_required` |
| `reporte_pdf` | Sin protección | `@login_required` |
| `reporte_reactivar` | Sin protección | `@login_required` |
| `reporte_descargar` | Sin protección | `@login_required` |

**Imports agregados:**
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from usuarios.views import AccesoWebPermitidoMixin
```

**Acceso resultante:** Solo **Administrador** y **Gerente** pueden acceder a las vistas CRUD. Las funciones auxiliares (preview, PDF, descargar, etc.) requieren usuario autenticado.

---

## 2. Módulo FINANCIERO — Vistas sin verificación de rol

**Archivo:** `financiero/views.py`

**Problema:** 4 vistas solo tenían `LoginRequiredMixin` (cualquier usuario logueado podía acceder), cuando deberían estar restringidas a Administrador y Gerente.

**Cambios realizados:**

| Vista | Antes | Después |
|-------|-------|---------|
| `PagoDetailView` | `LoginRequiredMixin` | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `PagoUpdateView` | `LoginRequiredMixin` | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `EstadoCuentaListView` | `LoginRequiredMixin` | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |
| `EstadoCuentaDetailView` | `LoginRequiredMixin` | `LoginRequiredMixin` + `AccesoWebPermitidoMixin` |

**Acceso resultante:** Solo **Administrador** y **Gerente** pueden ver/editar pagos y estados de cuenta desde la web.

---

## 3. Módulo ALERTAS — Uso de `is_staff` en vez de roles

**Archivos:** `alertas/views.py` y `alertas/views_api.py`

**Problema:** Las vistas de cambio de estado de alertas usaban `request.user.is_staff` (flag interno de Django) en lugar del sistema de roles del proyecto. Esto era inconsistente con el resto del sistema.

**Cambios realizados:**

| Archivo | Función | Antes | Después |
|---------|---------|-------|---------|
| `alertas/views.py` | `actualizar_estado_alerta` | `if not request.user.is_staff` | Verifica `rol.nombre in ['Administrador', 'Gerente']` |
| `alertas/views_api.py` | `cambiar_estado_web` | `if not request.user.is_staff` | Verifica `rol.nombre in ['Administrador', 'Gerente']` |

**Acceso resultante:** Solo **Administrador** y **Gerente** pueden cambiar el estado de las alertas, usando el mismo sistema de roles que el resto del proyecto.

---

## Tabla actualizada: Rol vs Módulo (después de correcciones)

| Módulo / Función | Administrador | Gerente | Residente | Vigilante | Personal | Visitante |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Reportes** (CRUD web) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Reportes** (preview/PDF/descargar) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Financiero** (ver pago detalle) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Financiero** (editar pago) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Financiero** (estados cuenta list) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Financiero** (estado cuenta detalle) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Alertas** (cambiar estado API) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Alertas** (cambiar estado web) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Verificación
```
python manage.py check
System check identified no issues (0 silenced).
```
