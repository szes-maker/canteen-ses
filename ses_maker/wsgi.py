"""
WSGI config for ses_maker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os


from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ses_maker.settings")

application = get_wsgi_application()

# For easier local development
if 'POSTGRESQL_PASSWORD' in os.environ:
    from whitenoise.django import DjangoWhiteNoise
    application = DjangoWhiteNoise(application)
