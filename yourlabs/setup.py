import posixpath
import os
import re
import os.path

from django.utils.importlib import import_module

class Setup(object):
    """
    This class helps keeping default settings out of your settings file by
    working with the globals() array.

    To set all sensible defaults, add to settings.py:

        USE_PINAX = True

        from yourlabs.setup import Setup
        setup = Setup(globals())
        setup.full()
    """
    def __init__(self, settings):
        self.ready = False
        self.settings = settings
        self.paths = []
        self.settings['gettext'] = lambda s: s

        self.PROJECT_ROOT = None
        if 'PROJECT_ROOT' in settings.keys():
            self.PROJECT_ROOT = settings['PROJECT_ROOT']
        elif 'DJANGO_SETTINGS_MODULE' in os.environ:
            self.settings_module = import_module(
                os.environ['DJANGO_SETTINGS_MODULE'])
            if hasattr(self.settings_module, '__path__'):
                self.PROJECT_ROOT = os.path.abspath(
                    self.settings_module.__path__)
            elif hasattr(self.settings_module, '__file__'):
                self.PROJECT_ROOT = os.path.abspath(os.path.dirname(
                    self.settings_module.__file__))

        if self.PROJECT_ROOT is None:
            print '[yourlabs] Could not find your project root, not setting up'
        else:
            print '[yourlabs] Setting PROJECT_ROOT: %s' % self.PROJECT_ROOT
            self.settings['PROJECT_ROOT'] = self.PROJECT_ROOT
            self.ready = True

 
    def debug_settings(self):
        return {
            'INSTALLED_APPS': [
                'devserver',
                'debug_toolbar',
            ],
            'MIDDLEWARE_CLASSES': [
                'debug_toolbar.middleware.DebugToolbarMiddleware'
            ]
        }

    def debug(self, value=True):
        if not self.ready: return
        s = self.settings
        
        s['DEBUG'] = value
        s['SERVE_MEDIA'] = value
        s['TEMPLATE_DEBUG'] = value

        if not value:
            for k, v in self.debug_settings():
                for x in v:
                    s[k].pop(s[k].index(x))

    def full(self):
        self.defaults()
        self.filesystem()
        self.create_paths()
        self.pinax()
        self.media()
        self.static()
        self.admin()
        self.template()
        self.fixture()
        self.locale()
        self.logging()
        self.applications()

    def defaults(self):
        if not self.ready: return
        s = self.settings

        if not 'SITE_ID' in s:
            s['SITE_ID'] = 1

        if not 'MESSAGE_STORAGE' in s:
            s['MESSAGE_STORAGE'] = 'django.contrib.messages.storage.session.SessionStorage'

        if not 'DATABASES' in s:
            s['DATABASES'] = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3', 
                    'NAME': 'dev.db',
                }
            }

        if not 'ROOT_URLCONF' in s:
            s['ROOT_URLCONF'] = 'urls'

    def filesystem(self):
        if not self.ready: return
        s = self.settings

        s['VAR_ROOT'] = os.path.join(s['PROJECT_ROOT'], 'var')
        s['RUN_ROOT'] = os.path.join(s['VAR_ROOT'], 'run')
        s['LOG_ROOT'] = os.path.join(s['VAR_ROOT'], 'log')

        for i in ('VAR_ROOT', 'RUN_ROOT', 'LOG_ROOT'):
            self.paths.append(s[i])
    
    def pinax(self):
        if not self.ready: return
        s = self.settings
        
        if not s.get('USE_PINAX', False):
            return
        
        if 'PINAX_ROOT' not in s.keys():
            import pinax
            s['PINAX_ROOT'] = os.path.abspath(os.path.dirname(pinax.__file__))
            
        if 'PINAX_THEME' not in s.keys():
            s['PINAX_THEME'] = 'default'
     
    def media(self):
        if not self.ready: return
        s = self.settings

        if not 'MEDIA_ROOT' in s.keys():
            s['MEDIA_ROOT'] = os.path.join(s['PROJECT_ROOT'], 
                                           'site_media', 'media')

        if not 'MEDIA_URL' in s.keys():
            s['MEDIA_URL'] = '/site_media/media/'

        self.paths.append(s['MEDIA_ROOT'])

    def static(self):
        if not self.ready: return
        s = self.settings

        if not 'STATIC_ROOT' in s.keys():
            s['STATIC_ROOT'] = os.path.join(s['PROJECT_ROOT'], 
                                           'site_media', 'static')
        
        if not 'STATIC_URL' in s.keys():
            s['STATIC_URL'] = '/site_media/static/'
    
        if not 'STATICFILES_DIRS' in s.keys():
            s['STATICFILES_DIRS'] = [
                os.path.join(s['PROJECT_ROOT'], 'media'),
            ]

            if s['USE_PINAX']:
                s['STATICFILES_DIRS'].append(
                    os.path.join(s['PINAX_ROOT'], 'templates', s['PINAX_THEME']))
        
        self.paths.append(s['STATIC_ROOT'])

    def admin(self):
        if not self.ready: return
        s = self.settings
        
        if 'ADMIN_MEDIA_PREFIX' not in s.keys():
            s['ADMIN_MEDIA_PREFIX'] = posixpath.join(s['STATIC_URL'], 'admin/')

    def template(self):
        if not self.ready: return
        s = self.settings

        if 'TEMPLATE_DIRS' not in s.keys():
            s['TEMPLATE_DIRS'] = [
                os.path.join(s['PROJECT_ROOT'], 'templates'),
            ]
            
            if s['USE_PINAX']:
                s['TEMPLATE_DIRS'].append(os.path.join(
                    s['PINAX_ROOT'], 'templates', s['PINAX_THEME']))
   
        self.paths += s['TEMPLATE_DIRS']

    def fixture(self):
        if not self.ready: return
        s = self.settings

        if 'FIXTURE_DIRS' not in s.keys():
            s['FIXTURE_DIRS'] = [
                os.path.join(s['PROJECT_ROOT'], 'fixtures'),
            ]
        
        self.paths += s['FIXTURE_DIRS']
    
    def create_paths(self):
        for path in self.paths:
            if not os.path.isdir(path):
                print '[yourlabs] CREATING', path
                os.makedirs(path)
    
    def locale(self, value=True):
        if not self.ready: return
        s = self.settings

        s['USE_I18N'] = value
        s['USE_L18N'] = value

    def logging(self, value=True):
        if not self.ready: return
        s = self.settings

        if 'LOGGING' not in s.keys():
            s['LOGGING'] = {
                'version': 1,
                'formatters': {
                    'verbose': {
                        'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
                    },
                    'simple': {
                        'format': '%(levelname)s %(message)s'
                    },
                },
                'handlers': {
                    'console':{
                        'level':'DEBUG',
                        'class':'logging.StreamHandler',
                        'formatter': 'simple'
                    },
                    'log_file':{
                        'level': 'DEBUG',
                        'class': 'logging.handlers.RotatingFileHandler',
                        'filename': os.path.join(s['LOG_ROOT'], 'django.log'),
                        'maxBytes': '16777216', # 16megabytes
                        'formatter': 'verbose'
                    },
                    'mail_admins': {
                        'level': 'ERROR',
                        'class': 'django.utils.log.AdminEmailHandler',
                        'include_html': True,
                    },
                },
                'loggers': {
                    'django': {
                        'handlers': ['console'],
                        'level': 'INFO',
                        'propagate': True,
                    },
                }
            }
        
        if 'django' in s['LOGGING'] and not s['DEBUG']:
            s['LOGGING']['django']['handlers'] = ['log_file']

    def add_logger(self, name, level='debug', formatter='simple'):
        if not self.ready: return
        s = self.settings

        s['LOGGING']['handlers']['%s_log_file' % name] = {
            'level': level.upper(),
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(s['LOG_ROOT'], '%s.log' % name),
            'maxBytes': '16777216', # 16megabytes
            'formatter': formatter
        }
        s['LOGGING']['loggers'][name] = {
            'handlers': ['console', '%s_log_file' % name],
            'level': level.upper(),
            'propagate': True,
        }

        if s['DEBUG']:
            s['LOGGING']['loggers'][name]['handlers'] = ['console']

    def applications(self):
        if not self.ready: return
        s = self.settings

        self.setup_haystack()
        self.setup_modeltranslation()
        self.setup_djkombu()
        self.setup_emailconfirmation()
        self.setup_localeurl()
        self.setup_yourlabs()

        if s['USE_PINAX']:
            self.setup_pinax_account()
    
    def setup_haystack(self):
        if not self.ready: return
        s = self.settings

        if 'HAYSTACK_ENABLE_REGISTRATION' not in s.keys():
            s['HAYSTACK_ENABLE_REGISTRATION'] = False
        if 'HAYSTACK_SITECONF' not in s.keys():
            s['HAYSTACK_SITECONF'] = 'search_sites'
        if 'HAYSTACK_SEARCH_ENGINE' not in s.keys():
            s['HAYSTACK_SEARCH_ENGINE'] = 'whoosh'
        if 'HAYSTACK_WHOOSH_PATH' not in s.keys():
            s['HAYSTACK_WHOOSH_PATH'] = os.path.join(s['VAR_ROOT'], 'whoosh')
        
        if s['HAYSTACK_SEARCH_ENGINE'] == 'whoosh':
            self.paths.append(s['HAYSTACK_WHOOSH_PATH'])

    def setup_modeltranslation(self):
        if not self.ready: return
        s = self.settings

        s['MODELTRANSLATION_DEFAULT_LANGUAGE']='en'
        s['MODELTRANSLATION_TRANSLATION_REGISTRY']='translation'

    def setup_djkombu(self):
        if not self.ready: return
        s = self.settings
    
        s['BROKER_BACKEND'] = "djkombu.transport.DatabaseTransport"

    def setup_emailconfirmation(self):
        if not self.ready: return
        s = self.settings

        if 'EMAIL_CONFIRMATION_DAYS' not in s.keys():
            s['EMAIL_CONFIRMATION_DAYS'] = 3

    def setup_localeurl(self):
        if not self.ready: return
        s = self.settings
        
        if 'LOCALE_INDEPENDENT_PATHS' not in s.keys():
            s['LOCALE_INDEPENDENT_PATHS'] = []
        s['LOCALE_INDEPENDENT_PATHS'].append(re.compile('/robots.txt'))
        
        if 'LOCALEURL_USE_ACCEPT_LANGUAGE' not in s.keys():
            s['LOCALEURL_USE_ACCEPT_LANGUAGE'] = True

    def setup_pinax_account(self):
        if not self.ready: return
        s = self.settings

        if not s['USE_PINAX']:
            return 

        if 'ACCOUNT_OPEN_SIGNUP' not in s.keys():
            s['ACCOUNT_OPEN_SIGNUP'] = True
        
        if 'ACCOUNT_EMAIL_VERIFICATION' not in s.keys():
            if s.get('DEBUG', False):
                s['ACCOUNT_EMAIL_VERIFICATION'] = False
            else:
                s['ACCOUNT_EMAIL_VERIFICATION'] = True
        
        if 'LOGIN_URL' not in s.keys():
            s['LOGIN_URL']='/account/login/'
    
    def setup_yourlabs(self):
        if not self.ready: return
        s = self.settings

        if 'yourlabs.runner' in s['INSTALLED_APPS']:
            self.add_logger('runner')
        if 'yourlabs.smoke' in s['INSTALLED_APPS']:
            self.add_logger('smoke')
