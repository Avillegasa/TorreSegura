import os
import sys
import random
import datetime
import decimal
from datetime import timedelta, date

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condominio_app.settings')
import django
django.setup()

# Importar modelos
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

from usuarios.models import Rol, Usuario
from viviendas.models import Edificio, Vivienda, Residente
from accesos.models import Visita, MovimientoResidente
from personal.models import Puesto, Empleado, Asignacion, ComentarioAsignacion
from financiero.models import (
    ConceptoCuota, Cuota, Pago, PagoCuota, 
    CategoriaGasto, Gasto, EstadoCuenta
)

# Configuración de números de datos a generar
NUM_ROLES = 6  # Aumentado para incluir Personal
NUM_USUARIOS = 50
NUM_EDIFICIOS = 3
NUM_VIVIENDAS = 60
NUM_RESIDENTES = 40
NUM_PUESTOS = 7
NUM_EMPLEADOS = 10
NUM_ASIGNACIONES = 30
NUM_VISITAS = 50
NUM_MOVIMIENTOS = 60
NUM_CONCEPTOS_CUOTA = 4
NUM_CUOTAS = 100
NUM_PAGOS = 60
NUM_CATEGORIAS_GASTO = 6
NUM_GASTOS = 50
NUM_ESTADOS_CUENTA = 30

print("Iniciando llenado de la base de datos...")


def crear_datos_base():
    """Crear datos base necesarios para el sistema"""
    print("\nCreando datos base...")
    
    # Crear rol de administrador si no existe
    admin_rol, created = Rol.objects.get_or_create(
        nombre='Administrador',
        defaults={'descripcion': 'Administrador del sistema con todos los permisos'}
    )
    print(f"Rol de Administrador {'creado' if created else 'ya existe'}")
    
    # Crear usuario administrador por defecto si no existe
    User = get_user_model()
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@torresegura.com',
            'first_name': 'Administrador',
            'last_name': 'Sistema',
            'rol': admin_rol,
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Usuario administrador creado")
    else:
        print("Usuario administrador ya existe")
    
    return admin_rol, admin_user


def generar_roles():
    """Generar roles para el sistema"""
    print("\nGenerando roles...")
    
    # Lista de posibles roles - ORDEN IMPORTANTE
    roles_data = [
        {'nombre': 'Administrador', 'descripcion': 'Control total del sistema'},
        {'nombre': 'Gerente', 'descripcion': 'Acceso a funciones administrativas y financieras'},
        {'nombre': 'Residente', 'descripcion': 'Acceso a información de su vivienda y áreas comunes'},
        {'nombre': 'Personal', 'descripcion': 'Acceso al módulo de mantenimiento'},  # CRUCIAL
        {'nombre': 'Vigilante', 'descripcion': 'Control de accesos y seguridad'},
        {'nombre': 'Visitante', 'descripcion': 'Acceso limitado temporal'},
    ]
    
    roles_creados = []
    for data in roles_data:
        rol, created = Rol.objects.get_or_create(
            nombre=data['nombre'],
            defaults={'descripcion': data['descripcion']}
        )
        roles_creados.append(rol)
        print(f"Rol {rol.nombre} {'creado' if created else 'ya existe'}")
    
    return roles_creados


def generar_usuarios(roles, num_usuarios=NUM_USUARIOS):
    """Generar usuarios ficticios para el sistema"""
    print(f"\nGenerando {num_usuarios} usuarios...")
    
    User = get_user_model()
    nombres = ['Juan', 'Pedro', 'María', 'Ana', 'Luis', 'Carlos', 'Sofía', 'Laura', 'Roberto', 'Miguel', 
              'Lucía', 'Fernanda', 'Gabriel', 'Jorge', 'Diana', 'Patricia', 'Andrés', 'Eduardo']
    
    apellidos = ['García', 'Pérez', 'Rodríguez', 'López', 'Martínez', 'González', 'Hernández', 'Sánchez', 
                'Ramírez', 'Torres', 'Flores', 'Rivera', 'Cruz', 'Morales', 'Reyes', 'Díaz', 'Mendoza']
    
    tipo_docs = ['DNI', 'PASAPORTE', 'CEDULA']
    
    # Filtrar roles excluyendo Personal (se creará específicamente para empleados)
    roles_usuarios = [r for r in roles if r.nombre != 'Personal']
    
    # CORRECCIÓN: Aumentar probabilidad de rol Residente
    def seleccionar_rol_ponderado():
        """Selecciona rol con ponderación: más residentes"""
        if random.random() < 0.6:  # 60% probabilidad de Residente
            return next((r for r in roles_usuarios if r.nombre == 'Residente'), random.choice(roles_usuarios))
        else:
            return random.choice(roles_usuarios)
    
    usuarios = []
    for i in range(num_usuarios):
        nombre = random.choice(nombres)
        apellido = random.choice(apellidos)
        username = f"{nombre.lower()}.{apellido.lower()}{random.randint(1, 99)}"
        email = f"{username}@example.com"
        
        # Evitar duplicados en username y email
        while User.objects.filter(username=username).exists():
            username = f"{nombre.lower()}.{apellido.lower()}{random.randint(1, 999)}"
        
        while User.objects.filter(email=email).exists():
            email = f"{username}{random.randint(1, 99)}@example.com"
        
        rol = seleccionar_rol_ponderado()  # Usar selección ponderada
        tipo_documento = random.choice(tipo_docs)
        numero_documento = f"{random.randint(10000000, 99999999)}"
        telefono = f"{random.randint(1000000000, 9999999999)}"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password='password123',
            first_name=nombre,
            last_name=apellido,
            rol=rol,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            telefono=telefono,
            is_active=random.random() > 0.1  # 10% de usuarios inactivos
        )
        
        usuarios.append(user)
        
        if i % 10 == 0:
            print(f"Creados {i} usuarios...")
    
    print(f"Total: {len(usuarios)} usuarios creados")
    return usuarios


