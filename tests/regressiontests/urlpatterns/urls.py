from django.conf.urls.defaults import *
from views import OneTimeView, callable_view

urlpatterns = patterns('',
    url(r'^callable-view/$', callable_view),
    url(r'^string-view/$', 'regressiontests.urlpatterns.views.string_view'),
    url(r'^class/new-instance/$', OneTimeView),
    url(r'^class/string/$', 'regressiontests.urlpatterns.views.StringView'),
)
