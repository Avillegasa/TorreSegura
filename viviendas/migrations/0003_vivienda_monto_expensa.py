from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viviendas', '0002_alter_edificio_options_alter_residente_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vivienda',
            name='monto_expensa',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Monto mensual de expensa asignado a esta vivienda',
                max_digits=10,
                null=True,
            ),
        ),
    ]
