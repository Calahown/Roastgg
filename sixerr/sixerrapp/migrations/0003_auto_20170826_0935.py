# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-26 16:35
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sixerrapp', '0002_remove_ranks_game'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Ranks',
            new_name='Ranking',
        ),
    ]
