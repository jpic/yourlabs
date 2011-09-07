from django.db.models import Q
from django.db import connection, transaction
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext as _
from django.core import urlresolvers
from django.template import defaultfilters
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command

class FailUrl(models.Model):
    url = models.URLField()
    creation_datetime = models.DateTimeField(auto_now_add=True)

    exception = models.TextField(null=True, blank=True)
    request = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['creation_datetime']
