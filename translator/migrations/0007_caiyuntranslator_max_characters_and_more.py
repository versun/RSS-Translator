# Generated by Django 5.0.1 on 2024-01-30 08:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('translator', '0006_testtranslator_alter_openaitranslator_prompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='caiyuntranslator',
            name='max_characters',
            field=models.IntegerField(default=5000),
        ),
        migrations.AddField(
            model_name='deepltranslator',
            name='max_characters',
            field=models.IntegerField(default=5000),
        ),
        migrations.AddField(
            model_name='deeplxtranslator',
            name='max_characters',
            field=models.IntegerField(default=50000),
        ),
        migrations.AddField(
            model_name='microsofttranslator',
            name='max_characters',
            field=models.IntegerField(default=5000),
        ),
    ]