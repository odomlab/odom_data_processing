from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = [

  # Repository admin docs:
  url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

  # Repository admin site:
  url(r'^admin/', include(admin.site.urls)),

  # Main repository app.
  url(r'^repository/', include('osqpipe.urls')),
]
