# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-02 07:54
from __future__ import unicode_literals

from django.db import migrations, models
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailuser',
            name='auth_number',
            field=models.IntegerField(default=users.models.random_auth_number, help_text='Access key seed for your reports and results. <strong>Warning! Changing this integer will invalidate all previously generated report and result links.</strong>', verbose_name='auth number'),
        ),
    ]
