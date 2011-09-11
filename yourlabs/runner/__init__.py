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
