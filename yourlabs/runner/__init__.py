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
        self.logger = loggin.getLogger(self.options['logger_name'])
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
                    if !self.is_same_exception(exc_type, exc_value, exc_tb, logged_data):
                        data.update({
                            'exc_type': exc_type,
                            'exc_value': exc_value,
                            'exc_tb': exc_tb,
                            'traceback': tb,
                        })
                    break
        else:
            data.update({
                'exc_type': exc_type,
                'exc_value': exc_value,
                'exc_tb': exc_tb,
                'downsince': ended,
                'traceback': ''.join(tb),
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

        time.sleep(self.options['fail_cooldown'])

    def notify_admins(self, data):
        message = []
        for e in self.exceptions[name]:
            message.append('Message: ' + e['message'])
            message.append('Date/Time: ' + str(e['datetime']))
            message.append('Exception class: ' + e['class'])
            message.append('Traceback:')
            message.append(e['traceback'])
            message.append('')

        send_mail(
            '[%s] Has been failing for %s consecutive times' % (
                name,
                self.consecutive_exceptions[name]
            ),
            "\n".join(message),
            'critical@yourlabs.org',
            ['jamespic@gmail.com'],
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

class Runner(object):
    def __init__(self, functions, logger, name=None, pidfile=None, killconcurrent=True):
        self.functions = functions
        self.logger = logger
        self.exceptions = {}
        self.consecutive_exceptions = {}
        self.killconcurrent = killconcurrent
        self.name = name or '_'.join([f.__name__ for f in self.functions])
        self.pidfile = pidfile or os.path.join(settings.RUN_ROOT, self.name + '.pid')

        for function in self.functions:
            self.exceptions[function.__name__] = []
            self.consecutive_exceptions[function.__name__] = 0

        self.concurrency_security()

    def log(self, level, message, *args):
        level = getattr(logging, level.upper())
        self.logger.log(level, '[%s] ' % self.name + message % args)

    def concurrency_security(self):
        if os.path.exists(self.pidfile):
            try:
                f = open(self.pidfile, 'r')
                concurrent = f.read()
                f.close()
                self.log('debug', 
                    'Found pidfile %s containing: %s', self.pidfile, concurrent)
            except Exception:
                self.log('error', 
                    'Could not read pidfile %s', self.pidfile)

            if os.path.exists('/proc/%s' % concurrent):
                if self.killconcurrent:
                    os.kill(int(concurrent), signal.SIGTERM)
                    self.log('debug', 'Sent SIGTERM to: %s' % concurrent)

                    i = 0
                    while os.path.exists('/proc/%s' % concurrent):
                        time.sleep(5)
                        if i == 5:
                            self.log('error', 
                                'Exiting because concurrent PID %s is still there',
                                concurrent)
                            os._exit(-1)
                        else:
                            self.log('debug', 
                                '/proc/%s still exists, waiting another 5 seconds',
                                concurrent)
                else:
                    self.log('error', 
                        '%s contains a pid (%s) which is still running !',
                        self.pidfile, concurrent)
                    os._exit(-1)
            else:
                self.log('debug', 'Could not find /proc/%s', concurrent)
                os.remove(self.pidfile)
        else:
            self.log('debug', 
                'Did not find pidfile %s, continuing normally', self.pidfile)

        f = open(self.pidfile, 'w')
        f.write(str(os.getpid()))
        f.flush()
        # Forcibly sync disk
        os.fsync(f.fileno())
        f.close()

    def run(self):
        while True:
            for function in self.functions:
                self.log('debug', 'Endless loop start')
                name = function.__name__

                try:
                    self.log('debug', 'Started %s', name)
                    function()
                    # it should have not crashed
                    self.consecutive_exceptions[name] = 0
                    self.log('info', 
                        'Task executed without raising an exception: %s', 
                        name)
                except Exception as e:
                    self.log('warning',
                        'Exception caught running %s with message: %s',
                        name, e.message)

                    exc_type, exc_value, exc_tb = sys.exc_info()
                    tb = traceback.format_exception(exc_type, exc_value, exc_tb)
                    for line in tb:
                        self.log('debug', line)

                    self.exceptions[name].append({
                        'exception': e,
                        'message': e.message,
                        'class': e.__class__.__name__,
                        'traceback': ''.join(tb),
                        'datetime': datetime.datetime.now()
                    })
                    self.consecutive_exceptions[name] += 1

                    if self.consecutive_exceptions[name] > 1:
                        self.log('error', '%s failed %s times', name, 
                            self.consecutive_exceptions[name])
                   
                    if self.consecutive_exceptions[name] >= 5 and \
                       self.consecutive_exceptions[name] % 5 == 0:
                        self.log('critical', 
                            '%s might not even work anymore: failed %s times',
                                name, 
                                self.consecutive_exceptions[name])

                        message = []
                        for e in self.exceptions[name]:
                            message.append('Message: ' + e['message'])
                            message.append('Date/Time: ' + str(e['datetime']))
                            message.append('Exception class: ' + e['class'])
                            message.append('Traceback:')
                            message.append(e['traceback'])
                            message.append('')

                        send_mail(
                            '[%s] Has been failing for %s consecutive times' % (
                                name,
                                self.consecutive_exceptions[name]
                            ),
                            "\n".join(message),
                            'critical@yourlabs.org',
                            ['jamespic@gmail.com'],
                            fail_silently=False
                        )
