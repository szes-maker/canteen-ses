from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.homepage, name='homepage'),
    url(r'^login/$', views.login, name='login'),
    url(r'^query/(?P<year>\d{4})/(?P<month>\d{1,2})/$', views.query, name='query'),
    url(r'^menu/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.menu, name='menu'),
    url(r'^submit/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.submit, name='submit'),
    url(r'^logout/$', views.logout, name='logout'),
]
