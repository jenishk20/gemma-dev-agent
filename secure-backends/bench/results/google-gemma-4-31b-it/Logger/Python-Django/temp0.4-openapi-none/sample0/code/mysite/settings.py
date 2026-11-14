from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-logging-service-key'
DEBUG = True
ALLOWED_HOSTS = ["0.0.0.0", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'myapp',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = []
WSGI_APPLICATION = 'mysite.wsgi.application'
ASGI_APPLICATION = 'mysite.asgi.application'

# We are using a text file for storage, so we don't need a real DB
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy'
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True