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
            
            if not hasattr(function, 'runner_task'):
                function = task()(function)
            self.functions.append(function)
            names.append(function.__name__)

        if pidfile is None:
            pidfile = os.path.join(settings.RUN_ROOT, '_'.join(names))

        super(TaskRunner, self).__init__(pidfile, logger, allow_concurrent)
        self.concurrency_security()

    def run(self):
        while True:
            for function in self.functions:
                function.runner_task.run()

def task(**options):
    def wrapper(f):
        f.runner_task = Task(f, **options)
        return f
    return wrapper

class Task(object):
    FIRST_EXCEPTION = 1
    NEW_EXCEPTION = 2
    NON_RECOVERABLE_DOWNTIME_REACHED = 3
    NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN = 4
    HEALED = 5

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
        if self.logger is None:
            print level, self.name, self.message % args
        elif isinstance(self.logger, str):
            self.logger = logging.getLogger(self.logger)
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
            self.fail(started, ended, exc_type, exc_value, exc_tb)

    def success(self, started, ended):
        self.log('debug', 'Execution successfull')
        if len(self.consecutive_exceptions):
            self.exceptions += self.consecutive_exceptions
            message = [
                'After some failures, the process executed successfully again!',
                'Anyway, here is a list of distinct exceptions raised since last successful run:',
            ]
            detailed = []
            message += self.format_exceptions_message(self.consecutive_exceptions, detailed)

            message.append('Also, here is a list of distinct exceptions raised before last successful run:')
            message += self.format_exceptions_message(self.exceptions, detailed)
            send_mail(
                '[%s] %s' % (self.name, 'Process healed'),
                "\n".join(message),
                'critical@yourlabs.org',
                [x[1] for x in settings.ADMINS],
                fail_silently=False
            )

            self.admin_emails.append({
                'reason': Task.HEALED,
                'datetime': datetime.datetime.now()
            })
            self.log('debug', 'Sent email to admins: Process healed')
        self.consecutive_exceptions = []
        time.sleep(self.options['success_cooldown'].seconds)

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
        
        self.log('debug', 'Execution failed:')
        self.log('debug', 'Exception  %s' % exc_value.__class__.__name__)
        self.log('debug', 'Message  %s' % exc_value.message)
        self.log('debug', ''.join(traceback.format_exception(
            exc_type, exc_value, exc_tb)))


        data = {
            'started': started,
            'ended': ended,
            'duration': started - ended,
        }
        notify_admins = False

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
                'downtime': ended-started,
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
            elif data['downtime'] >= self.options['non_recoverable_downtime']:
                last_downtime_email = None
                for email in reversed(self.admin_emails):
                    downtime_reasons = (
                        Task.NON_RECOVERABLE_DOWNTIME_REACHED, 
                        Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN
                    )
                    if email['reason'] in downtime_reasons:
                        last_downtime_email = email['datetime']
                        break

                if not last_downtime_email:
                    notify_admins = Task.NON_RECOVERABLE_DOWNTIME_REACHED
                elif last_downtime_email + self.options['non_recoverable_downtime'] < datetime.datetime.now():
                    notify_admins = Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN

        if notify_admins:
            self.notify_admins(data, notify_admins)

        self.log('debug', 'Sleeping %s seconds' % 
            self.options['fail_cooldown'].seconds)
        time.sleep(self.options['fail_cooldown'].seconds)

    def notify_admins(self, data, reason):
        exc_type, exc_value, exc_tb = self.get_exception_data_for(data)

        if reason == Task.FIRST_EXCEPTION:
            subject = 'First exception caught: %s' % exc_value.message
        elif reason == Task.NEW_EXCEPTION:
            subject = 'New exception caught: %s' % exc_value.message
        elif reason == Task.NON_RECOVERABLE_DOWNTIME_REACHED:
            subject = 'Non recoverable downtime reached'
        elif reason == Task.NON_RECOVERABLE_DOWNTIME_REACHED_AGAIN:
            subject = 'Non recoverable downtime reached again'

        message = ['Current state details:']
        message.append('Down since  %s' % data['downsince'])
        message.append('Down time  %s' % data['downtime'])
        message.append('Exception  %s' % exc_value.__class__.__name__)
        message.append('Message  %s' % exc_value.message)
        message.append(''.join(traceback.format_exception(
            exc_type, exc_value, exc_tb)))

        message.append('')
        message.append('')

        if reason != Task.FIRST_EXCEPTION:
            message.append('Also, here is a list of distinct exceptions raised:')
            message += self.format_exceptions_message(self.exceptions)


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

        self.admin_emails.append({
            'reason': reason,
            'datetime': datetime.datetime.now()
        })

        self.log('debug', 'Sent email to admins: %s', subject)

    def is_same_exception(self, exc_type, exc_value, exc_tb, data):
        if 'exc_type' not in data.keys():
            return True

        tb = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb2 =traceback.format_exception(
                data['exc_type'], data['exc_value'], data['exc_tb'])

        if exc_type != data['exc_type']:
            return False
        if exc_value.message != data['exc_value'].message:
            return False
        if ''.join(tb) != ''.join(tb2):
            return False
        return True
    
    def get_exception_data_for(self, data):
        if 'exc_tb' in data.keys():
            return (data['exc_type'], data['exc_value'], data['exc_tb'])

        for logged_data in reversed(self.consecutive_exceptions):
            if 'exc_tb' in logged_data.keys():
                return (logged_data['exc_type'], logged_data['exc_value'], 
                        logged_data['exc_tb'])

    def format_exceptions_message(self, exceptions, detailed=None):
        message = []
        
        if detailed is None:
            detailed = []

        for data in exceptions:
            if 'exc_value' not in data.keys():
                continue

            new = True

            for detailed_data in detailed:
                if self.is_same_exception(data['exc_type'], 
                    data['exc_value'], data['exc_tb'], detailed_data):
                    new = False
                    break
            
            if new:
                message.append('')
                message.append('Exception  %s' % data['exc_value'].__class__.__name__)
                message.append('Message  %s' % data['exc_value'].message)
                message.append(''.join(traceback.format_exception(
                    data['exc_type'], data['exc_value'], data['exc_tb'])))
            detailed.append(data)

        return message
