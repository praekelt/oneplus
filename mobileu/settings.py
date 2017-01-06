"""
Django settings for mobileu project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

import djcelery

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

djcelery.setup_loader()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "t(kb(vxl5&51a89sfw+)gzy-*+m5*jef+j*vo%e*5jsa244l3c"

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

# os.path.join(BASE_DIR, "oneplus/templates")
TEMPLATE_DIRS = [os.path.join(BASE_DIR, "templates")]

ALLOWED_HOSTS = []

SITE_ID = 1

# Application definition

INSTALLED_APPS = (
    #"django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "grappelli",
    #"django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "haystack",
    "gamification",
    "communication",
    "content",
    "auth",
    "organisation",
    "core",
    "django_summernote",
    "south",
    "requests",
    "koremutake",
    "import_export",
    "djcelery",
)

MIDDLEWARE_CLASSES = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "mobileu.urls"

WSGI_APPLICATION = "mobileu.wsgi.application"

# Close the session when user closes the browser
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AUTH_USER_MODEL = "auth.CustomUser"

TEST_RUNNER = 'core.tests.TestRunner'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SUMMERNOTE_CONFIG = {
    # Change editor size
    'width': '100%',
    'height': '400',

    # Customize toolbar buttons
    'toolbar': [
        ['style', ['style']],
        ['style', ['bold', 'italic', 'underline', 'clear']],
        ['para', ['ul', 'ol', 'paragraph']],
        ['insert', ['link', 'picture']],
        ['table', ['table']],
    ],
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': os.environ.get('ELASTICSEARCH_URL', 'http://127.0.0.1:9200/'),
        'INDEX_NAME': 'haystack',
    },
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/


STATIC_URL = "/static/"

ENV_PATH = os.path.abspath(os.path.dirname(__file__))
MEDIA_ROOT = os.path.join(ENV_PATH, 'media/')
MEDIA_URL = "/media/"

GRAPPELLI_ADMIN_TITLE = "MobileU"

# STATICFILES_FINDERS = (
#    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.FileSystemFinder',
#)

# TEMPLATE_CONTEXT_PROCESSORS = (
#    "django.core.context_processors.request",
#)

CELERY_IMPORTS = ('mobileu.tasks', 'communication.tasks')
BROKER_URL = 'amqp://guest:guest@localhost:5672/'

MATHML_URL = 'http://mathml.p16n.org/'


GRADE_10_COURSE_NAME = "One Plus Grade 10"
GRADE_11_COURSE_NAME = "One Plus Grade 11"
GRADE_12_COURSE_NAME = "One Plus Grade 12"
GRADE_10_OPEN_CLASS_NAME = "Grade 10 - Open Class"
GRADE_11_OPEN_CLASS_NAME = "Grade 11 - Open Class"
GRADE_12_OPEN_CLASS_NAME = "Grade 12 - Open Class"
OPEN_SCHOOL = "Open School"


try:
    from production_settings import *
except ImportError as e:
    pass
