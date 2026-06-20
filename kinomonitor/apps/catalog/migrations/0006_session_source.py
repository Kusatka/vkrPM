from django.db import migrations, models


def backfill_source(apps, schema_editor):
    """Разметить существующие строки: реальные — по домену ссылки, остальные — demo."""
    Session = apps.get_model("catalog", "Session")
    Session.objects.filter(url__icontains="afisha.ru").update(source="afisha")
    Session.objects.filter(url__icontains="mos-kino.ru").update(source="moskino")
    Session.objects.filter(source="").update(source="demo")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_session_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="source",
            field=models.CharField(
                blank=True,
                choices=[("afisha", "Афиша"), ("moskino", "Москино"), ("demo", "Демо")],
                db_index=True,
                help_text="Откуда данные: парсер Афиши, Москино или демо-генератор",
                max_length=20,
                verbose_name="Источник",
            ),
        ),
        migrations.RunPython(backfill_source, noop),
    ]
