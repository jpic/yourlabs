import logging
import pickle

from django.db.models import get_model
from django.conf import settings
from django.test import client

logger = logging.getLogger('smoke')

class Smoke(object):
    def get_client(self):
        c = client.Client()
        c.login(username=settings.SMOKE_TEST_USERNAME, password=settings.SMOKE_TEST_PASSWORD)
        return c

    def run(self):
        FailUrl = get_model('smoke', 'failurl')
        c = self.get_client()

        for url in self.get_urls():
            failurl = FailUrl(url=url)

            try:
                response = c.get(url)
                if response.status_code != 200:
                    failurl.reason = 'status code %s' % response.status_code
                    logger.error('status code %s from %s' % (response.status_code, url))
                    failurl.save()
            except Exception as e:
                failurl.exception = pickle.dumps(e)
                failurl.reason = 'exception'
                failurl.save()
                logger.error('exception %s in %s' % (e, url))