def generar_edificios(num_edificios=NUM_EDIFICIOS):
    """Generar edificios para el condominio"""
    print(f"\nGenerando {num_edificios} edificios...")
    
    nombres_edificios = ['Torre A', 'Torre B', 'Torre C', 'Residencial Norte', 'Residencial Sur', 
                       'Edificio Central', 'Torre Principal', 'Condominio Las Palmas', 'Edificio El Mirador']
    
    direcciones = [
        'Av. Principal 123, Col. Centro',
        'Calle Robles 456, Fracc. Los Pinos',
        'Blvd. Las Palmas 789, Zona Dorada',
        'Calle 5 de Mayo 234, Col. Reforma',
        'Av. Revolución 567, Fracc. Santa Fe',
        'Calle Cedros 890, Col. Bosques',
        'Blvd. Las Américas 345, Zona Diamante',
        'Av. Insurgentes 678, Col. Del Valle',
        'Calle Girasoles 901, Fracc. Jardines'
    ]
    
    edificios = []
    for i in range(num_edificios):
        nombre = nombres_edificios[i] if i < len(nombres_edificios) else f"Edificio {i+1}"
        direccion = direcciones[i] if i < len(direcciones) else f"Calle {i+1} #{random.randint(100, 999)}"
        pisos = random.randint(5, 20)
        
        # Fecha de construcción entre 1990 y 2020
        year = random.randint(1990, 2020)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        fecha_construccion = date(year, month, day)
        
        edificio = Edificio.objects.create(
            nombre=nombre,
            direccion=direccion,
            pisos=pisos,
            fecha_construccion=fecha_construccion
        )
        
        edificios.append(edificio)
        print(f"Edificio '{nombre}' creado")
    
    return edificios


def generar_viviendas(edificios, num_viviendas=NUM_VIVIENDAS):
    """Generar viviendas para los edificios"""
    print(f"\nGenerando {num_viviendas} viviendas...")
    
    estados = ['OCUPADO', 'DESOCUPADO', 'MANTENIMIENTO']
    viviendas = []
    
    # Distribuir viviendas entre los edificios
    for edificio in edificios:
        # Calcular viviendas por edificio
        num_por_edificio = num_viviendas // len(edificios)
        if edificio == edificios[-1]:  # al último edificio asignarle las restantes
            num_por_edificio += num_viviendas % len(edificios)
        
        # Crear viviendas para este edificio
        for i in range(num_por_edificio):
            piso = random.randint(1, edificio.pisos)
            
            # Generar número de vivienda único
            intentos = 0
            max_intentos = 100
            while intentos < max_intentos:
                numero = f"{piso}{random.randint(1, 20):02d}"
                if not Vivienda.objects.filter(edificio=edificio, numero=numero).exists():
                    break
                intentos += 1
            
            # Si no se pudo generar un número único, usar uno secuencial
            if intentos >= max_intentos:
                numero = f"{piso}{(i+1):02d}"
            
            metros_cuadrados = random.randint(60, 200)
            habitaciones = random.randint(1, 4)
            baños = random.randint(1, 3)
            estado = random.choice(estados)
            
            # 5% de viviendas inactivas (dadas de baja)
            activo = random.random() > 0.05
            
            vivienda = Vivienda.objects.create(
                edificio=edificio,
                numero=numero,
                piso=piso,
                metros_cuadrados=metros_cuadrados,
                habitaciones=habitaciones,
                baños=baños,
                estado='BAJA' if not activo else estado,
                activo=activo
            )
            
            # Si está inactiva, añadir fecha y motivo de baja
            if not activo:
                vivienda.fecha_baja = timezone.now().date() - timedelta(days=random.randint(1, 365))
                vivienda.motivo_baja = random.choice([
                    "Remodelación completa",
                    "Problemas estructurales",
                    "Cambio de uso",
                    "Unificación con otra vivienda",
                    "Daños por filtración"
                ])
                vivienda.save()
            
            viviendas.append(vivienda)
        
        print(f"Creadas {num_por_edificio} viviendas para {edificio.nombre}")
    
    print(f"Total: {len(viviendas)} viviendas creadas")
    return viviendas


def generar_residentes(usuarios, viviendas, num_residentes=NUM_RESIDENTES):
    """Generar residentes para las viviendas"""
    print(f"\nGenerando {num_residentes} residentes...")
    
    # Filtrar viviendas activas y desocupadas para mejor distribución
    viviendas_disponibles = [v for v in viviendas if v.activo and v.estado in ['DESOCUPADO', 'OCUPADO']]
    
    if not viviendas_disponibles:
        print("No hay viviendas disponibles para asignar residentes")
        return []
    
    # Filtrar usuarios con rol Residente y sin residente asignado
    usuarios_residentes = [u for u in usuarios if u.rol and u.rol.nombre == 'Residente']
    usuarios_con_residente = set(Residente.objects.values_list('usuario_id', flat=True))
    usuarios_disponibles = [u for u in usuarios_residentes if u.id not in usuarios_con_residente]
    
    if not usuarios_disponibles:
        print("No hay usuarios con rol Residente disponibles para crear residentes")
        return []
    
    # Limitar según lo disponible
    num_residentes = min(num_residentes, len(usuarios_disponibles))
    
    residentes = []
    viviendas_usadas = set()
    
    for i in range(num_residentes):
        usuario = usuarios_disponibles[i]
        
        # Seleccionar vivienda disponible (evitar duplicados si es posible)
        viviendas_candidatas = [v for v in viviendas_disponibles if v.id not in viviendas_usadas]
        if not viviendas_candidatas:
            # Si todas están usadas, permitir compartir vivienda
            viviendas_candidatas = viviendas_disponibles
        
        vivienda = random.choice(viviendas_candidatas)
        viviendas_usadas.add(vivienda.id)
        
        # Propietarios vs inquilinos: 40% propietarios
        es_propietario = random.random() < 0.4
        vehiculos = random.randint(0, 3)
        
        # Fecha de ingreso entre 1 y 5 años atrás
        fecha_ingreso = timezone.now().date() - timedelta(days=random.randint(30, 1825))
        
        residente = Residente.objects.create(
            usuario=usuario,
            vivienda=vivienda,
            fecha_ingreso=fecha_ingreso,
            vehiculos=vehiculos,
            activo=usuario.is_active,
            es_propietario=es_propietario
        )
        
        residentes.append(residente)
        
        # Actualizar estado de la vivienda a OCUPADO
        if vivienda.estado == 'DESOCUPADO' and residente.activo:
            vivienda.estado = 'OCUPADO'
            vivienda.save()
    
    print(f"Total: {len(residentes)} residentes creados")
    return residentes


