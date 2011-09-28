import sys
import logging
import pickle
import traceback

from django.db.models import get_model
from django.conf import settings
from django.test import client

from yourlabs import runner

try:
    from sentry.client.models import sentry_exception_handler
except ImportError:
    sentry_exception_handler = False

logger = logging.getLogger('smoke')

class SmokeUrl(object):
    def __init__(self, url, tags):
        self.url = url
        self.tags = tags

class Smoke(object):
    def get_client(self):
        c = client.Client()
        c.login(username=settings.SMOKE_TEST_USERNAME, password=settings.SMOKE_TEST_PASSWORD)
        return c

    def run(self):
        FailUrl = get_model('smoke', 'failurl')
        c = self.get_client()

        for smoke_url in self.get_urls():
            FailUrl.objects.filter(url=smoke_url.url).delete()
            failurl = FailUrl(url=smoke_url.url)

            try:
                response = c.get(smoke_url.url)
                if response.status_code != 200:
                    logger.error('status code %s from %s' % (response.status_code, smoke_url.url))
                    failurl.reason = 'status code %s' % response.status_code
                    failurl.save()
                    failurl.tags.add(smoke_url.tags)
                    continue
            except Exception as e:
                if sentry_exception_handler:
                    sentry_exception_handler(request=response.request)

                exc_type, exc_value, exc_tb = sys.exc_info()
                print ''.join(traceback.format_exception(
                                exc_type, exc_value, exc_tb))
                logger.error('exception %s in %s' % (e, smoke_url.url))
                failurl.traceback = pickle.dumps(traceback.format_exception(
                                exc_type, exc_value, exc_tb))
                failurl.exception = unicode(e)
                failurl.reason = 'exception'
                failurl.save()
                failurl.tags.add(smoke_url.tags)
                continue
            
            # should be ok
            FailUrl.objects.filter(url=smoke_url.url).delete()
