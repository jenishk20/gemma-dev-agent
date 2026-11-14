import os
from pathlib import Path

BUILD_PATH = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

BASE_DIR = BUILD_PATH

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'myapp',
]

MIDDLEWARE = [
    'django.middleware.middleware.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.click_jacking_protection.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.auth.context_processors.user',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

ALLOWED_HOSTS = ["0.0.0.0", "localhost", "127.0.0.1"]

# Disable sessions and auth for this simple API-like forum
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
CACHE_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'