def generar_puestos(num_puestos=NUM_PUESTOS):
    """Generar puestos de trabajo para el personal"""
    print(f"\nGenerando {num_puestos} puestos de trabajo...")
    
    puestos_data = [
        {'nombre': 'Jardinero', 'descripcion': 'Mantenimiento de areas verdes', 'requiere_especializacion': False},
        {'nombre': 'Seguridad', 'descripcion': 'Control de accesos y vigilancia', 'requiere_especializacion': True},
        {'nombre': 'Recepcionista', 'descripcion': 'Atencion en lobby y registro de visitas', 'requiere_especializacion': False},
        {'nombre': 'Tecnico De Mantenimiento', 'descripcion': 'Reparaciones y mantenimiento especializado', 'requiere_especializacion': True},
        {'nombre': 'Plomero', 'descripcion': 'Mantenimiento y reparacion de sistemas de agua', 'requiere_especializacion': True},
        {'nombre': 'Electricista', 'descripcion': 'Mantenimiento electrico', 'requiere_especializacion': True},
        {'nombre': 'Pintor', 'descripcion': 'Realiza trabajos de pintura', 'requiere_especializacion': False},
        {'nombre': 'Otro', 'descripcion': 'Puesto personalizado', 'requiere_especializacion': False},
    ]
    
    puestos = []
    for i in range(min(num_puestos, len(puestos_data))):
        data = puestos_data[i]
        
        puesto, created = Puesto.objects.get_or_create(
            nombre=data['nombre'],
            defaults={
                'descripcion': data['descripcion'],
                'requiere_especializacion': data['requiere_especializacion']
            }
        )
        
        puestos.append(puesto)
        print(f"Puesto '{puesto.nombre}' {'creado' if created else 'ya existe'}")
    
    return puestos


def crear_usuarios_personal(num_empleados=NUM_EMPLEADOS):
    """Crear usuarios específicamente con rol Personal para empleados"""
    print(f"\nCreando {num_empleados} usuarios con rol Personal...")
    
    User = get_user_model()
    
    # Obtener rol Personal
    try:
        rol_personal = Rol.objects.get(nombre='Personal')
    except Rol.DoesNotExist:
        print("Error: Rol 'Personal' no existe")
        return []
    
    nombres = ['José', 'Manuel', 'Francisco', 'Antonio', 'Rosa', 'Carmen', 'Elena', 'Isabel', 
               'Ricardo', 'Fernando', 'Guadalupe', 'Alejandro', 'Javier', 'Raúl', 'Teresa']
    
    apellidos = ['Moreno', 'Jiménez', 'Ruiz', 'Navarro', 'Romero', 'Gutiérrez', 'Muñoz', 'Álvarez',
                'Castillo', 'Ortega', 'Delgado', 'Castro', 'Ortiz', 'Rubio', 'Marín']
    
    usuarios_personal = []
    for i in range(num_empleados):
        nombre = random.choice(nombres)
        apellido = random.choice(apellidos)
        username = f"emp.{nombre.lower()}.{apellido.lower()}{random.randint(1, 99)}"
        email = f"{username}@torresegura.com"
        
        # Evitar duplicados
        while User.objects.filter(username=username).exists():
            username = f"emp.{nombre.lower()}.{apellido.lower()}{random.randint(1, 999)}"
        
        while User.objects.filter(email=email).exists():
            email = f"{username}{random.randint(1, 99)}@torresegura.com"
        
        numero_documento = f"{random.randint(10000000, 99999999)}"
        telefono = f"{random.randint(1000000000, 9999999999)}"
        
        # CRUCIAL: Crear usuario con rol Personal
        user = User.objects.create_user(
            username=username,
            email=email,
            password='personal123',
            first_name=nombre,
            last_name=apellido,
            rol=rol_personal,  # ESTO ES CLAVE
            tipo_documento='DNI',
            numero_documento=numero_documento,
            telefono=telefono,
            is_active=True
        )
        
        usuarios_personal.append(user)
        print(f"Usuario Personal creado: {username}")
    
    print(f"Total: {len(usuarios_personal)} usuarios Personal creados")
    return usuarios_personal


def generar_empleados(usuarios_personal, puestos, edificios, admin_user):
    """Generar empleados para el condominio usando usuarios con rol Personal"""
    print(f"\nGenerando empleados...")
    
    if not usuarios_personal:
        print("No hay usuarios Personal para crear empleados")
        return []
    
    if not puestos:
        print("No hay puestos para asignar empleados")
        return []
    
    tipos_contrato = ['PERMANENTE', 'TEMPORAL', 'EXTERNO']
    especialidades = ['General', 'Hidráulica', 'Eléctrica', 'Administrativa', 'Jardinería', 'Seguridad']
    
    empleados = []
    for usuario in usuarios_personal:
        puesto = random.choice(puestos)
        edificio = random.choice(edificios) if edificios else None
        
        # Fecha de contratación entre 1 y 10 años atrás
        fecha_contratacion = timezone.now().date() - timedelta(days=random.randint(30, 3650))
        
        tipo_contrato = random.choice(tipos_contrato)
        salario = decimal.Decimal(str(random.randint(8000, 25000)))
        
        # Contacto de emergencia
        contacto_emergencia = f"{random.choice(['Juan', 'María', 'Pedro', 'Ana', 'Luis'])} {random.choice(['García', 'Pérez', 'López', 'Rodríguez'])}"
        telefono_emergencia = f"{random.randint(1000000000, 9999999999)}"
        
        # Especialidad para puestos especializados
        especialidad = random.choice(especialidades) if puesto.requiere_especializacion else ""
        
        try:
            empleado = Empleado.objects.create(
                usuario=usuario,
                puesto=puesto,
                edificio=edificio,
                fecha_contratacion=fecha_contratacion,
                tipo_contrato=tipo_contrato,
                salario=salario,
                contacto_emergencia=contacto_emergencia,
                telefono_emergencia=telefono_emergencia,
                especialidad=especialidad,
                activo=True,
                creado_por=admin_user
            )
            
            empleados.append(empleado)
            print(f"Empleado creado: {usuario.get_full_name()} - {puesto.nombre}")
            
        except Exception as e:
            print(f"Error al crear empleado para {usuario.username}: {str(e)}")
            continue
    
    print(f"Total: {len(empleados)} empleados creados")
    return empleados


