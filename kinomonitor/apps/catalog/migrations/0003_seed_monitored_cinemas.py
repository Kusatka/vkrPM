"""Сид: два стартовых кинотеатра для парсера afisha (конфиг живёт в БД)."""

from django.db import migrations


def seed(apps, schema_editor):
    Cinema = apps.get_model("catalog", "Cinema")
    Cinema.objects.update_or_create(
        slug="illusion",
        defaults={
            "name": "Иллюзион",
            "network": "Госфильмофонд",
            "is_niche": True,
            "afisha_slug": "illyuzion-2692",
            "is_monitored": True,
            "website": "https://illusion-cinema.ru/",
        },
    )
    Cinema.objects.update_or_create(
        slug="karo-oktyabr",
        defaults={
            "name": "КАРО 11 Октябрь",
            "network": "Каро",
            "afisha_slug": "karo-11-oktyabr-3103",
            "is_monitored": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_cinema_afisha_slug_cinema_is_monitored")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
