# Generated by Django 3.2 on 2021-08-01 09:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0018_intervals_refactor'),
    ]

    operations = [
        migrations.RenameModel('EventInterval', 'EventRecurrence'),
        migrations.RenameField('EventTime', 'interval', 'recurrence'),
        migrations.RenameField('EventTime', 'interval_auto', 'recurrence_auto'),
    ]