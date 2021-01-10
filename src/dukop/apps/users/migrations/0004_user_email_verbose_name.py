# Generated by Django 2.2.17 on 2021-01-10 18:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_group_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(help_text='Your email address will be used for password resets and notification about your event/submissions.', max_length=254, unique=True, verbose_name='email'),
        ),
    ]