def generar_asignaciones(empleados, edificios, viviendas, admin_user, num_asignaciones=NUM_ASIGNACIONES):
    """Generar asignaciones de trabajo para los empleados"""
    print(f"\nGenerando {num_asignaciones} asignaciones de trabajo...")
    
    if not empleados:
        print("No hay empleados para asignar tareas")
        return []
    
    # Filtrar empleados activos
    empleados_activos = [e for e in empleados if e.activo]
    
    if not empleados_activos:
        print("No hay empleados activos para asignar tareas")
        return []
    
    tipos_asignacion = ['TAREA', 'RESPONSABILIDAD']
    estados = ['PENDIENTE', 'EN_PROGRESO', 'COMPLETADA', 'CANCELADA']
    prioridades = [1, 2, 2, 2, 3, 3, 4]  # Más probabilidad de prioridad normal
    
    titulos_tareas = [
        "Limpieza de áreas comunes", "Reparación de luminarias", "Mantenimiento de jardines",
        "Revisión de sistemas de seguridad", "Limpieza de piscina", "Reparación de filtraciones",
        "Pintura de pasillos", "Mantenimiento preventivo de elevadores", "Limpieza de estacionamiento",
        "Revisión de bombas de agua", "Instalación de cámaras de seguridad", "Reparación de cerraduras",
        "Mantenimiento de aires acondicionados", "Limpieza de ductos de ventilación"
    ]
    
    asignaciones = []
    comentarios_creados = 0
    
    for i in range(num_asignaciones):
        empleado = random.choice(empleados_activos)
        tipo = random.choice(tipos_asignacion)
        
        # Probabilidades diferentes para estados según tipo
        if tipo == 'TAREA':
            estado = random.choices(estados, weights=[0.3, 0.3, 0.3, 0.1])[0]
        else:
            estado = random.choices(estados, weights=[0.2, 0.5, 0.2, 0.1])[0]
        
        # Título y descripción
        titulo = random.choice(titulos_tareas)
        descripcion = f"Descripción detallada para la tarea '{titulo}'. Incluye instrucciones específicas para su realización."
        
        # Fechas
        fecha_inicio = timezone.now().date() - timedelta(days=random.randint(0, 30))
        
        # Para tareas completadas, añadir fecha fin
        fecha_fin = None
        fecha_completada = None
        tiempo_estimado_horas = random.randint(2, 24)
        
        # CORRECCIÓN: Siempre asignar fecha_fin para TAREAS
        if tipo == 'TAREA':
            fecha_fin = fecha_inicio + timedelta(days=random.randint(1, 15))
            if estado == 'COMPLETADA':
                fecha_completada = timezone.now() - timedelta(
                    days=random.randint(0, 10),
                    hours=random.randint(0, 23)
                )
        elif tipo == 'RESPONSABILIDAD':
            # Para responsabilidades, fecha_fin es opcional
            if random.random() < 0.7:  # 70% tienen fecha fin
                fecha_fin = fecha_inicio + timedelta(days=random.randint(30, 180))
            if estado == 'COMPLETADA':
                fecha_completada = timezone.now() - timedelta(
                    days=random.randint(0, 10),
                    hours=random.randint(0, 23)
                )
        
        # Edificio y vivienda (opcional)
        edificio = random.choice(edificios) if edificios else None
        vivienda = None
        if random.random() < 0.5 and edificio:  # 50% de probabilidad de asignar a una vivienda específica
            viviendas_edificio = [v for v in viviendas if v.edificio == edificio and v.activo]
            if viviendas_edificio:
                vivienda = random.choice(viviendas_edificio)
        
        prioridad = random.choice(prioridades)
        notas = f"Notas adicionales para la asignación. Prioridad: {prioridad}."
        
        try:
            asignacion = Asignacion.objects.create(
                empleado=empleado,
                tipo=tipo,
                titulo=titulo,
                descripcion=descripcion,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                edificio=edificio,
                vivienda=vivienda,
                estado=estado,
                prioridad=prioridad,
                notas=notas,
                asignado_por=admin_user,
                fecha_completada=fecha_completada,
                tiempo_estimado_horas=tiempo_estimado_horas
            )
            
            asignaciones.append(asignacion)
            
            # Añadir comentarios a algunas asignaciones
            num_comentarios = random.randint(0, 3)
            for j in range(num_comentarios):
                fecha_comentario_delta = random.randint(0, 30)
                fecha_comentario = timezone.now() - timedelta(
                    days=fecha_comentario_delta,
                    hours=random.randint(0, 23)
                )
                
                comentario_texto = random.choice([
                    "Avance de la tarea según lo planeado.",
                    "Se requieren materiales adicionales.",
                    "Trabajo completado satisfactoriamente.",
                    "Tarea retrasada por falta de acceso.",
                    "Se encontraron problemas adicionales.",
                    f"Actualización: {random.randint(10, 90)}% completado."
                ])
                
                ComentarioAsignacion.objects.create(
                    asignacion=asignacion,
                    usuario=random.choice([admin_user, empleado.usuario]),
                    fecha=fecha_comentario,
                    comentario=comentario_texto
                )
                comentarios_creados += 1
                
        except Exception as e:
            print(f"Error al crear asignación: {str(e)}")
            continue
    
    print(f"Total: {len(asignaciones)} asignaciones creadas con {comentarios_creados} comentarios")
    return asignaciones


