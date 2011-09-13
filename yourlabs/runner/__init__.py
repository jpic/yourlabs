import datetime
import logging
import time
import traceback
import signal
import sys
import datetime
import os
import os.path

from django.core.management import call_command
from django.conf import settings
from django.core.mail import send_mail
from django.utils.importlib import import_module

import daemon

class TaskRunner(daemon.Daemon):
    def __init__(self, task_names, pidfile=None, logger='runner', 
                 allow_concurrent=False):
        self.functions = []

        names = []
        for task_name in task_names:
            s = task_name.split('.')
            function = s[-1]
            module = '.'.join(s[:-1])
            module = import_module(module)
            function = getattr(module, function)
            
            self.functions.append(task()(function))
            names.append(function.__name__)

        if pidfile is None:
            pidfile = '_'.join(names)

        super(TaskRunner, self).__init__(pidfile, logger, allow_concurrent)

    def run(self):
        for function in self.functions:
            function.runner_task.run()

def task(**options):
    def wrapper(f):
        f.runner_task = Task(f, **options)
        return f
    return wrapper

class Task(object):
    def __init__(self, function, **options):
        self.function = function
        self.name = self.function.__name__

        self.options = {
            'success_cooldown': datetime.timedelta(minutes=5),
            'fail_cooldown': datetime.timedelta(minutes=20),
            'non_recoverable_downtime': datetime.timedelta(hours=12),
            'logger_name': 'runner',
            'uid': None,
            'gid': None,
        }
        self.options.update(options)

        self.exceptions = []
        self.consecutive_exceptions = []
        self.logger = logging.getLogger(self.options['logger_name'])
        self.admin_emails = []

    def log(self, level, message, *args):
        level = getattr(logging, level.upper())
        self.logger.log(level, '[%s] ' % self.name + message % args)

    def run(self):
        try:
            started = datetime.datetime.now()
            self.function()
            ended = datetime.datetime.now()
            self.success(started, ended)
        except Exception as e:
            ended = datetime.datetime.now()
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.fail(started, ended, e, exc_type, exc_value, exc_tb)

    def success(self, started, ended):
        self.exceptions.append(self.consecutive_exceptions)
        self.consecutive_exceptions = []
        time.sleep(self.options['success_cooldown'])

    def fail(self, started, ended, exc_type, exc_value, exc_tb):
        """
        It will call notify_admins with reason:
        - Task.FIRST_EXCEPTION if it's the first exception raised ever in this
          process, because it might have been introduced by a code update
        - Task.NEW_EXCEPTION if such an exception was never logged
        - Task.NON_RECOVERABLE_DOWNTIME_REACHED if it's been too long since
          the task keeps crashing (see non_recoverable_downtime option)
        - Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN just to make sure the
          email stays in the top of the admin's mailbox
        """
        
        data = {
            'started': started,
            'ended': ended,
            'duration': started - ended,
        }

        if len(self.consecutive_exceptions):
            data['downsince'] = self.consecutive_exceptions[0]['started']
            data['downtime'] = datetime.datetime.now() - data['downsince']

            # add exc_ stuff to data *only* if it differs from the last logged
            # exc_data
            for logged_data in reversed(self.consecutive_exceptions):
                if 'exc_tb' in logged_data.keys():
                    # only bloat with gory details if they are different
                    # from last exception
                    if not self.is_same_exception(exc_type, exc_value, exc_tb, logged_data):
                        data.update({
                            'exc_type': exc_type,
                            'exc_value': exc_value,
                            'exc_tb': exc_tb,
                        })
                    break
        else:
            data.update({
                'exc_type': exc_type,
                'exc_value': exc_value,
                'exc_tb': exc_tb,
                'downsince': ended,
            })

        self.exceptions.append(data)
        self.consecutive_exceptions.append(data)

        if len(self.exceptions) == 1:
            notify_admins = Task.FIRST_EXCEPTION
        else:
            new = True
            for logged_data in self.exceptions:
                if self.is_same_exception(exc_type, exc_value, exc_tb, logged_data):
                    new = False
                    break
            
            if new:
                notify_admins = Task.NEW_EXCEPTION
            elif data['downsince'] >= self.options['non_recoverable_downtime']:
                last_downtime_email = None
                for email in self.admin_emails:
                    downtime_reasons = (
                        Task.NON_RECOVERABLE_DOWNTIME_REACHED, 
                        Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN
                    )
                    if email['reason'] in downtime_reasons:
                        last_downtime_email = email['datetime']
                        break

                if not last_downtime_email:
                    notify_admins = Task.NON_RECOVERABLE_DOWNTIME_REACHED
                elif last_downtime_email + self.options['non_recoverable_downtime'] > datetime.datetime.now():
                    notify_admins = Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN

        if notify_admins:
            self.notify_admins(data, notify_admins)
        time.sleep(self.options['fail_cooldown'])

    def notify_admins(self, data, reason):
        if reason == Task.FIRST_EXCEPTION:
            suject = 'First exception caught: %s' % data['exc_value'].message
        elif reason == Task.NEW_EXCEPTION:
            subject = 'New exception caught: %s' % data['exc_value'].message
        elif reason == Task.NON_RECOVERABLE_DOWNTIME_REACHED:
            subject = 'Non recoverable downtime reached'
        elif reason == Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN:
            suject = 'Non recoverable downtime reached again'

        message = ['Current state details:']
        message.append('Down since', data['downsince'])
        message.append('Down time', data['downtime'])
        message.append('Exception', data['exc_value'].__class__.__name__)
        message.append('Message', data['exc_value'].message)
        message.append(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))

        message.append('')
        message.append('')

        if reason != Task.FIRST_EXCEPTION:
            message.append('Also, here is a list of distinct exceptions raised:')
            
            detailed = []
            for data in self.exceptions:
                new = True

                for detailed_data in detailed:
                    if self.is_same_exception(data['exc_type'], 
                        data['exc_value'], data['exc_tb'], detailed_data):
                        new = False
                        break
                
                if new:
                    message.append('')
                    message.append('Exception', data['exc_value'].__class__.__name__)
                    message.append('Message', data['exc_value'].message)
                    message.append(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))

        send_mail(
            '[%s] %s' % (
                self.name,
                subject
            ),
            "\n".join(message),
            'critical@yourlabs.org',
            [x[1] for x in settings.ADMINS],
            fail_silently=False
        )

    def is_same_exception(self, exc_type, exc_value, exc_tb, data):
        tb = traceback.format_exception(exc_type, exc_value, exc_tb)
        if exc_type != data['exc_type']:
            return False
        if exc_value.message != data['exc_value'].message:
            return False
        if ''.join(tb) != data['traceback']:
            return False
        return True
