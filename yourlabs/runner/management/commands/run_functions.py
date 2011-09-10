import logging

from yourlabs import runner

from django.utils.importlib import import_module

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    args = '<module.function> [<module.function> ...]'
    help = 'Continuously run a set of functions'

    def handle(self, *args, **options):
        functions = []

        for arg in args:
            s = arg.split('.')
            function = s[-1]
            module = '.'.join(s[:-1])
            module = import_module(module)
            functions.append(getattr(module, function))

        logger = logging.getLogger('runner')

        r = runner.Runner(functions, logger)
        r.run()
