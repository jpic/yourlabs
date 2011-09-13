import logging

from yourlabs import runner

from django.utils.importlib import import_module

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    args = '<module.function> [<module.function> ...]'
    help = 'Continuously run a set of functions'

    def handle(self, *args, **options):
        r = runner.TaskRunner(args)
        r.run()
