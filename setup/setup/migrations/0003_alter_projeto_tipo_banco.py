# Generated by Django 5.2 on 2025-04-29 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setup', '0002_projeto_delete_produto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projeto',
            name='tipo_banco',
            field=models.CharField(choices=[('postgresql', 'PostgreSQL'), ('sqlite3', 'SQLite3')], default='PostgreSQL', max_length=50),
        ),
    ]
