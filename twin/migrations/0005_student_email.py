# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-21 15:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twin', '0004_preferencehistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='email',
            field=models.CharField(default='', max_length=200, verbose_name='E-mail'),
        ),
    ]
