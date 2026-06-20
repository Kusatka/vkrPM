from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_movie_is_special"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="url",
            field=models.URLField(
                blank=True,
                help_text="Страница источника, где можно купить билет на этот сеанс",
                max_length=500,
                verbose_name="Ссылка на сеанс",
            ),
        ),
    ]
