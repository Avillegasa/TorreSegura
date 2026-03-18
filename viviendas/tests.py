from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from usuarios.models import Rol
from .models import Edificio, Vivienda, Residente

class EdificioModelTest(TestCase):
    """
    Pruebas para el modelo Edificio
    """
    
    def setUp(self):
        self.edificio = Edificio.objects.create(
            nombre='Torre Norte',
            direccion='Av. Principal 123',
            pisos=15,
            cantidad_viviendas=30,
            fecha_construccion='2010-05-20'
        )
    
    def test_edificio_creation(self):
        """Verificar la creación correcta de un edificio"""
        self.assertEqual(self.edificio.nombre, 'Torre Norte')
        self.assertEqual(self.edificio.direccion, 'Av. Principal 123')
        self.assertEqual(self.edificio.pisos, 15)
        self.assertEqual(str(self.edificio.fecha_construccion), '2010-05-20')
    
    def test_edificio_str(self):
        """Verificar que el método __str__ funciona correctamente"""
        self.assertEqual(str(self.edificio), 'Torre Norte')

class ViviendaModelTest(TestCase):
    """
    Pruebas para el modelo Vivienda
    """
    
    def setUp(self):
        # Crear edificio
        self.edificio = Edificio.objects.create(
            nombre='Torre Sur',
            direccion='Av. Secundaria 456',
            pisos=10,
            cantidad_viviendas=2,
            fecha_construccion='2015-08-10'
        )
        
        # Crear vivienda
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='501',
            piso=5,
            metros_cuadrados=120,
            habitaciones=3,
            baños=2,
            estado='OCUPADO',
            activo=True
        )
        
        # Crear vivienda dada de baja
        self.vivienda_baja = Vivienda.objects.create(
            edificio=self.edificio,
            numero='502',
            piso=5,
            metros_cuadrados=100,
            habitaciones=2,
            baños=1,
            estado='DESOCUPADO',
            activo=False,
            fecha_baja=timezone.now().date(),
            motivo_baja='Remodelación completa'
        )

    def test_no_permite_rebasar_limite_viviendas_del_edificio(self):
        """No debe permitir registrar más viviendas que el límite del edificio"""
        with self.assertRaises(ValidationError):
            Vivienda.objects.create(
                edificio=self.edificio,
                numero='503',
                piso=5,
                metros_cuadrados=80,
                habitaciones=1,
                baños=1,
                estado='DESOCUPADO',
                activo=True,
            )
    
    def test_vivienda_creation(self):
        """Verificar la creación correcta de una vivienda"""
        self.assertEqual(self.vivienda.edificio, self.edificio)
        self.assertEqual(self.vivienda.numero, '501')
        self.assertEqual(self.vivienda.piso, 5)
        self.assertEqual(self.vivienda.metros_cuadrados, 120)
        self.assertEqual(self.vivienda.habitaciones, 3)
        self.assertEqual(self.vivienda.baños, 2)
        self.assertEqual(self.vivienda.estado, 'OCUPADO')
        self.assertTrue(self.vivienda.activo)
    
    def test_vivienda_baja_creation(self):
        """Verificar la creación correcta de una vivienda dada de baja"""
        self.assertEqual(self.vivienda_baja.edificio, self.edificio)
        self.assertEqual(self.vivienda_baja.numero, '502')
        self.assertEqual(self.vivienda_baja.estado, 'BAJA')  # El estado debería cambiarse a BAJA automáticamente
        self.assertFalse(self.vivienda_baja.activo)
        self.assertIsNotNone(self.vivienda_baja.fecha_baja)
        self.assertEqual(self.vivienda_baja.motivo_baja, 'Remodelación completa')
    
    def test_vivienda_str(self):
        """Verificar que el método __str__ funciona correctamente"""
        expected_str = f"Vivienda 501 - Piso 5"
        self.assertEqual(str(self.vivienda), expected_str)
    
    def test_save_method_cambia_estado_baja(self):
        """Verificar que al dar de baja una vivienda, su estado cambia a BAJA"""
        self.vivienda.activo = False
        self.vivienda.motivo_baja = 'Demolición'
        self.vivienda.fecha_baja = timezone.now().date()
        self.vivienda.save()
        
        self.assertEqual(self.vivienda.estado, 'BAJA')

