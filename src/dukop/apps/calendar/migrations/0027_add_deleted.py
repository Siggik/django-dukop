# Generated by Django 3.2 on 2022-03-15 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0026_alter_sphere_sub_spheres'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='event',
            name='deleted_on',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]