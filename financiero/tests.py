from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from usuarios.models import Rol
from viviendas.models import Edificio, Vivienda, Residente
from .models import ConceptoCuota, Cuota, Pago, PagoCuota, CategoriaGasto, Gasto, EstadoCuenta

class ConceptoCuotaModelTest(TestCase):
    """
    Pruebas para el modelo ConceptoCuota
    """
    
    def setUp(self):
        self.concepto = ConceptoCuota.objects.create(
            nombre='Cuota de Mantenimiento',
            descripcion='Cuota mensual para mantenimiento del condominio',
            monto_base=Decimal('100.00'),
            periodicidad='MENSUAL',
            aplica_recargo=True,
            porcentaje_recargo=Decimal('2.00'),
            activo=True
        )
    
    def test_concepto_creation(self):
        """Verificar la creación correcta de un concepto de cuota"""
        self.assertEqual(self.concepto.nombre, 'Cuota de Mantenimiento')
        self.assertEqual(self.concepto.descripcion, 'Cuota mensual para mantenimiento del condominio')
        self.assertEqual(self.concepto.monto_base, Decimal('100.00'))
        self.assertEqual(self.concepto.periodicidad, 'MENSUAL')
        self.assertTrue(self.concepto.aplica_recargo)
        self.assertEqual(self.concepto.porcentaje_recargo, Decimal('2.00'))
        self.assertTrue(self.concepto.activo)
    
    def test_concepto_str(self):
        """Verificar que el método __str__ funciona correctamente"""
        expected_str = 'Cuota de Mantenimiento - Mensual'
        self.assertEqual(str(self.concepto), expected_str)

class CuotaModelTest(TestCase):
    """
    Pruebas para el modelo Cuota
    """
    
    def setUp(self):
        # Crear conceptos, edificios y viviendas necesarios para las pruebas
        self.concepto = ConceptoCuota.objects.create(
            nombre='Cuota de Mantenimiento',
            monto_base=Decimal('100.00'),
            periodicidad='MENSUAL',
            aplica_recargo=True,
            porcentaje_recargo=Decimal('2.00')
        )
        
        self.edificio = Edificio.objects.create(
            nombre='Edificio Test',
            direccion='Calle Test 123',
            pisos=10
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='101',
            piso=1,
            metros_cuadrados=80,
            habitaciones=2,
            baños=1
        )
        
        # Crear una cuota
        self.fecha_emision = timezone.now().date()
        self.fecha_vencimiento = self.fecha_emision + timedelta(days=30)
        
        self.cuota = Cuota.objects.create(
            concepto=self.concepto,
            vivienda=self.vivienda,
            monto=Decimal('100.00'),
            fecha_emision=self.fecha_emision,
            fecha_vencimiento=self.fecha_vencimiento,
            pagada=False,
            recargo=Decimal('0.00'),
            notas='Cuota de prueba'
        )
    
    def test_cuota_creation(self):
        """Verificar la creación correcta de una cuota"""
        self.assertEqual(self.cuota.concepto, self.concepto)
        self.assertEqual(self.cuota.vivienda, self.vivienda)
        self.assertEqual(self.cuota.monto, Decimal('100.00'))
        self.assertEqual(self.cuota.fecha_emision, self.fecha_emision)
        self.assertEqual(self.cuota.fecha_vencimiento, self.fecha_vencimiento)
        self.assertFalse(self.cuota.pagada)
        self.assertEqual(self.cuota.recargo, Decimal('0.00'))
        self.assertEqual(self.cuota.notas, 'Cuota de prueba')
    
    def test_total_a_pagar(self):
        """Verificar que el método total_a_pagar funciona correctamente"""
        # Sin recargos
        self.assertEqual(self.cuota.total_a_pagar(), Decimal('100.00'))

        # Con recargos: usar update_fields para evitar que el pre_save signal
        # recalcule el recargo (la cuota no está vencida en el test)
        Cuota.objects.filter(pk=self.cuota.pk).update(recargo=Decimal('10.00'))
        self.cuota.refresh_from_db()
        self.assertEqual(self.cuota.total_a_pagar(), Decimal('110.00'))
    
    def test_marcar_como_pagada(self):
        """Verificar que el método marcar_como_pagada funciona correctamente"""
        # Añadir un recargo
        self.cuota.recargo = Decimal('10.00')
        self.cuota.save()
        
        # Marcar como pagada
        self.cuota.marcar_como_pagada()
        
        # Verificar cambios
        self.assertTrue(self.cuota.pagada)
        self.assertEqual(self.cuota.recargo, Decimal('0.00'))
    
    def test_fecha_vencimiento_validation(self):
        """Verificar que la validación de fecha_vencimiento funciona correctamente"""
        # Intentar crear una cuota con fecha de vencimiento anterior a la de emisión
        with self.assertRaises(Exception):
            Cuota.objects.create(
                concepto=self.concepto,
                vivienda=self.vivienda,
                monto=Decimal('100.00'),
                fecha_emision=self.fecha_emision,
                fecha_vencimiento=self.fecha_emision - timedelta(days=1)
            )

