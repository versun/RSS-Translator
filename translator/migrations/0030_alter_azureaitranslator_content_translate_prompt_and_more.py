# Generated by Django 5.0.6 on 2024-05-10 04:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("translator", "0029_azureaitranslator_content_translate_prompt_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="azureaitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="azureaitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="azureaitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="claudetranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="claudetranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="claudetranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="geminitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="geminitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="geminitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="groqtranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="groqtranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="groqtranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="moonshotaitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="moonshotaitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="moonshotaitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="openaitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="openaitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="openaitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="openrouteraitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="openrouteraitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="openrouteraitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="togetheraitranslator",
            name="content_translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Content Translate Prompt",
            ),
        ),
        migrations.AlterField(
            model_name="togetheraitranslator",
            name="summary_prompt",
            field=models.TextField(
                default="Summarize the following text in {target_language} and return markdown format."
            ),
        ),
        migrations.AlterField(
            model_name="togetheraitranslator",
            name="translate_prompt",
            field=models.TextField(
                default="You are a professional, authentic translation engine. Translate only the text into {target_language}, return only the translations, do not explain the original text.",
                verbose_name="Title Translate Prompt",
            ),
        ),
    ]
