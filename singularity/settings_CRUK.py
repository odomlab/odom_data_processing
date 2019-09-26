
# Django settings for cs_pipeline project.

# Note: do not attempt to load the pipeline config object here. Doing
# so will seriously mess up tests of the config system.

DEBUG = False # This is production now.
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Gord Brown', 'gordon.brown@cruk.cam.ac.uk'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE'   : 'django.db.backends.postgresql_psycopg2',
        'NAME'     : 'chipseq',
        'USER'     : 'chipseq',
        'PASSWORD' : 'XXXXXXXX',
        'HOST'     : 'dolab-srv003.cri.camres.org', # set to use tunnel from EBI back to CI
        'PORT'     : '', # port to tunnel
    }
}

# Set default locale (as recommended here: http://stackoverflow.com/questions/10339963/getdefaultlocale-returning-none-when-running-sync-db-on-django-project-in-pychar).
import os; os.environ['LC_ALL'] = 'en_GB.UTF-8'

# Get our project path for use in auto-creating template dirs,
# below. This points at our enclosing directory, i.e. pipeline/django/
PROJECT_PATH = os.path.realpath(os.path.split(os.path.dirname(__file__))[0])

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
#STATIC_ROOT = '/sw/local/var/www/html/django'
STATIC_ROOT = '/var/www/html/django'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody (done - TFR).
SECRET_KEY = ',8au(9o2@3%pcid98A(*Oufl23^&EUIea8EOL11!9812AO#$%ULYD#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'cs_pipeline.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'cs_pipeline.wsgi.application'

from pkg_resources import Requirement, resource_filename
TEMPLATE_DIRS = (
    PROJECT_PATH + '/cs_pipeline/templates/',

    # FIXME I suspect this is a bit of a hack, vulnerable to the
    # osqpipe egg being compressed.
    resource_filename(Requirement.parse('osqpipe'), 'osqpipe/templates/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
    'django.contrib.humanize',
    'osqpipe',
    'sitetree',
    'rest_framework',
    'rest_framework.authtoken',
# The following are for development use only:
#    'debug_toolbar',
#    'devserver',
)

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/django_log.txt',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_auth_ldap': {
          'handlers': ['file'],
          'level': 'DEBUG',
          'propagate': True,
        },
    }
}

# Required by the debug_toolbar middleware.
INTERNAL_IPS=('127.0.0.1',)

DEBUG_TOOLBAR_CONFIG = {

  # Set to true to interrupt e.g. all search form redirects in list views.
  'INTERCEPT_REDIRECTS': False,
}

# Required for the sitetree app
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += ('django.core.context_processors.request',
                                'django.contrib.auth.context_processors.auth')

# Some authentication config
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

from django.conf.global_settings import AUTHENTICATION_BACKENDS
#AUTHENTICATION_BACKENDS += ('django_auth_ldap.backend.LDAPBackend',)

# Allow LDAP authentication.
#import ldap
#from django_auth_ldap.config import LDAPSearch

#AUTH_LDAP_SERVER_URI = "ldap://dc.cri.camres.org:389"

# The following gleaned from our Redmine installation. FIXME move
# these out into our main pipeline config at some point.
#AUTH_LDAP_BIND_DN       = "CRI\SVC-DOLabLDAP"
#AUTH_LDAP_BIND_PASSWORD = "D59PJSZOicHwmnS5xXHV"
#AUTH_LDAP_USER_SEARCH   = LDAPSearch("OU=CRI,OU=Accounts,DC=cri,DC=camres,DC=org",
#                                     ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)")

# Restrict connections to within the building for now.
ALLOWED_HOSTS = ['*']
#ALLOWED_HOSTS = ['*.crnet.org',
#                 '*.cri.camres.org']

REST_FRAMEWORK = {
  # At the very least the REST API requires a login.
  'DEFAULT_PERMISSION_CLASSES': (
    'rest_framework.permissions.IsAuthenticated',
  ),
  'DEFAULT_AUTHENTICATION_CLASSES': (
    'osqpipe.authentication.ExpiringTokenAuthentication',
    'rest_framework.authentication.BasicAuthentication',
    'rest_framework.authentication.SessionAuthentication',
  ),
  'TOKEN_EXPIRE_HOURS': 1,
}
