

from django.db.backends.mysql.base import DatabaseFeatures
from django.db.backends.base.base import BaseDatabaseWrapper
from datetime import timedelta
from pathlib import Path
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-4foc3q6ki3r=cux4ug9wa)0phx&3wy_i3sq^89y)o*fr#-xvwr',
)
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '*').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django_prometheus',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
    'rest_framework',
    'celery',
]

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'shop_db')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'judyjudy')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = 'UTC'

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'shop.system_metrics_middleware.SystemMetricsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    'shop.middleware.CorrelationIdMiddleware'
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'CONN_MAX_AGE': 0,
    }
}

CACHES = {
    "default": {

        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": "1",           # DB 1 to separate cache from Celery (DB 0)
        },
        "KEY_PREFIX": "shop",
        "TIMEOUT": 300,          # default 5 min, overridden per-view in cache_utils.py
    }
}

# "BACKEND": "django.core.cache.backends.redis.RedisCache",

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'shop.User'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}


BaseDatabaseWrapper.check_database_version_supported = lambda self: None
DatabaseFeatures.can_return_rows_from_bulk_insert = property(
    lambda self: False)
DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)


BASE_DIR = Path(__file__).resolve().parent.parent


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_BASE_DIR = os.path.join(BASE_DIR, 'logs')

# system services
SERVICES = ['auth', 'order', 'cart', 'favorite', 'shops']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_filter': {
            '()': 'shop.middleware.CorrelationIdFilter',
        }
    },
    'formatters': {
        'simple': {
            'format': '[{asctime}] [{correlation_id}] {levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters': ['correlation_filter'],
            'formatter': 'simple',
        },
    },
    'loggers': {}
}

for service in SERVICES:
    service_log_dir = os.path.join(LOG_BASE_DIR, service)
    os.makedirs(service_log_dir, exist_ok=True)
# info handlers
    LOGGING['handlers'][f'{service}_info'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': os.path.join(service_log_dir, 'info.log'),
        'maxBytes': 1024 * 1024 * 5,  # 5MB
        'backupCount': 3,
        'filters': ['correlation_filter'],
        'formatter': 'simple',
    }

  # errors handlers
    LOGGING['handlers'][f'{service}_error'] = {
        'level': 'ERROR',  # Catches WARNING, ERROR, and CRITICAL
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': os.path.join(service_log_dir, 'errors.log'),
        'maxBytes': 1024 * 1024 * 5,
        'backupCount': 5,
        'filters': ['correlation_filter'],
        'formatter': 'simple',
    }

    # Register the unique Logger for this service
    LOGGING['loggers'][f'service.{service}'] = {
        'handlers': ['console', f'{service}_info', f'{service}_error'],
        'level': 'DEBUG',
        'propagate': False,
    }
