# Registro de Cambios - Creación de Usuarios por Gerente
**Fecha:** 17 de marzo de 2026

---

## Resumen
Se implementó la funcionalidad para que el **Gerente** pueda crear usuarios con roles restringidos (Residente, Vigilante, Personal). Los usuarios con rol **Personal** reciben credenciales reales para acceso a la **aplicación móvil**.

---

## Archivos Modificados

### 1. `usuarios/forms.py`
- **Filtro de roles:** El Gerente ahora solo puede seleccionar: **Residente**, **Vigilante**, **Personal** (antes se mostraban todos excepto Administrador).
- **Campos de credenciales:** Se removió la lógica que hacía opcionales el username, email y contraseña para Personal. Ahora todos los roles requieren credenciales reales.

### 2. `usuarios/views.py`
- **Creación de Personal:** Al crear un usuario con rol Personal, se:
  - Genera un username automático basado en nombre/apellido si se deja vacío.
  - Guarda la contraseña real (antes se usaba `set_unusable_password()`).
  - Crea un registro `EmailAddress` con `verified=True` vía django-allauth para que pueda iniciar sesión en la app móvil sin verificación de email.
  - Almacena las credenciales en la sesión para mostrarlas una única vez.
  - Redirige a la página de credenciales.
- **Nueva vista `usuario_credenciales`:** Muestra las credenciales generadas y las elimina de la sesión (solo se ven una vez).

### 3. `usuarios/urls.py`
- Se agregó la ruta: `path('credenciales/', views.usuario_credenciales, name='usuario-credenciales')`

### 4. `templates/usuarios/usuario_form.html`
- **JavaScript actualizado:** Se removió la lógica que ocultaba los campos de credenciales y llenaba valores dummy para el rol Personal. Ahora los campos de username, email y contraseña se muestran para **todos los roles**, incluyendo Personal.

### 5. `templates/usuarios/usuario_credenciales.html` *(NUEVO)*
- Nueva plantilla que muestra las credenciales de acceso móvil después de crear un usuario Personal.
- Incluye: nombre completo, rol, puesto, usuario y contraseña.
- Tiene botón de **Imprimir** y estilos de impresión optimizados.
- Advertencia de que las credenciales se muestran **solo una vez**.

---

## Flujo de Uso
1. El Gerente accede a **Crear Usuario**.
2. Selecciona el rol (Residente, Vigilante o Personal).
3. Si elige **Personal**, aparecen los campos adicionales (puesto, contrato, salario, etc.).
4. Completa el formulario con username, email y contraseña (o deja username vacío para auto-generación).
5. Al guardar, se redirige a una página con las credenciales generadas.
6. El Gerente puede imprimir o anotar las credenciales antes de salir.
7. Las credenciales se eliminan de la sesión y no se pueden volver a consultar.
