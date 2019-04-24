"""
Django settings for cjworkbench project.

Generated by 'django-admin startproject' using Django 1.10.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""


import os
import sys
import json
from json.decoder import JSONDecodeError
from os.path import abspath, dirname, join, normpath
from server.settingsutils import workbench_user_display

if sys.version_info[0] < 3:
    raise RuntimeError('CJ Workbench requires Python 3')

SITE_ID = 1

# ----- Configurable Parameters -----

# How many rows in one table?
MAX_ROWS_PER_TABLE = 1000000

# How much StoredObject space can each module take up?
MAX_STORAGE_PER_MODULE = 1024*1024*1024

# configuration for urlscraper
SCRAPER_NUM_CONNECTIONS = 8
SCRAPER_TIMEOUT = 30  # seconds

# Chunk size for chardet file encoding detection
CHARDET_CHUNK_SIZE = 1024*1024

# Chunk size for separator detection
SEP_DETECT_CHUNK_SIZE = 1024*1024

# Use categories if file over this size
CATEGORY_FILE_SIZE_MIN = 250*1024*1024

# ----- App Boilerplate -----

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration below uses these instead of BASE_DIR
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
if 'CJW_PRODUCTION' in os.environ:
    DEBUG = not os.environ['CJW_PRODUCTION']
else:
    DEBUG = True

DEFAULT_FROM_EMAIL = 'Workbench <hello@accounts.workbenchdata.com>'

# SECRET_KEY
try:
    SECRET_KEY = os.environ['CJW_SECRET_KEY']
except KeyError:
    sys.exit('Must set CJW_SECRET_KEY')

# DATABASES
try:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'cjworkbench',
            'USER': 'cjworkbench',
            'HOST': os.environ['CJW_DB_HOST'],
            'PASSWORD': os.environ['CJW_DB_PASSWORD'],
            'PORT': '5432',
            'CONN_MAX_AGE': 30,
            'TEST': {
                'SERIALIZE': False,
            }
        }
    }
except KeyError:
    sys.exit('Must set CJW_DB_HOST and CJW_DB_PASSWORD')

# RabbitMQ
try:
    RABBITMQ_HOST = os.environ['CJW_RABBITMQ_HOST']
except KeyError:
    sys.exit('Must set CJW_RABBITMQ_HOST')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_rabbitmq.core.RabbitmqChannelLayer',
        'CONFIG': {
            'host': RABBITMQ_HOST
        },
    },
}

# EMAIL_BACKEND
#
# In Production, sets ACCOUNT_ADAPTER, SENDGRID_TEMPLATE_IDS
if DEBUG or os.environ.get('CJW_MOCK_EMAIL'):
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.path.join(BASE_DIR, 'local_mail')
else:
    EMAIL_BACKEND = 'sgbackend.SendGridBackend'
    # ACCOUNT_ADAPTER is specifically for sendgrid and nothing else
    ACCOUNT_ADAPTER = 'cjworkbench.views.account_adapter.WorkbenchAccountAdapter'

    if 'CJW_SENDGRID_API_KEY' not in os.environ:
        sys.exit('Must set CJW_SENDGRID_API_KEY in production')

    if not all(x in os.environ for x in [
                'CJW_SENDGRID_INVITATION_ID',
                'CJW_SENDGRID_CONFIRMATION_ID',
                'CJW_SENDGRID_PASSWORD_CHANGE_ID',
                'CJW_SENDGRID_PASSWORD_RESET_ID']):
        sys.exit('Must set Sendgrid template IDs for all system emails')

    SENDGRID_API_KEY = os.environ['CJW_SENDGRID_API_KEY']

    SENDGRID_TEMPLATE_IDS = {
        'account/email/email_confirmation': os.environ['CJW_SENDGRID_CONFIRMATION_ID'],
        'account/email/email_confirmation_signup': os.environ['CJW_SENDGRID_CONFIRMATION_ID'],
        'account/email/password_reset_key': os.environ['CJW_SENDGRID_PASSWORD_RESET_ID'],
    }

try:
    GOOGLE_ANALYTICS_PROPERTY_ID = os.environ['CJW_GOOGLE_ANALYTICS']
except KeyError:
    pass

if 'HTTPS' in os.environ and os.environ['HTTPS'] == 'on':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'channels',
    'webpack_loader',
    'rest_framework',
    'polymorphic',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'cjworkbench',
    'server',
    'worker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
]

SESSION_ENGINE='django.contrib.sessions.backends.db'

ROOT_URLCONF = 'cjworkbench.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages'
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
}

WSGI_APPLICATION = 'cjworkbench.wsgi.application'
ASGI_APPLICATION = 'cjworkbench.asgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = '/account/login'
LOGIN_REDIRECT_URL = '/workflows'

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files. CSS, JavaScript are bundled by webpack, but fonts, test data,
# images, etc. are not
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'server.staticfiles.LessonSupportDataFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
]
STATIC_ROOT = normpath(join(DJANGO_ROOT, 'static'))
STATICFILES_DIRS = (
    ('bundles', os.path.join(BASE_DIR, 'assets', 'bundles')),
    ('fonts', os.path.join(BASE_DIR, 'assets', 'fonts')),
    ('images', os.path.join(BASE_DIR, 'assets', 'images')),
)
# Make `collectstatic` command upload to the right place
STATICFILES_STORAGE = 'server.storage.minio_storage_for_collectstatic.MinioStorage'

# In dev mode, we'll serve local files. But in prod we can overwrite STATIC_URL
# to serve from S3
#
# We break with Django tradition here and give an absolute URL even when
# in DEBUG mode. That's good! We need absolute URLs even in DEBUG mode,
# because lessons include data files the worker must access.
STATIC_URL = os.environ.get('STATIC_URL', 'http://localhost:8000/static/')

# Webpack loads all our js/css into handy bundles
WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'bundles/',
        'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plaintext': {
            'format': (
                '%(levelname)s %(asctime)s %(name)s %(thread)d %(message)s'
            ),
        },
        'json': {
            'class': 'server.logging.json.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'plaintext' if DEBUG else 'json',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # It's nice to have level=DEBUG, but we have experience with lots of
        # modules that we think are now better off as INFO.
        'aioamqp': {'level': 'INFO'},
        'asyncio': {'level': 'INFO'},
        'botocore': {'level': 'INFO'},
        'channels_rabbitmq': {'level': 'INFO'},
        'daphne': {'level': 'INFO'},
        'intercom': {'level': 'INFO'},
        'oauthlib': {'level': 'INFO'},
        'urllib3': {'level': 'INFO'},
        'requests_oauthlib': {'level': 'INFO'},
        's3transfer': {'level': 'INFO'},
        'django.request': {
            # Django prints WARNINGs for 400-level HTTP responses. That's
            # wrong: our code is _meant_ to output 400-level HTTP responses in
            # some cases -- that's exactly why 400-level HTTP responses exist!
            # Ignore those WARNINGs and only log ERRORs.
            'level': 'ERROR',
        },
        'django.channels.server': {'level': 'ERROR'},  # ditto djano.request
        # DEBUG only gets messages when settings.DEBUG==True
        'django.db.backends': {'level': 'INFO'},
    }
}

# User accounts

ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USER_DISPLAY = workbench_user_display
ACCOUNT_SIGNUP_FORM_CLASS = 'cjworkbench.forms.signup.WorkbenchSignupForm'

AUTHENTICATION_BACKENDS = [
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Third party services
PARAMETER_OAUTH_SERVICES = {}  # id_name => parameters. See requests-oauthlib docs

# Google, for Google Drive.

CJW_GOOGLE_CLIENT_SECRETS_PATH = os.environ.get('CJW_GOOGLE_CLIENT_SECRETS', False)
if not CJW_GOOGLE_CLIENT_SECRETS_PATH:
    CJW_GOOGLE_CLIENT_SECRETS_PATH = 'client_secret.json'

CJW_GOOGLE_CLIENT_SECRETS_PATH = os.path.join(BASE_DIR, CJW_GOOGLE_CLIENT_SECRETS_PATH)

GOOGLE_OAUTH2_CLIENT_SECRETS_JSON = None
if os.path.isfile(CJW_GOOGLE_CLIENT_SECRETS_PATH):
    GOOGLE_OAUTH2_CLIENT_SECRETS_JSON = CJW_GOOGLE_CLIENT_SECRETS_PATH

    with open(GOOGLE_OAUTH2_CLIENT_SECRETS_JSON) as f:
        d = json.load(f)
        PARAMETER_OAUTH_SERVICES['google_credentials'] = {
            'class': 'OAuth2',
            'client_id': d['web']['client_id'],
            'client_secret': d['web']['client_secret'],
            'auth_url': d['web']['auth_uri'],
            'token_url': d['web']['token_uri'],
            'refresh_url': d['web']['token_uri'],
            'redirect_url': d['web']['redirect_uris'][0],
            'scope': ' '.join([
                'openid',
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
            ])
        }


# Twitter, for Twitter module

CJW_TWITTER_CLIENT_SECRETS_PATH = os.environ.get('CJW_TWITTER_CLIENT_SECRETS', False)
if not CJW_TWITTER_CLIENT_SECRETS_PATH:
    CJW_TWITTER_CLIENT_SECRETS_PATH = 'twitter_secret.json'
CJW_TWITTER_CLIENT_SECRETS_PATH = os.path.join(BASE_DIR, CJW_TWITTER_CLIENT_SECRETS_PATH)

try:
    with open(CJW_TWITTER_CLIENT_SECRETS_PATH) as f:
        d = json.load(f)
        PARAMETER_OAUTH_SERVICES['twitter_credentials'] = {
            'class': 'OAuth1a',
            'consumer_key': d['key'],
            'consumer_secret': d['secret'],
            'auth_url': 'https://api.twitter.com/oauth/authorize',
            'request_token_url': 'https://api.twitter.com/oauth/request_token',
            'access_token_url': 'https://api.twitter.com/oauth/access_token',
            'redirect_url': d['redirect_url'],
        }
except FileNotFoundError:
    # Cannot print(): integration tests parse stdout/stderr.
    #print(f'Missing {CJW_TWITTER_CLIENT_SECRETS_PATH}. Twitter auth will not work')
    pass

# Various services for django-allauth

CJW_SOCIALACCOUNT_SECRETS_PATH = os.environ.get('CJW_SOCIALACCOUNT_SECRETS', False)
if not CJW_SOCIALACCOUNT_SECRETS_PATH:
    CJW_SOCIALACCOUNT_SECRETS_PATH = 'socialaccounts_secrets.json'

CJW_SOCIALACCOUNT_SECRETS_PATH = os.path.join(BASE_DIR, CJW_SOCIALACCOUNT_SECRETS_PATH)

if os.path.isfile(CJW_SOCIALACCOUNT_SECRETS_PATH):
    try:
        CJW_SOCIALACCOUNT_SECRETS = json.loads(open(CJW_SOCIALACCOUNT_SECRETS_PATH, 'r').read())
    except JSONDecodeError:
        CJW_SOCIALACCOUNT_SECRETS = []

    for provider in CJW_SOCIALACCOUNT_SECRETS:


        INSTALLED_APPS.append('allauth.socialaccount.providers.' + provider['provider'])
else:

    CJW_SOCIALACCOUNT_SECRETS = []


# Knowledge base root url, used as a default for missing help links
KB_ROOT_URL = 'http://help.workbenchdata.com/'

I_AM_TESTING = 'test' in sys.argv
if I_AM_TESTING:
    for provider in ['allauth.socialaccount.providers.facebook',
                     'allauth.socialaccount.providers.google']:
        if provider not in INSTALLED_APPS:
            INSTALLED_APPS.append(provider)

TEST_RUNNER = 'server.tests.runner.TimeLoggingDiscoverRunner'

if 'MINIO_URL' not in os.environ:
    sys.exit('Must set MINIO_URL')
if 'MINIO_ACCESS_KEY' not in os.environ:
    sys.exit('Must set MINIO_ACCESS_KEY')
if 'MINIO_SECRET_KEY' not in os.environ:
    sys.exit('Must set MINIO_SECRET_KEY')
if 'MINIO_BUCKET_PREFIX' not in os.environ:
    sys.exit('Must set MINIO_BUCKET_PREFIX')
MINIO_URL = os.environ['MINIO_URL']
MINIO_EXTERNAL_URL = os.environ.get('MINIO_EXTERNAL_URL', MINIO_URL)
MINIO_ACCESS_KEY = os.environ['MINIO_ACCESS_KEY']
MINIO_SECRET_KEY = os.environ['MINIO_SECRET_KEY']
MINIO_BUCKET_PREFIX = os.environ['MINIO_BUCKET_PREFIX']
MINIO_BUCKET_SUFFIX = os.environ.get('MINIO_BUCKET_SUFFIX', '')
MINIO_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
if 'MINIO_STATIC_URL_PATTERN' in os.environ:
    STATIC_URL = os.environ['MINIO_STATIC_URL_PATTERN'] \
        .replace('{MINIO_BUCKET_PREFIX}', MINIO_BUCKET_PREFIX)

if STATIC_URL != 'http://localhost:8000/static/':
    print(f'Serving static files from {STATIC_URL}')
