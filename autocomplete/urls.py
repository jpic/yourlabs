from django.conf.urls.defaults import *
from django.conf import settings

import views

urlpatterns = patterns('yourlabs.autocomplete.views',
    url(
        r'',
        views.AutocompleteView.as_view(),
        name='autocomplete',
    ),
)