class PagoModelTest(TestCase):
    """
    Pruebas para el modelo Pago
    """
    
    def setUp(self):
        # Crear rol, usuario, edificio, vivienda y residente
        self.rol_admin = Rol.objects.create(nombre='Administrador', descripcion='Administrador del sistema')
        
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        self.edificio = Edificio.objects.create(
            nombre='Edificio Test',
            direccion='Calle Test 123',
            pisos=10
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='101',
            piso=1,
            metros_cuadrados=80,
            habitaciones=2,
            baños=1
        )
        
        self.usuario_residente = User.objects.create_user(
            username='residente',
            email='residente@example.com',
            password='password',
            first_name='Juan',
            last_name='Pérez'
        )
        
        self.residente = Residente.objects.create(
            usuario=self.usuario_residente,
            vivienda=self.vivienda,
            es_propietario=True
        )
        
        # Crear pago
        self.pago = Pago.objects.create(
            vivienda=self.vivienda,
            residente=self.residente,
            monto=Decimal('200.00'),
            fecha_pago=timezone.now().date(),
            metodo_pago='TRANSFERENCIA',
            referencia='REF123456',
            estado='PENDIENTE',
            registrado_por=self.admin_user,
            notas='Pago de prueba'
        )
    
    def test_pago_creation(self):
        """Verificar la creación correcta de un pago"""
        self.assertEqual(self.pago.vivienda, self.vivienda)
        self.assertEqual(self.pago.residente, self.residente)
        self.assertEqual(self.pago.monto, Decimal('200.00'))
        self.assertEqual(self.pago.metodo_pago, 'TRANSFERENCIA')
        self.assertEqual(self.pago.referencia, 'REF123456')
        self.assertEqual(self.pago.estado, 'PENDIENTE')
        self.assertEqual(self.pago.registrado_por, self.admin_user)
        self.assertEqual(self.pago.notas, 'Pago de prueba')
    
    def test_verificar_pago(self):
        """Verificar que el método verificar_pago funciona correctamente"""
        self.pago.verificar_pago(self.admin_user)
        
        self.assertEqual(self.pago.estado, 'VERIFICADO')
        self.assertEqual(self.pago.verificado_por, self.admin_user)
        self.assertIsNotNone(self.pago.fecha_verificacion)
    
    def test_rechazar_pago(self):
        """Verificar que el método rechazar_pago funciona correctamente"""
        motivo = "Comprobante no válido"
        self.pago.rechazar_pago(self.admin_user, motivo)
        
        self.assertEqual(self.pago.estado, 'RECHAZADO')
        self.assertEqual(self.pago.verificado_por, self.admin_user)
        self.assertIsNotNone(self.pago.fecha_verificacion)
        self.assertIn(motivo, self.pago.notas)

class PagoCuotaModelTest(TestCase):
    """
    Pruebas para el modelo PagoCuota
    """
    
    def setUp(self):
        # Configuración básica para las pruebas
        
        # Crear concepto
        self.concepto = ConceptoCuota.objects.create(
            nombre='Cuota de Mantenimiento',
            monto_base=Decimal('100.00'),
            periodicidad='MENSUAL'
        )
        
        # Crear edificio y vivienda
        self.edificio = Edificio.objects.create(
            nombre='Edificio Test',
            direccion='Calle Test 123',
            pisos=10
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='101',
            piso=1,
            metros_cuadrados=80,
            habitaciones=2,
            baños=1
        )
        
        # Crear usuario residente
        User = get_user_model()
        self.usuario_residente = User.objects.create_user(
            username='residente',
            email='residente@example.com',
            password='password',
            first_name='Juan',
            last_name='Pérez'
        )
        
        self.residente = Residente.objects.create(
            usuario=self.usuario_residente,
            vivienda=self.vivienda,
            es_propietario=True
        )
        
        # Crear usuario administrador
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        # Crear cuota
        self.cuota = Cuota.objects.create(
            concepto=self.concepto,
            vivienda=self.vivienda,
            monto=Decimal('100.00'),
            fecha_emision=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30)
        )
        
        # Crear pago
        self.pago = Pago.objects.create(
            vivienda=self.vivienda,
            residente=self.residente,
            monto=Decimal('100.00'),
            fecha_pago=timezone.now().date(),
            metodo_pago='EFECTIVO',
            registrado_por=self.admin_user
        )
        
        # Crear relación PagoCuota
        self.pago_cuota = PagoCuota.objects.create(
            pago=self.pago,
            cuota=self.cuota,
            monto_aplicado=Decimal('100.00')
        )
    
    def test_pagocuota_creation(self):
        """Verificar la creación correcta de una relación PagoCuota"""
        self.assertEqual(self.pago_cuota.pago, self.pago)
        self.assertEqual(self.pago_cuota.cuota, self.cuota)
        self.assertEqual(self.pago_cuota.monto_aplicado, Decimal('100.00'))
    
    def test_pagocuota_validation(self):
        """Verificar que la validación de monto_aplicado funciona correctamente"""
        # Intentar crear una relación PagoCuota con monto mayor al total de la cuota
        with self.assertRaises(Exception):
            PagoCuota.objects.create(
                pago=self.pago,
                cuota=self.cuota,
                monto_aplicado=Decimal('200.00')  # Mayor que el monto de la cuota
            )

