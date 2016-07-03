"""
Django settings for biocloud project.

Generated by 'django-admin startproject' using Django 1.9.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

from os.path import abspath, dirname, join, exists
from pathlib import Path
from django.core.urlresolvers import reverse_lazy
from django.conf import ImproperlyConfigured

# Build paths inside the project like this: join(BASE_DIR, "directory")
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))

# Use 12factor inspired environment variables or from a file
# Powered by django-environ
import environ
env = environ.Env()

# Ideally move env file should be outside the git repo
# i.e. BASE_DIR.parent.parent
env_file = join(dirname(__file__), 'local.env')
if exists(env_file):
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
# Raises ImproperlyConfigured exception if SECRET_KEY not in os.environ
SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    # Raises ImproperlyConfigured exception if DATABASE_URL not in
    # os.environ
    'default': env.db()
}


# Application definition

DJANGO_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

THIRD_PARTY_APPS = (
    'crispy_forms',
    'compressor',
    'django_q',
)

LOCAL_APPS = (
    'core',
    'users',
    'data_sources',
    'experiments',
    'analyses',
    'rna_seq',
    'dashboard',
)

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'biocloud.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(BASE_DIR, 'templates'),
            # More template dirs here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
            ],
        },
    },
]

WSGI_APPLICATION = 'biocloud.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',    # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',   # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',  # noqa
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = join(BASE_DIR, 'assets')

STATICFILES_DIRS = [join(BASE_DIR, 'static')]

# list of finder classes that know how to find static files in
# various locations
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)


# URL settings.

LOGIN_URL = reverse_lazy('login')

LOGOUT_URL = reverse_lazy('logout')

LOGIN_REDIRECT_URL = reverse_lazy('dashboard_home')


# Custom user model

AUTH_USER_MODEL = 'users.EmailUser'


# BioCloud specific path settings

# env.path() returns an environ.Path object.
# environ.Path() converts the path itself into str.
# Path(env.path(...)()) finally converts the str into a pathlib.Path object.
BIOCLOUD_DATA_SOURCES_DIR = Path(env.path(
    'BIOCLOUD_DATA_SOURCES_DIR', required=True
)())
if not BIOCLOUD_DATA_SOURCES_DIR.is_dir():
    raise ImproperlyConfigured(
        "BIOCLOUD_DATA_SOURCES_DIR %s requires to be a directory."
        % BIOCLOUD_DATA_SOURCES_DIR
    )


# Django-Q settings
# Ref: https://django-q.readthedocs.org/en/latest/configure.html

Q_CLUSTER = {
    'name': 'BioCloud-queue',
    'workers': 1,
    'recycle': 5,
    'timeout': None,  # what is timed out may never time out
    'compress': True,
    'save_limit': 10,
    'queue_limit': 1,
    'cpu_affinity': 1,
    'catch_up': False,
    'orm': 'default'
}


# Third-party app and custom settings

LIBSASS_SOURCEMAPS = True

LIBSASS_PRECISION = 10

COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)

CRISPY_TEMPLATE_PACK = 'bootstrap3'

WERKZEUG_DEBUG = env.bool('WERKZEUG_DEBUG', default=False)
