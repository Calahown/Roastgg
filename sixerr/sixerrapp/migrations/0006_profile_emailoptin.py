# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-27 04:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sixerrapp', '0005_remove_gig_rank'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='emailoptin',
            field=models.BooleanField(default=True),
        ),
    ]
