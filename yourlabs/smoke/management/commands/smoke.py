from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

import smoke

class Command(BaseCommand):
    args = 'n/a'
    help = 'gsm smoke test'

    def handle(self, *args, **options):
        for app in settings.INSTALLED_APPS:
            app_module = import_module(app)
            try:
                module = import_module('%s.smoke' % app)
                module.Smoke().run()
            except:
                if module_has_submodule(app_module, 'smoke'):
                    raise
