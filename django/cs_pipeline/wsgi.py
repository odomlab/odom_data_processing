"""
WSGI config for cs_pipeline project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cs_pipeline.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application

# # ----------- See http://stackoverflow.com/a/21124143 for a discussion of the below:
# from django.core.handlers.wsgi import WSGIHandler

# class WSGIEnvironment(WSGIHandler):

#     def __call__(self, environ, start_response):

#         os.environ['OSQPIPE_CONFDIR'] = environ['OSQPIPE_CONFDIR']
#         return super(WSGIEnvironment, self).__call__(environ, start_response)

# #application = WSGIEnvironment()

# # ----------- The original line, replaced by the above: (and reinstated following ugrade from Django 1.5.4 to 1.8).
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
