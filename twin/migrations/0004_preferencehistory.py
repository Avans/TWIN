# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-27 13:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('twin', '0003_delete_term'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreferenceHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('preference_for', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preferencehistory_for', to='twin.Student', verbose_name='Heeft voorkeur voor')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='twin.Student')),
            ],
            options={
                'ordering': ['student'],
                'verbose_name': 'Voorkeur geschiedenis',
                'verbose_name_plural': 'Voorkeuren geschiedenis',
            },
        ),
    ]
