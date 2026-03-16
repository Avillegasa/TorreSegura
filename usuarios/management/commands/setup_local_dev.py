# usuarios/management/commands/setup_local_dev.py
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings
from django.contrib.auth import get_user_model
from usuarios.models import Rol

User = get_user_model()

class Command(BaseCommand):
    help = 'Configura el entorno de desarrollo local completo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Crear un superusuario para desarrollo',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Configurando entorno de desarrollo local...')
        
        # 1. Configurar Site
        try:
            site = Site.objects.get(pk=getattr(settings, 'SITE_ID', 1))
            site.domain = '127.0.0.1:8000'
            site.name = 'Desarrollo Local - TorreSegura'
            site.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Site actualizado: {site.domain}')
            )
        except Site.DoesNotExist:
            site = Site.objects.create(
                pk=getattr(settings, 'SITE_ID', 1),
                domain='127.0.0.1:8000',
                name='Desarrollo Local - TorreSegura'
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Site creado: {site.domain}')
            )
        
        # 2. Verificar roles
        try:
            roles_count = Rol.objects.count()
            if roles_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Roles encontrados: {roles_count}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️ No se encontraron roles. Ejecuta las migraciones primero.')
                )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Error verificando roles: {e}')
            )
        
        # 3. Crear superusuario si se solicita
        if options['create_superuser']:
            try:
                if not User.objects.filter(is_superuser=True).exists():
                    admin_user = User.objects.create_superuser(
                        username='admin',
                        email='admin@localhost.com',
                        password='admin123',
                        first_name='Admin',
                        last_name='Desarrollo'
                    )
                    self.stdout.write(
                        self.style.SUCCESS('✅ Superusuario creado:')
                    )
                    self.stdout.write(f'   Usuario: admin')
                    self.stdout.write(f'   Contraseña: admin123')
                    self.stdout.write(f'   Email: admin@localhost.com')
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️ Ya existe un superusuario')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creando superusuario: {e}')
                )
        
        self.stdout.write('\n🎉 Configuración completada!')
        self.stdout.write('💡 Comandos útiles para desarrollo:')
        self.stdout.write('   python manage.py runserver')
        self.stdout.write('   python manage.py shell')
        self.stdout.write('   python manage.py makemigrations')
        self.stdout.write('   python manage.py migrate')