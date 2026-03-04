"""
WSGI config for academic_platform project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Set the Django settings module for the 'wsgi' application.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_platform.settings')

application = get_wsgi_application()

