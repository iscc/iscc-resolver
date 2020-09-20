# -*- coding: utf-8 -*-
"""Ugly side-effect only module :)"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "isccr.settings")
django.setup()
