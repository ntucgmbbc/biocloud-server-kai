# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-16 15:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GenomeReference',
            fields=[
                ('identifier', models.CharField(help_text='Identifier for the genome reference. Ex. hg19, GRCh38.p5.', max_length=64, primary_key=True, serialize=False)),
                ('source', models.CharField(choices=[('NCBI', 'NCBI'), ('ENSEMBL', 'Ensembl'), ('UCSC', 'UCSC'), ('OTHER', 'Other or Custom')], help_text='The institution that maintains the genome reference.', max_length=16)),
                ('organism', models.CharField(help_text='Species description using the Linnaean taxonomy naming system. Ex. Homo sapiens; Mus musculus.', max_length=512)),
                ('newer_reference', models.ForeignKey(help_text='If new version of the genome reference of the same organism and source exists, link the reference here. For example, UCSC mm9 can set its newer reference to UCSC mm10.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='analyses.GenomeReference', verbose_name='newer version')),
            ],
        ),
    ]