class ResidenteModelTest(TestCase):
    """
    Pruebas para el modelo Residente
    """
    
    def setUp(self):
        # Crear edificio y vivienda
        self.edificio = Edificio.objects.create(
            nombre='Torre Este',
            direccion='Calle Este 789',
            pisos=8,
            cantidad_viviendas=10,
            fecha_construccion='2018-03-15'
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='301',
            piso=3,
            metros_cuadrados=90,
            habitaciones=2,
            baños=1,
            estado='OCUPADO',
            activo=True
        )
        
        # Crear usuario
        User = get_user_model()
        self.usuario = User.objects.create_user(
            username='residente',
            email='residente@example.com',
            password='password',
            first_name='Ana',
            last_name='Martínez'
        )
        
        # Crear residente
        self.residente = Residente.objects.create(
            usuario=self.usuario,
            vivienda=self.vivienda,
            vehiculos=1,
            es_propietario=True,
            activo=True
        )
    
    def test_residente_creation(self):
        """Verificar la creación correcta de un residente"""
        self.assertEqual(self.residente.usuario, self.usuario)
        self.assertEqual(self.residente.vivienda, self.vivienda)
        self.assertEqual(self.residente.vehiculos, 1)
        self.assertTrue(self.residente.es_propietario)
        self.assertTrue(self.residente.activo)
    
    def test_residente_str(self):
        """Verificar que el método __str__ funciona correctamente"""
        expected_str = f"Ana Martínez - Vivienda 301"
        self.assertEqual(str(self.residente), expected_str)
    
    def test_sincronizacion_estado_usuario(self):
        """Verificar que el estado del residente se sincroniza con el usuario"""
        # Desactivar usuario
        self.usuario.is_active = False
        self.usuario.save()
        
        # Verificar que el residente también se desactiva
        self.residente.refresh_from_db()
        self.assertFalse(self.residente.activo)
        
        # Activar usuario
        self.usuario.is_active = True
        self.usuario.save()
        
        # Verificar que el residente también se activa
        self.residente.refresh_from_db()
        self.assertTrue(self.residente.activo)

