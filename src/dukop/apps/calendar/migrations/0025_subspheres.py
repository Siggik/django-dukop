from django.db import migrations, models


def update_spheres(apps, schema_editor):
    Sphere = apps.get_model('calendar', 'Sphere')

    everywhere = Sphere.objects.get(slug="", default=True)
    cph = Sphere.objects.get(slug="cph")
    aah = Sphere.objects.get(slug="aah")

    if not cph in everywhere.sub_spheres.all():
        everywhere.sub_spheres.add(cph)

    if not aah in everywhere.sub_spheres.all():
        everywhere.sub_spheres.add(aah)


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0024_eventtime_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='sphere',
            name='sub_spheres',
            field=models.ManyToManyField(blank=True, help_text="Other spheres intersecting or contained within this sphere. This can only have one level of 'nested' spheres - you can only choose spheres that aren't also containing other spheres.", limit_choices_to={'sub_spheres': None}, null=True, related_name='_calendar_sphere_sub_spheres_+', to='calendar.Sphere', verbose_name='Related spheres'),
        ),
        migrations.AlterField(
            model_name='eventlink',
            name='link',
            field=models.URLField(blank=True, help_text="Must begin with 'https://' or 'http://'", max_length=2048, null=True),
        ),
        migrations.RunPython(update_spheres),
    ]