class CategoriaGastoModelTest(TestCase):
    """
    Pruebas para el modelo CategoriaGasto
    """
    
    def setUp(self):
        self.categoria = CategoriaGasto.objects.create(
            nombre='Mantenimiento',
            descripcion='Gastos relacionados con mantenimiento',
            presupuesto_mensual=Decimal('1000.00'),
            color='#3498db',
            activo=True
        )
    
    def test_categoria_creation(self):
        """Verificar la creación correcta de una categoría de gasto"""
        self.assertEqual(self.categoria.nombre, 'Mantenimiento')
        self.assertEqual(self.categoria.descripcion, 'Gastos relacionados con mantenimiento')
        self.assertEqual(self.categoria.presupuesto_mensual, Decimal('1000.00'))
        self.assertEqual(self.categoria.color, '#3498db')
        self.assertTrue(self.categoria.activo)
    
    def test_categoria_str(self):
        """Verificar que el método __str__ funciona correctamente"""
        self.assertEqual(str(self.categoria), 'Mantenimiento')

class GastoModelTest(TestCase):
    """
    Pruebas para el modelo Gasto
    """
    
    def setUp(self):
        # Crear categoria de gasto
        self.categoria = CategoriaGasto.objects.create(
            nombre='Mantenimiento',
            presupuesto_mensual=Decimal('1000.00')
        )
        
        # Crear usuario administrador
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword',
            rol=self.rol_admin
        )
        
        # Crear gasto
        self.gasto = Gasto.objects.create(
            categoria=self.categoria,
            concepto='Reparación de bomba de agua',
            descripcion='Reparación de la bomba principal del edificio',
            monto=Decimal('350.00'),
            fecha=timezone.now().date(),
            proveedor='Servicios Hidráulicos S.A.',
            factura='FAC-12345',
            estado='PENDIENTE',
            tipo_gasto='MANTENIMIENTO',
            registrado_por=self.admin_user,
            presupuestado=True,
            recurrente=False,
            notas='Gasto de prueba'
        )
    
    def test_gasto_creation(self):
        """Verificar la creación correcta de un gasto"""
        self.assertEqual(self.gasto.categoria, self.categoria)
        self.assertEqual(self.gasto.concepto, 'Reparación de bomba de agua')
        self.assertEqual(self.gasto.descripcion, 'Reparación de la bomba principal del edificio')
        self.assertEqual(self.gasto.monto, Decimal('350.00'))
        self.assertEqual(self.gasto.proveedor, 'Servicios Hidráulicos S.A.')
        self.assertEqual(self.gasto.factura, 'FAC-12345')
        self.assertEqual(self.gasto.estado, 'PENDIENTE')
        self.assertEqual(self.gasto.tipo_gasto, 'MANTENIMIENTO')
        self.assertEqual(self.gasto.registrado_por, self.admin_user)
        self.assertTrue(self.gasto.presupuestado)
        self.assertFalse(self.gasto.recurrente)
        self.assertEqual(self.gasto.notas, 'Gasto de prueba')
    
    def test_marcar_como_pagado(self):
        """Verificar que el método marcar_como_pagado funciona correctamente"""
        fecha_pago = timezone.now().date()
        self.gasto.marcar_como_pagado(fecha_pago)
        
        self.assertEqual(self.gasto.estado, 'PAGADO')
        self.assertEqual(self.gasto.fecha_pago, fecha_pago)
    
    def test_cancelar(self):
        """Verificar que el método cancelar funciona correctamente"""
        self.gasto.cancelar()
        
        self.assertEqual(self.gasto.estado, 'CANCELADO')