def generar_visitas(residentes, admin_user, num_visitas=NUM_VISITAS):
    """Generar visitas para los residentes"""
    print(f"\nGenerando {num_visitas} visitas...")
    
    if not residentes:
        print("No hay residentes para generar visitas")
        return []
    
    # Filtrar residentes activos
    residentes_activos = [r for r in residentes if r.activo and r.vivienda and r.vivienda.activo]
    
    if not residentes_activos:
        print("No hay residentes activos para generar visitas")
        return []
    
    nombres_visitantes = ['Juan', 'Pedro', 'María', 'Ana', 'Luis', 'Carlos', 'Sofía', 'Laura', 'Roberto', 'Miguel',
                        'Lucía', 'Fernanda', 'Gabriel', 'Jorge', 'Diana', 'Patricia', 'Andrés', 'Eduardo']
    
    apellidos_visitantes = ['García', 'Pérez', 'Rodríguez', 'López', 'Martínez', 'González', 'Hernández', 'Sánchez',
                          'Ramírez', 'Torres', 'Flores', 'Rivera', 'Cruz', 'Morales', 'Reyes', 'Díaz', 'Mendoza']
    
    motivos_visita = [
        "Visita familiar", "Entrega de paquetería", "Mantenimiento programado", 
        "Visita social", "Entrega de comida", "Reunión de trabajo", 
        "Inspección de servicios", "Entrega de correspondencia"
    ]
    
    visitas = []
    for i in range(num_visitas):
        residente = random.choice(residentes_activos)
        
        nombre_visitante = f"{random.choice(nombres_visitantes)} {random.choice(apellidos_visitantes)}"
        documento_visitante = f"{random.randint(10000000, 99999999)}"
        
        # Fecha de entrada (últimos 60 días)
        fecha_hora_entrada = timezone.now() - timedelta(
            days=random.randint(0, 60),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Fecha de salida (opcional)
        fecha_hora_salida = None
        if random.random() < 0.7:  # 70% de visitas ya han salido
            horas_visita = random.randint(1, 8)
            fecha_hora_salida = fecha_hora_entrada + timedelta(hours=horas_visita)
        
        motivo = random.choice(motivos_visita)
        
        visita = Visita.objects.create(
            nombre_visitante=nombre_visitante,
            documento_visitante=documento_visitante,
            vivienda_destino=residente.vivienda,
            residente_autoriza=residente,
            fecha_hora_entrada=fecha_hora_entrada,
            fecha_hora_salida=fecha_hora_salida,
            motivo=motivo,
            registrado_por=admin_user
        )
        
        visitas.append(visita)
    
    print(f"Total: {len(visitas)} visitas creadas")
    return visitas


def generar_movimientos_residentes(residentes, num_movimientos=NUM_MOVIMIENTOS):
    """Generar movimientos de entrada/salida para los residentes"""
    print(f"\nGenerando {num_movimientos} movimientos de residentes...")
    
    if not residentes:
        print("No hay residentes para generar movimientos")
        return []
    
    # Filtrar residentes activos
    residentes_activos = [r for r in residentes if r.activo]
    
    if not residentes_activos:
        print("No hay residentes activos para generar movimientos")
        return []
    
    movimientos = []
    for i in range(num_movimientos):
        residente = random.choice(residentes_activos)
        
        # Decidir si es entrada o salida
        es_entrada = random.random() < 0.5
        
        # Fecha y hora (últimos 30 días)
        fecha_hora = timezone.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        vehiculo = random.random() < 0.4  # 40% con vehículo
        
        # Placa solo si hay vehículo
        placa_vehiculo = ""
        if vehiculo:
            letras = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
            numeros = "".join(random.choices("0123456789", k=3))
            placa_vehiculo = f"{letras}-{numeros}"
        
        movimiento = MovimientoResidente.objects.create(
            residente=residente,
            fecha_hora_entrada=fecha_hora if es_entrada else None,
            fecha_hora_salida=fecha_hora if not es_entrada else None,
            vehiculo=vehiculo,
            placa_vehiculo=placa_vehiculo
        )
        
        movimientos.append(movimiento)
    
    print(f"Total: {len(movimientos)} movimientos de residentes creados")
    return movimientos


def generar_conceptos_cuota(num_conceptos=NUM_CONCEPTOS_CUOTA):
    """Generar conceptos de cuota para el sistema financiero"""
    print(f"\nGenerando {num_conceptos} conceptos de cuota...")
    
    conceptos_data = [
        {
            'nombre': 'Cuota de Mantenimiento', 
            'descripcion': 'Cuota mensual para gastos generales de mantenimiento',
            'monto_base': decimal.Decimal('1200.00'),
            'periodicidad': 'MENSUAL',
            'aplica_recargo': True,
            'porcentaje_recargo': decimal.Decimal('5.00')
        },
        {
            'nombre': 'Cuota Extraordinaria', 
            'descripcion': 'Cuota para proyectos especiales o gastos no previstos',
            'monto_base': decimal.Decimal('3000.00'),
            'periodicidad': 'UNICA',
            'aplica_recargo': True,
            'porcentaje_recargo': decimal.Decimal('10.00')
        },
        {
            'nombre': 'Fondo de Reserva', 
            'descripcion': 'Aportación trimestral al fondo de reserva del condominio',
            'monto_base': decimal.Decimal('800.00'),
            'periodicidad': 'TRIMESTRAL',
            'aplica_recargo': False,
            'porcentaje_recargo': decimal.Decimal('0.00')
        },
        {
            'nombre': 'Cuota de Agua', 
            'descripcion': 'Pago del servicio de agua potable',
            'monto_base': decimal.Decimal('350.00'),
            'periodicidad': 'MENSUAL',
            'aplica_recargo': True,
            'porcentaje_recargo': decimal.Decimal('3.00')
        }
    ]
    
    conceptos = []
    for i in range(min(num_conceptos, len(conceptos_data))):
        data = conceptos_data[i]
        
        concepto, created = ConceptoCuota.objects.get_or_create(
            nombre=data['nombre'],
            defaults={
                'descripcion': data['descripcion'],
                'monto_base': data['monto_base'],
                'periodicidad': data['periodicidad'],
                'aplica_recargo': data['aplica_recargo'],
                'porcentaje_recargo': data['porcentaje_recargo'],
                'activo': True
            }
        )
        
        conceptos.append(concepto)
        print(f"Concepto '{concepto.nombre}' {'creado' if created else 'ya existe'}")
    
    return conceptos


def generar_cuotas(conceptos, viviendas, num_cuotas=NUM_CUOTAS):
    """Generar cuotas para las viviendas"""
    print(f"\nGenerando {num_cuotas} cuotas...")
    
    if not conceptos or not viviendas:
        print("No hay conceptos o viviendas para generar cuotas")
        return []
    
    # Filtrar viviendas activas
    viviendas_activas = [v for v in viviendas if v.activo]
    
    if not viviendas_activas:
        print("No hay viviendas activas para generar cuotas")
        return []
    
    cuotas = []
    cuotas_por_vivienda = min(6, num_cuotas // len(viviendas_activas) + 1)
    
    for vivienda in viviendas_activas:
        for i in range(cuotas_por_vivienda):
            if len(cuotas) >= num_cuotas:
                break
                
            concepto = random.choice(conceptos)
            
            # Fecha de emisión (últimos 12 meses)
            meses_atras = random.randint(0, 11)
            dia_emision = random.randint(1, 10)  # Primeros 10 días del mes
            
            hoy = timezone.now().date()
            # Calcular mes de emisión
            if hoy.month - meses_atras <= 0:
                mes_emision = hoy.month - meses_atras + 12
                año_emision = hoy.year - 1
            else:
                mes_emision = hoy.month - meses_atras
                año_emision = hoy.year
                
            fecha_emision = date(año_emision, mes_emision, dia_emision)
            
            # Fecha de vencimiento (15-30 días después)
            dias_vencimiento = random.randint(15, 30)
            fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
            
            # Monto (incluir variación sobre el monto base)
            variacion = random.uniform(-0.05, 0.15)  # Entre -5% y +15%
            monto_base = float(concepto.monto_base)
            monto = decimal.Decimal(str(round(monto_base * (1 + variacion), 2)))
            
            # Estado pagado (más probabilidad en cuotas antiguas)
            probabilidad_pagada = 0.9 if meses_atras > 2 else 0.5
            pagada = random.random() < probabilidad_pagada
            
            # Recargo para cuotas vencidas no pagadas
            recargo = decimal.Decimal('0.00')
            if not pagada and fecha_vencimiento < hoy and concepto.aplica_recargo:
                meses_vencida = (hoy.year - fecha_vencimiento.year) * 12 + hoy.month - fecha_vencimiento.month
                if meses_vencida > 0:
                    porcentaje_mensual = float(concepto.porcentaje_recargo) / 100
                    recargo_calculado = float(monto) * porcentaje_mensual * meses_vencida
                    recargo = decimal.Decimal(str(round(recargo_calculado, 2)))
            
            cuota = Cuota.objects.create(
                concepto=concepto,
                vivienda=vivienda,
                monto=monto,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                pagada=pagada,
                recargo=recargo,
                notas=f"Cuota de {concepto.nombre} para {vivienda}. Período: {fecha_emision.strftime('%B %Y')}"
            )
            
            cuotas.append(cuota)
            
            if len(cuotas) % 50 == 0:
                print(f"Creadas {len(cuotas)} cuotas...")
    
    print(f"Total: {len(cuotas)} cuotas creadas")
    return cuotas


def generar_pagos(cuotas, residentes, admin_user, num_pagos=NUM_PAGOS):
    """Generar pagos para las cuotas"""
    print(f"\nGenerando {num_pagos} pagos...")
    
    if not cuotas or not residentes:
        print("No hay cuotas o residentes para generar pagos")
        return []
    
    # Filtrar cuotas pagadas
    cuotas_pagadas = [c for c in cuotas if c.pagada]
    
    if not cuotas_pagadas:
        print("No hay cuotas pagadas para generar pagos")
        return []
    
    # Mapear residentes por vivienda
    residentes_por_vivienda = {}
    for residente in residentes:
        if residente.vivienda and residente.activo:
            if residente.vivienda.id not in residentes_por_vivienda:
                residentes_por_vivienda[residente.vivienda.id] = []
            residentes_por_vivienda[residente.vivienda.id].append(residente)
    
    metodos_pago = ['EFECTIVO', 'TRANSFERENCIA', 'CHEQUE', 'TARJETA']
    estados_pago = ['VERIFICADO', 'PENDIENTE', 'RECHAZADO']
    pesos_estados = [0.7, 0.2, 0.1]  # 70% verificados, 20% pendientes, 10% rechazados
    
    pagos = []
    pagos_cuota = []
    
    # Agrupar cuotas por vivienda
    cuotas_por_vivienda = {}
    for cuota in cuotas_pagadas:
        if cuota.vivienda.id not in cuotas_por_vivienda:
            cuotas_por_vivienda[cuota.vivienda.id] = []
        cuotas_por_vivienda[cuota.vivienda.id].append(cuota)
    
    # Crear pagos
    for vivienda_id, cuotas_vivienda in cuotas_por_vivienda.items():
        # Saltar si no hay residentes para esta vivienda
        if vivienda_id not in residentes_por_vivienda:
            continue
            
        if len(pagos) >= num_pagos:
            break
            
        residentes_vivienda = residentes_por_vivienda[vivienda_id]
        
        # Agrupar algunas cuotas en un solo pago
        random.shuffle(cuotas_vivienda)
        
        i = 0
        while i < len(cuotas_vivienda) and len(pagos) < num_pagos:
            # Determinar cuántas cuotas incluir en este pago (1-3)
            num_cuotas_pago = min(random.randint(1, 3), len(cuotas_vivienda) - i)
            cuotas_pago = cuotas_vivienda[i:i+num_cuotas_pago]
            i += num_cuotas_pago
            
            # Calcular monto total del pago
            monto_total = sum(float(cuota.monto) for cuota in cuotas_pago)
            monto_total = decimal.Decimal(str(round(monto_total, 2)))
            
            # Fecha de pago (cercana a la emisión de la cuota más reciente)
            cuota_reciente = max(cuotas_pago, key=lambda c: c.fecha_emision)
            dias_despues = random.randint(1, 20)
            fecha_pago = cuota_reciente.fecha_emision + timedelta(days=dias_despues)
            
            # No crear pagos con fecha futura
            if fecha_pago > timezone.now().date():
                fecha_pago = timezone.now().date() - timedelta(days=random.randint(0, 5))
            
            # Residente que realiza el pago
            residente = random.choice(residentes_vivienda)
            
            # Método de pago
            metodo_pago = random.choice(metodos_pago)
            
            # Referencia según método de pago
            referencia = ""
            if metodo_pago == 'TRANSFERENCIA':
                referencia = f"TRANS-{random.randint(100000, 999999)}"
            elif metodo_pago == 'CHEQUE':
                referencia = f"CH-{random.randint(1000, 9999)}"
            elif metodo_pago == 'TARJETA':
                referencia = f"CARD-{random.randint(1000, 9999)}"
            
            # Estado del pago
            estado = random.choices(estados_pago, weights=pesos_estados)[0]
            
            # Crear pago
            pago = Pago.objects.create(
                vivienda=residente.vivienda,
                residente=residente,
                monto=monto_total,
                fecha_pago=fecha_pago,
                metodo_pago=metodo_pago,
                referencia=referencia,
                estado=estado,
                registrado_por=admin_user,
                notas=f"Pago de {len(cuotas_pago)} cuotas. Realizado por {residente.usuario.get_full_name()}"
            )
            
            # Si está verificado, añadir fecha y usuario
            if estado == 'VERIFICADO':
                pago.verificado_por = admin_user
                pago.fecha_verificacion = timezone.now() - timedelta(days=random.randint(0, 5))
                pago.save()
            
            # Crear relaciones PagoCuota
            for cuota in cuotas_pago:
                pago_cuota = PagoCuota.objects.create(
                    pago=pago,
                    cuota=cuota,
                    monto_aplicado=cuota.monto
                )
                pagos_cuota.append(pago_cuota)
            
            pagos.append(pago)
    
    print(f"Total: {len(pagos)} pagos creados con {len(pagos_cuota)} relaciones a cuotas")
    return pagos


def generar_categorias_gasto(num_categorias=NUM_CATEGORIAS_GASTO):
    """Generar categorías de gasto para el sistema financiero"""
    print(f"\nGenerando {num_categorias} categorías de gasto...")
    
    categorias_data = [
        {'nombre': 'Mantenimiento', 'descripcion': 'Gastos de mantenimiento general', 'presupuesto_mensual': decimal.Decimal('15000.00'), 'color': '#4CAF50'},
        {'nombre': 'Servicios', 'descripcion': 'Servicios públicos (luz, agua, gas)', 'presupuesto_mensual': decimal.Decimal('8000.00'), 'color': '#2196F3'},
        {'nombre': 'Seguridad', 'descripcion': 'Gastos relacionados con seguridad', 'presupuesto_mensual': decimal.Decimal('12000.00'), 'color': '#F44336'},
        {'nombre': 'Limpieza', 'descripcion': 'Servicios de limpieza y materiales', 'presupuesto_mensual': decimal.Decimal('5000.00'), 'color': '#9C27B0'},
        {'nombre': 'Administrativos', 'descripcion': 'Gastos administrativos', 'presupuesto_mensual': decimal.Decimal('3500.00'), 'color': '#FF9800'},
        {'nombre': 'Áreas Comunes', 'descripcion': 'Mantenimiento de áreas recreativas', 'presupuesto_mensual': decimal.Decimal('4500.00'), 'color': '#795548'}
    ]
    
    categorias = []
    for i in range(min(num_categorias, len(categorias_data))):
        data = categorias_data[i]
        
        categoria, created = CategoriaGasto.objects.get_or_create(
            nombre=data['nombre'],
            defaults={
                'descripcion': data['descripcion'],
                'presupuesto_mensual': data['presupuesto_mensual'],
                'color': data['color'],
                'activo': True
            }
        )
        
        categorias.append(categoria)
        print(f"Categoría '{categoria.nombre}' {'creada' if created else 'ya existe'}")
    
    return categorias


def generar_gastos(categorias, edificios, admin_user, num_gastos=NUM_GASTOS):
    """Generar gastos para el condominio"""
    print(f"\nGenerando {num_gastos} gastos...")
    
    if not categorias:
        print("No hay categorías para generar gastos")
        return []
    
    conceptos_gasto = [
        "Reparación de bombas de agua", "Pintura de áreas comunes", "Servicio de limpieza",
        "Pago de servicio eléctrico", "Mantenimiento de elevadores", "Suministros de oficina",
        "Servicio de vigilancia", "Mantenimiento de jardines", "Reparación de luminarias",
        "Fumigación", "Servicios de plomería", "Limpieza de cisternas",
        "Reparación de fugas", "Material de limpieza", "Mantenimiento de piscina",
        "Pago de agua", "Reparación de portón eléctrico", "Mantenimiento de cámaras de seguridad"
    ]
    
    proveedores = [
        "Servicios Integrales S.A.", "Mantenimiento Express", "ElectroSoluciones",
        "Plomería Profesional", "Jardines Verdes", "Seguridad Total",
        "Limpieza Profunda", "Servicios Municipales", "Pinturas y Acabados",
        "Reparaciones Generales", "Constructora Moderna", "Servicios Hidráulicos"
    ]
    
    tipos_gasto = ['ORDINARIO', 'EXTRAORDINARIO', 'MANTENIMIENTO', 'SERVICIO']
    estados_gasto = ['PENDIENTE', 'PAGADO', 'CANCELADO']
    pesos_estados = [0.2, 0.7, 0.1]  # 20% pendientes, 70% pagados, 10% cancelados
    
    gastos = []
    for i in range(num_gastos):
        categoria = random.choice(categorias)
        
        # Concepto y descripción
        concepto = random.choice(conceptos_gasto)
        descripcion = f"Descripción detallada para el gasto '{concepto}'."
        
        # Monto (ajustado según la categoría)
        base_monto = float(categoria.presupuesto_mensual) / 5  # 20% del presupuesto mensual
        variacion = random.uniform(0.5, 1.5)  # Entre 50% y 150% del base
        monto = decimal.Decimal(str(round(base_monto * variacion, 2)))
        
        # Fechas
        dias_atras = random.randint(0, 365)
        fecha = timezone.now().date() - timedelta(days=dias_atras)
        
        # Proveedor y factura
        proveedor = random.choice(proveedores)
        factura = f"FAC-{random.randint(1000, 9999)}"
        
        # Estado y fecha de pago
        estado = random.choices(estados_gasto, weights=pesos_estados)[0]
        fecha_pago = None
        if estado == 'PAGADO':
            fecha_pago = fecha + timedelta(days=random.randint(1, 15))
        
        # Tipo de gasto
        tipo_gasto = random.choice(tipos_gasto)
        
        # Presupuestado y recurrente
        presupuestado = random.random() < 0.6  # 60% presupuestados
        recurrente = random.random() < 0.3  # 30% recurrentes
        
        gasto = Gasto.objects.create(
            categoria=categoria,
            concepto=concepto,
            descripcion=descripcion,
            monto=monto,
            fecha=fecha,
            fecha_pago=fecha_pago,
            proveedor=proveedor,
            factura=factura,
            estado=estado,
            tipo_gasto=tipo_gasto,
            registrado_por=admin_user,
            autorizado_por=admin_user if estado != 'PENDIENTE' else None,
            notas=f"Gasto de {tipo_gasto} en concepto de {concepto}.",
            presupuestado=presupuestado,
            recurrente=recurrente
        )
        
        gastos.append(gasto)
        
        if i % 10 == 0:
            print(f"Creados {i} gastos...")
    
    print(f"Total: {len(gastos)} gastos creados")
    return gastos


def generar_estados_cuenta(viviendas, num_estados=NUM_ESTADOS_CUENTA):
    """Generar estados de cuenta para las viviendas"""
    print(f"\nGenerando {num_estados} estados de cuenta...")
    
    if not viviendas:
        print("No hay viviendas para generar estados de cuenta")
        return []
    
    # Filtrar viviendas activas
    viviendas_activas = [v for v in viviendas if v.activo]
    
    if not viviendas_activas:
        print("No hay viviendas activas para generar estados de cuenta")
        return []
    
    estados = []
    estados_por_vivienda = min(3, num_estados // len(viviendas_activas) + 1)
    
    for vivienda in viviendas_activas:
        # Generar estados de cuenta para los últimos meses
        for i in range(min(estados_por_vivienda, 6)):  # Máximo 6 meses atrás
            if len(estados) >= num_estados:
                break
                
            # Calcular período (mes anterior al actual - i meses)
            hoy = timezone.now().date()
            
            # Mes anterior
            if hoy.month == 1:
                mes_anterior = 12
                año_anterior = hoy.year - 1
            else:
                mes_anterior = hoy.month - 1
                año_anterior = hoy.year
            
            # Restar i meses
            mes_estado = mes_anterior - i
            año_estado = año_anterior
            
            while mes_estado <= 0:
                mes_estado += 12
                año_estado -= 1
            
            # Primer día del mes
            fecha_inicio = date(año_estado, mes_estado, 1)
            
            # Último día del mes
            if mes_estado == 12:
                ultimo_dia = date(año_estado + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo_dia = date(año_estado, mes_estado + 1, 1) - timedelta(days=1)
            
            # Verificar si ya existe un estado para este período
            existe = EstadoCuenta.objects.filter(
                vivienda=vivienda,
                fecha_inicio=fecha_inicio,
                fecha_fin=ultimo_dia
            ).exists()
            
            if existe:
                continue
            
            # Saldo anterior
            saldo_anterior = decimal.Decimal(str(random.randint(-5000, 2000)))
            
            # Crear estado de cuenta
            try:
                estado = EstadoCuenta.objects.create(
                    vivienda=vivienda,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=ultimo_dia,
                    saldo_anterior=saldo_anterior
                )
                
                # Calcular totales
                estado.calcular_totales()
                
                # Simular envío en algunos casos
                if random.random() < 0.6:  # 60% enviados
                    estado.enviado = True
                    estado.fecha_envio = timezone.now() - timedelta(days=random.randint(1, 30))
                    estado.save()
                
                estados.append(estado)
                
            except Exception as e:
                print(f"Error creando estado de cuenta: {str(e)}")
                continue
    
    print(f"Total: {len(estados)} estados de cuenta creados")
    return estados


def main():
    """Función principal que coordina el llenado de la base de datos"""
    try:
        with transaction.atomic():
            print("=== INICIANDO PROCESO DE LLENADO DE BASE DE DATOS ===")
            
            # 1. Crear datos base
            admin_rol, admin_user = crear_datos_base()
            
            # 2. Generar roles
            roles = generar_roles()
            
            # 3. Generar usuarios (excluyendo Personal)
            usuarios = generar_usuarios(roles)
            usuarios.append(admin_user)  # Añadir usuario administrador
            
            # 4. Generar edificios
            edificios = generar_edificios()
            
            # 5. Generar viviendas
            viviendas = generar_viviendas(edificios)
            
            # 6. Generar residentes
            residentes = generar_residentes(usuarios, viviendas)
            
            # 7. Generar puestos
            puestos = generar_puestos()
            
            # 8. Crear usuarios específicos para Personal
            usuarios_personal = crear_usuarios_personal()
            
            # 9. Generar empleados usando usuarios Personal
            empleados = generar_empleados(usuarios_personal, puestos, edificios, admin_user)
            
            # 10. Generar asignaciones
            asignaciones = generar_asignaciones(empleados, edificios, viviendas, admin_user)
            
            # 11. Generar visitas
            visitas = generar_visitas(residentes, admin_user)
            
            # 12. Generar movimientos de residentes
            movimientos = generar_movimientos_residentes(residentes)
            
            # 13. Generar conceptos de cuota
            conceptos = generar_conceptos_cuota()
            
            # 14. Generar cuotas
            cuotas = generar_cuotas(conceptos, viviendas)
            
            # 15. Generar pagos
            pagos = generar_pagos(cuotas, residentes, admin_user)
            
            # 16. Generar categorías de gasto
            categorias = generar_categorias_gasto()
            
            # 17. Generar gastos
            gastos = generar_gastos(categorias, edificios, admin_user)
            
            # 18. Generar estados de cuenta
            estados = generar_estados_cuenta(viviendas)
            
            print("\n" + "="*70)
            print("¡PROCESO DE LLENADO COMPLETADO CON ÉXITO!")
            print("="*70)
            print(f"""
📊 RESUMEN DE DATOS GENERADOS:
──────────────────────────────
👥 Usuarios y Roles:
   • Roles: {len(roles)}
   • Usuarios regulares: {len(usuarios)}
   • Usuarios Personal: {len(usuarios_personal)}
   • Total usuarios: {len(usuarios) + len(usuarios_personal)}

🏢 Infraestructura:
   • Edificios: {len(edificios)}
   • Viviendas: {len(viviendas)}
   • Residentes: {len(residentes)}

👷 Personal:
   • Puestos: {len(puestos)}
   • Empleados: {len(empleados)}
   • Asignaciones: {len(asignaciones)}

🚪 Control de Acceso:
   • Visitas: {len(visitas)}
   • Movimientos: {len(movimientos)}

💰 Sistema Financiero:
   • Conceptos de Cuota: {len(conceptos)}
   • Cuotas: {len(cuotas)}
   • Pagos: {len(pagos)}
   • Categorías de Gasto: {len(categorias)}
   • Gastos: {len(gastos)}
   • Estados de Cuenta: {len(estados)}

🔑 CREDENCIALES DE ACCESO:
──────────────────────────
👨‍💼 Administrador:
   • Usuario: admin
   • Contraseña: admin123
   • Email: admin@torresegura.com

👷 Personal (ejemplo):
   • Usuario: {usuarios_personal[0].username if usuarios_personal else 'N/A'}
   • Contraseña: personal123
   • Email: {usuarios_personal[0].email if usuarios_personal else 'N/A'}

📝 NOTAS IMPORTANTES:
──────────────────────
✅ Todos los empleados tienen rol 'Personal'
✅ Los residentes tienen rol 'Residente'
✅ El sistema financiero está poblado con datos realistas
✅ Las fechas están distribuidas en los últimos 12 meses
✅ Los estados de cuenta se generan automáticamente

🚀 El sistema está listo para usar!
            """)
            
            print("="*70)
    
    except Exception as e:
        print(f"\n❌ ERROR DURANTE EL PROCESO: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n🔄 La transacción ha sido cancelada y no se han guardado cambios.")


if __name__ == "__main__":
    main()