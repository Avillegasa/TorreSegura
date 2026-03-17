#!/usr/bin/env python
"""
Script inteligente que detecta automáticamente los campos disponibles
"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Configurar entorno Django
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condominio_app.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from usuarios.models import Rol

Usuario = get_user_model()

def get_model_fields(model):
    """Obtiene los nombres de campos de un modelo"""
    return [field.name for field in model._meta.fields]

def crear_datos_inteligentes():
    print("🚀 Iniciando creación de datos inteligentes...")
    
    try:
        with transaction.atomic():
            # 1. Crear roles básicos
            print("👥 Creando roles...")
            roles = {
                'Administrador': 'Control total del sistema',
                'Gerente': 'Gestión administrativa', 
                'Residente': 'Propietario o inquilino',
                'Empleado': 'Personal de servicios'
            }
            
            for nombre, descripcion in roles.items():
                Rol.objects.get_or_create(nombre=nombre, defaults={'descripcion': descripcion})
            
            # 2. Crear usuarios administradores
            print("🔑 Creando usuarios administradores...")
            rol_admin = Rol.objects.get(nombre='Administrador')
            
            # Verificar campos de Usuario
            usuario_fields = get_model_fields(Usuario)
            print(f"📋 Campos Usuario: {usuario_fields}")
            
            if not Usuario.objects.filter(username='admin').exists():
                admin_data = {
                    'username': 'admin',
                    'email': 'admin@torresegura.com',
                    'password': 'admin123',
                    'first_name': 'Carlos',
                    'last_name': 'Administrador'
                }
                
                # Agregar campos opcionales si existen
                if 'telefono' in usuario_fields:
                    admin_data['telefono'] = '+591-70000001'
                
                admin = Usuario.objects.create_superuser(**admin_data)
                admin.rol = rol_admin
                admin.save()
            
            # 3. Crear edificios
            print("🏢 Creando edificios...")
            from viviendas.models import Edificio
            
            edificio_fields = get_model_fields(Edificio)
            print(f"📋 Campos Edificio: {edificio_fields}")
            
            edificio_data = {
                'nombre': 'Torre Aurora',
                'direccion': 'Av. Arce #2570',
                'pisos': 15
            }
            
            # Agregar campos opcionales
            if 'fecha_construccion' in edificio_fields:
                edificio_data['fecha_construccion'] = timezone.now().date() - timedelta(days=365*3)
            if 'descripcion' in edificio_fields:
                edificio_data['descripcion'] = 'Torre residencial moderna'
            if 'activo' in edificio_fields:
                edificio_data['activo'] = True
            
            edificio, created = Edificio.objects.get_or_create(
                nombre='Torre Aurora',
                defaults=edificio_data
            )
            print(f"✅ Edificio {'creado' if created else 'ya existe'}")
            
            # 4. Crear viviendas
            print("🏠 Creando viviendas...")
            from viviendas.models import Vivienda
            
            vivienda_fields = get_model_fields(Vivienda)
            print(f"📋 Campos Vivienda: {vivienda_fields}")
            
            for i in range(1, 6):
                numero = f"10{i:02d}"
                
                vivienda_data = {
                    'edificio': edificio,
                    'numero': numero,
                    'piso': 10
                }
                
                # Agregar campos opcionales basados en lo que existe
                if 'metros_cuadrados' in vivienda_fields:
                    vivienda_data['metros_cuadrados'] = 80
                if 'habitaciones' in vivienda_fields:
                    vivienda_data['habitaciones'] = 2
                if 'baños' in vivienda_fields:
                    vivienda_data['baños'] = 1
                elif 'banos' in vivienda_fields:
                    vivienda_data['banos'] = 1
                if 'estado' in vivienda_fields:
                    vivienda_data['estado'] = 'OCUPADO'
                if 'activo' in vivienda_fields:
                    vivienda_data['activo'] = True
                
                vivienda, created = Vivienda.objects.get_or_create(
                    edificio=edificio,
                    numero=numero,
                    defaults=vivienda_data
                )
                if created:
                    print(f"✅ Vivienda {numero} creada")
            
            # 5. Crear residentes
            print("👨‍👩‍👧‍👦 Creando residentes...")
            from viviendas.models import Residente
            
            residente_fields = get_model_fields(Residente)
            print(f"📋 Campos Residente: {residente_fields}")
            
            rol_residente = Rol.objects.get(nombre='Residente')
            viviendas = Vivienda.objects.filter(edificio=edificio)[:3]
            
            residentes_data = [
                {
                    'username': 'residente1',
                    'email': 'juan.perez@email.com',
                    'password': 'residente123',
                    'first_name': 'Juan',
                    'last_name': 'Pérez'
                },
                {
                    'username': 'residente2',
                    'email': 'maria.lopez@email.com',
                    'password': 'residente123',
                    'first_name': 'María',
                    'last_name': 'López'
                },
                {
                    'username': 'residente3',
                    'email': 'carlos.mamani@email.com',
                    'password': 'residente123',
                    'first_name': 'Carlos',
                    'last_name': 'Mamani'
                }
            ]
            
            for i, data in enumerate(residentes_data):
                if not Usuario.objects.filter(username=data['username']).exists():
                    user_data = data.copy()
                    
                    # Agregar campos opcionales de usuario
                    if 'telefono' in usuario_fields:
                        user_data['telefono'] = f'+591-7000001{i}'
                    
                    user = Usuario.objects.create_user(**user_data)
                    user.rol = rol_residente
                    user.save()
                    
                    # Crear residente con campos disponibles
                    if i < len(viviendas):
                        residente_data = {
                            'usuario': user,
                            'vivienda': viviendas[i]
                        }
                        
                        # Agregar campos opcionales de residente
                        if 'es_propietario' in residente_fields:
                            residente_data['es_propietario'] = True
                        if 'activo' in residente_fields:
                            residente_data['activo'] = True
                        if 'fecha_ingreso' in residente_fields:
                            residente_data['fecha_ingreso'] = timezone.now().date() - timedelta(days=30*i)
                        
                        residente, created = Residente.objects.get_or_create(
                            usuario=user,
                            defaults=residente_data
                        )
                        if created:
                            print(f"✅ Residente {user.first_name} creado")
            
            # 6. Intentar crear datos de personal si existe
            try:
                print("👷 Intentando crear datos de personal...")
                from personal.models import Puesto, Empleado
                
                puesto_fields = get_model_fields(Puesto)
                print(f"📋 Campos Puesto: {puesto_fields}")
                
                puesto_data = {'nombre': 'Portero'}
                if 'descripcion' in puesto_fields:
                    puesto_data['descripcion'] = 'Control de acceso'
                if 'requiere_especializacion' in puesto_fields:
                    puesto_data['requiere_especializacion'] = False
                
                puesto, created = Puesto.objects.get_or_create(
                    nombre='Portero',
                    defaults=puesto_data
                )
                
                # Crear empleado
                rol_empleado = Rol.objects.get(nombre='Empleado')
                if not Usuario.objects.filter(username='portero1').exists():
                    empleado_user = Usuario.objects.create_user(
                        username='portero1',
                        email='portero1@torresegura.com',
                        password='empleado123',
                        first_name='Miguel',
                        last_name='Quispe'
                    )
                    empleado_user.rol = rol_empleado
                    empleado_user.save()
                    
                    empleado_fields = get_model_fields(Empleado)
                    print(f"📋 Campos Empleado: {empleado_fields}")
                    
                    empleado_data = {
                        'usuario': empleado_user,
                        'puesto': puesto,
                        'fecha_contratacion': timezone.now().date() - timedelta(days=365)
                    }
                    
                    # Campos opcionales
                    if 'edificio' in empleado_fields:
                        empleado_data['edificio'] = edificio
                    if 'salario' in empleado_fields:
                        empleado_data['salario'] = Decimal('2500')
                    if 'tipo_contrato' in empleado_fields:
                        empleado_data['tipo_contrato'] = 'PERMANENTE'
                    if 'activo' in empleado_fields:
                        empleado_data['activo'] = True
                    
                    empleado, created = Empleado.objects.get_or_create(
                        usuario=empleado_user,
                        defaults=empleado_data
                    )
                    if created:
                        print("✅ Empleado portero creado")
                        
            except ImportError:
                print("⚠️ Módulo personal no disponible, saltando...")
            
            # 7. Intentar crear datos financieros básicos
            try:
                print("💰 Intentando crear datos financieros...")
                from financiero.models import ConceptoCuota, CategoriaGasto
                
                concepto_fields = get_model_fields(ConceptoCuota)
                print(f"📋 Campos ConceptoCuota: {concepto_fields}")
                
                concepto_data = {
                    'nombre': 'Administración Mensual',
                    'monto_base': Decimal('350')
                }
                
                if 'descripcion' in concepto_fields:
                    concepto_data['descripcion'] = 'Cuota mensual de administración'
                if 'periodicidad' in concepto_fields:
                    concepto_data['periodicidad'] = 'MENSUAL'
                if 'aplica_recargo' in concepto_fields:
                    concepto_data['aplica_recargo'] = True
                if 'porcentaje_recargo' in concepto_fields:
                    concepto_data['porcentaje_recargo'] = Decimal('2.5')
                
                concepto, created = ConceptoCuota.objects.get_or_create(
                    nombre='Administración Mensual',
                    defaults=concepto_data
                )
                if created:
                    print("✅ Concepto de cuota creado")
                
            except ImportError:
                print("⚠️ Módulo financiero no disponible, saltando...")
            
            print("✅ ¡Datos inteligentes creados exitosamente!")
            print("\n" + "="*60)
            print("📋 CREDENCIALES CREADAS:")
            print("="*60)
            print("\n🔑 ADMINISTRADOR:")
            print("Usuario: admin | Password: admin123")
            print("\n👨‍👩‍👧‍👦 RESIDENTES:")
            print("Usuario: residente1 | Password: residente123 (Juan Pérez)")
            print("Usuario: residente2 | Password: residente123 (María López)")
            print("Usuario: residente3 | Password: residente123 (Carlos Mamani)")
            print("\n👷 EMPLEADO:")
            print("Usuario: portero1 | Password: empleado123 (Miguel Quispe)")
            print("\n🏢 EDIFICIOS CREADOS:")
            print("- Torre Aurora (15 pisos, 5 viviendas de prueba)")
            print("\n🚀 ¡Sistema listo para pruebas básicas!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print("Detalles:")
        print(traceback.format_exc())

if __name__ == "__main__":
    crear_datos_inteligentes()