class EdificioViewsTest(TestCase):
    """
    Pruebas para las vistas relacionadas con Edificios
    """
    
    def setUp(self):
        # Crear usuario administrador
        self.rol_admin = Rol.objects.create(nombre='Administrador', descripcion='Administrador del sistema')
        
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        # Crear usuario normal
        self.rol_normal = Rol.objects.create(nombre='Normal', descripcion='Usuario normal')
        self.normal_user = User.objects.create_user(
            username='normal',
            email='normal@example.com',
            password='normalpassword',
            rol=self.rol_normal
        )
        
        # Crear edificio
        self.edificio = Edificio.objects.create(
            nombre='Torre Oeste',
            direccion='Calle Oeste 321',
            pisos=12,
            cantidad_viviendas=24,
            fecha_construccion='2016-11-20'
        )
        
        # Iniciar cliente
        self.client = Client()
    
    def test_edificio_list_view(self):
        """Verificar que se puede ver la lista de edificios"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('edificio-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/edificio_list.html')
        self.assertContains(response, 'Torre Oeste')
    
    def test_edificio_create_view_admin(self):
        """Verificar que un administrador puede crear un edificio"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('edificio-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/edificio_form.html')
        
        # Probar POST
        data = {
            'nombre': 'Torre Nueva',
            'direccion': 'Calle Nueva 123',
            'pisos': 20,
            'cantidad_viviendas': 40,
            'fecha_construccion': '2022-01-15'
        }
        
        response = self.client.post(reverse('edificio-create'), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se creó el edificio
        self.assertTrue(Edificio.objects.filter(nombre='Torre Nueva').exists())
    
    def test_edificio_create_view_normal_user(self):
        """Verificar que un usuario normal no puede crear un edificio"""
        self.client.login(username='normal', password='normalpassword')
        response = self.client.get(reverse('edificio-create'))
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_edificio_update_view_admin(self):
        """Verificar que un administrador puede actualizar un edificio"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('edificio-update', args=[self.edificio.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/edificio_form.html')
        
        # Probar POST
        data = {
            'nombre': 'Torre Oeste Actualizada',
            'direccion': 'Calle Oeste 321',
            'pisos': 15,
            'cantidad_viviendas': 24,
            'fecha_construccion': '2016-11-20'
        }
        
        response = self.client.post(reverse('edificio-update', args=[self.edificio.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se actualizó el edificio
        self.edificio.refresh_from_db()
        self.assertEqual(self.edificio.nombre, 'Torre Oeste Actualizada')
        self.assertEqual(self.edificio.pisos, 15)

class ViviendaViewsTest(TestCase):
    """
    Pruebas para las vistas relacionadas con Viviendas
    """
    
    def setUp(self):
        # Crear usuario administrador
        self.rol_admin = Rol.objects.create(nombre='Administrador', descripcion='Administrador del sistema')
        
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        # Crear edificio
        self.edificio = Edificio.objects.create(
            nombre='Torre Central',
            direccion='Av. Central 789',
            pisos=20,
            cantidad_viviendas=100,
            fecha_construccion='2019-05-10'
        )
        
        # Crear vivienda
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='1001',
            piso=10,
            metros_cuadrados=150,
            habitaciones=3,
            baños=2,
            estado='OCUPADO',
            activo=True
        )
        
        # Iniciar cliente
        self.client = Client()
        self.client.login(username='admin', password='adminpassword')
    
    def test_vivienda_list_view(self):
        """Verificar que se puede ver la lista de viviendas"""
        response = self.client.get(reverse('vivienda-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/vivienda_list.html')
        self.assertContains(response, '1001')
    
    def test_vivienda_detail_view(self):
        """Verificar que se puede ver el detalle de una vivienda"""
        response = self.client.get(reverse('vivienda-detail', args=[self.vivienda.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/vivienda_detail.html')
        self.assertContains(response, 'Vivienda 1001')
        self.assertContains(response, 'Piso 10')
    
    def test_vivienda_create_view(self):
        """Verificar que se puede crear una vivienda"""
        response = self.client.get(reverse('vivienda-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/vivienda_form.html')
        
        # Probar POST
        data = {
            'edificio': self.edificio.id,
            'numero': '2001',
            'piso': 20,
            'metros_cuadrados': 200,
            'habitaciones': 4,
            'baños': 3,
            'estado': 'DESOCUPADO',
            'activo': True
        }
        
        response = self.client.post(reverse('vivienda-create'), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se creó la vivienda
        self.assertTrue(Vivienda.objects.filter(numero='2001').exists())
    
    def test_vivienda_baja_view(self):
        """Verificar que se puede dar de baja una vivienda"""
        response = self.client.get(reverse('vivienda-baja', args=[self.vivienda.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/vivienda_baja.html')
        
        # Probar POST
        data = {
            'motivo_baja': 'Remodelación completa',
            'fecha_baja': timezone.now().date().strftime('%Y-%m-%d')
        }
        
        response = self.client.post(reverse('vivienda-baja', args=[self.vivienda.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se dio de baja la vivienda
        self.vivienda.refresh_from_db()
        self.assertFalse(self.vivienda.activo)
        self.assertEqual(self.vivienda.estado, 'BAJA')
        self.assertEqual(self.vivienda.motivo_baja, 'Remodelación completa')
        self.assertIsNotNone(self.vivienda.fecha_baja)

class ResidenteViewsTest(TestCase):
    """
    Pruebas para las vistas relacionadas con Residentes
    """
    
    def setUp(self):
        # Crear usuario administrador
        self.rol_admin = Rol.objects.create(nombre='Administrador', descripcion='Administrador del sistema')
        
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        # Crear edificio y vivienda
        self.edificio = Edificio.objects.create(
            nombre='Torre Residencial',
            direccion='Av. Residencial 456',
            pisos=15,
            cantidad_viviendas=50,
            fecha_construccion='2020-02-10'
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='701',
            piso=7,
            metros_cuadrados=110,
            habitaciones=2,
            baños=2,
            estado='OCUPADO',
            activo=True
        )
        
        # Crear usuario para residente
        self.usuario_residente = User.objects.create_user(
            username='residente',
            email='residente@example.com',
            password='password',
            first_name='Laura',
            last_name='Gómez',
            numero_documento='1234567',
            telefono='77777777'
        )
        
        # Crear residente
        self.residente = Residente.objects.create(
            usuario=self.usuario_residente,
            vivienda=self.vivienda,
            vehiculos=2,
            es_propietario=True,
            activo=True
        )
        
        # Iniciar cliente
        self.client = Client()
        self.client.login(username='admin', password='adminpassword')
    
    def test_residente_list_view(self):
        """Verificar que se puede ver la lista de residentes"""
        response = self.client.get(reverse('residente-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/residente_list.html')
        self.assertContains(response, 'Laura Gómez')
    
    def test_residente_detail_view(self):
        """Verificar que se puede ver el detalle de un residente"""
        response = self.client.get(reverse('residente-detail', args=[self.residente.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'viviendas/residente_detail.html')
        self.assertContains(response, 'Laura Gómez')
        self.assertContains(response, 'Torre Residencial')
    
    def test_residente_create_view(self):
        """Verificar que se puede crear un residente"""
        data = {
            # Campos del usuario (requeridos por ResidenteCreationForm)
            'username': 'nuevoresidente',
            'email': 'nuevoresidente@example.com',
            'first_name': 'Carlos',
            'last_name': 'López',
            'telefono': '70000000',
            'numero_documento': '7654321',
            'password1': 'Password123!@#',
            'password2': 'Password123!@#',

            # Campos auxiliares del formulario
            'edificio': self.edificio.id,
            'vivienda': self.vivienda.id,

            # Campos del modelo Residente
            'vehiculos': 1,
            'es_propietario': False,
            'activo': True
        }
        
        response = self.client.post(reverse('residente-create'), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se creó el residente
        self.assertTrue(Residente.objects.filter(usuario__username='nuevoresidente').exists())

    def test_residente_update_view(self):
        """Verificar que se puede actualizar un residente"""
        data = {
            # Campos del usuario (requeridos por ResidenteCreationForm en edición)
            'username': self.usuario_residente.username,
            'email': self.usuario_residente.email,
            'first_name': self.usuario_residente.first_name,
            'last_name': self.usuario_residente.last_name,
            'telefono': self.usuario_residente.telefono,
            'numero_documento': self.usuario_residente.numero_documento,
            # Contraseñas opcionales en edición
            'password1': '',
            'password2': '',

            # Campos auxiliares del formulario
            'edificio': self.edificio.id,
            'vivienda': self.vivienda.id,

            # Campos del modelo Residente
            'vehiculos': 3,  # Actualizar número de vehículos
            'es_propietario': True,
            'activo': True
        }
        
        response = self.client.post(reverse('residente-update', args=[self.residente.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirección
        
        # Verificar que se actualizó el residente
        self.residente.refresh_from_db()
        self.assertEqual(self.residente.vehiculos, 3)