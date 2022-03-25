# Generated by Django 3.2 on 2022-03-25 20:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_grouplink'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='grouplink',
            options={'ordering': ('priority',)},
        ),
        migrations.RemoveField(
            model_name='group',
            name='link1',
        ),
        migrations.RemoveField(
            model_name='group',
            name='link2',
        ),
        migrations.RemoveField(
            model_name='group',
            name='link3',
        ),
        migrations.AlterField(
            model_name='grouplink',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='users.group'),
        ),
    ]