class EstadoCuentaModelTest(TestCase):
    """
    Pruebas para el modelo EstadoCuenta
    """
    
    def setUp(self):
        # Crear edificio y vivienda
        self.edificio = Edificio.objects.create(
            nombre='Edificio Test',
            direccion='Calle Test 123',
            pisos=10
        )
        
        self.vivienda = Vivienda.objects.create(
            edificio=self.edificio,
            numero='101',
            piso=1,
            metros_cuadrados=80,
            habitaciones=2,
            baños=1
        )
        
        # Crear estado de cuenta
        self.fecha_inicio = date(2024, 1, 1)
        self.fecha_fin = date(2024, 1, 31)
        
        self.estado_cuenta = EstadoCuenta.objects.create(
            vivienda=self.vivienda,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            saldo_anterior=Decimal('100.00')
        )
    
    def test_estado_cuenta_creation(self):
        """Verificar la creación correcta de un estado de cuenta"""
        self.assertEqual(self.estado_cuenta.vivienda, self.vivienda)
        self.assertEqual(self.estado_cuenta.fecha_inicio, self.fecha_inicio)
        self.assertEqual(self.estado_cuenta.fecha_fin, self.fecha_fin)
        self.assertEqual(self.estado_cuenta.saldo_anterior, Decimal('100.00'))
        self.assertEqual(self.estado_cuenta.total_cuotas, Decimal('0.00'))
        self.assertEqual(self.estado_cuenta.total_pagos, Decimal('0.00'))
        self.assertEqual(self.estado_cuenta.total_recargos, Decimal('0.00'))
        self.assertEqual(self.estado_cuenta.saldo_final, Decimal('100.00'))  # Saldo anterior + totales
        self.assertFalse(self.estado_cuenta.enviado)
        self.assertIsNone(self.estado_cuenta.fecha_envio)
    
    def test_calcular_totales(self):
        """Verificar que el método calcular_totales funciona correctamente"""
        # Crear concepto
        concepto = ConceptoCuota.objects.create(
            nombre='Cuota de Mantenimiento',
            monto_base=Decimal('100.00')
        )
        
        # Crear usuario
        User = get_user_model()
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Crear cuotas en el período
        cuota1 = Cuota.objects.create(
            concepto=concepto,
            vivienda=self.vivienda,
            monto=Decimal('100.00'),
            fecha_emision=self.fecha_inicio,
            fecha_vencimiento=self.fecha_inicio + timedelta(days=15)
        )
        
        cuota2 = Cuota.objects.create(
            concepto=concepto,
            vivienda=self.vivienda,
            monto=Decimal('50.00'),
            fecha_emision=self.fecha_inicio + timedelta(days=10),
            fecha_vencimiento=self.fecha_fin,
            recargo=Decimal('5.00')
        )
        
        # Crear usuario residente
        usuario_residente = User.objects.create_user(
            username='residente',
            email='residente@example.com',
            password='password'
        )
        
        residente = Residente.objects.create(
            usuario=usuario_residente,
            vivienda=self.vivienda
        )
        
        # Crear pago en el período
        pago = Pago.objects.create(
            vivienda=self.vivienda,
            residente=residente,
            monto=Decimal('80.00'),
            fecha_pago=self.fecha_inicio + timedelta(days=5),
            metodo_pago='EFECTIVO',
            estado='VERIFICADO',
            registrado_por=admin_user
        )
        
        # Calcular totales
        self.estado_cuenta.calcular_totales()
        
        # Verificar que los totales se calcularon correctamente
        self.assertEqual(self.estado_cuenta.total_cuotas, Decimal('150.00'))  # 100 + 50
        self.assertEqual(self.estado_cuenta.total_pagos, Decimal('80.00'))
        self.assertEqual(self.estado_cuenta.total_recargos, Decimal('5.00'))
        
        # Saldo final = 100 (anterior) + 150 (cuotas) + 5 (recargos) - 80 (pagos) = 175
        self.assertEqual(self.estado_cuenta.saldo_final, Decimal('175.00'))
    
    def test_marcar_como_enviado(self):
        """Verificar que el método marcar_como_enviado funciona correctamente"""
        self.estado_cuenta.marcar_como_enviado()
        
        self.assertTrue(self.estado_cuenta.enviado)
        self.assertIsNotNone(self.estado_cuenta.fecha_envio)
    
    def test_fecha_fin_validation(self):
        """Verificar que la validación de fecha_fin funciona correctamente"""
        # Intentar crear un estado de cuenta con fecha_fin anterior a fecha_inicio
        with self.assertRaises(Exception):
            EstadoCuenta.objects.create(
                vivienda=self.vivienda,
                fecha_inicio=self.fecha_inicio,
                fecha_fin=self.fecha_inicio - timedelta(days=1)
            )