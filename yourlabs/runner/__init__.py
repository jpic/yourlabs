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
    def __init__(self, functions, logger, pidfile=None, killconcurrent=True):
        self.functions = functions
        self.logger = logger
        self.exceptions = {}
        self.consecutive_exceptions = {}
        self.killconcurrent = killconcurrent

        for function in self.functions:
            self.exceptions[function.__name__] = []
            self.consecutive_exceptions[function.__name__] = 0

        self.pidfile = pidfile
        if self.pidfile is None:
            self.pidfile = '%s/%s.pid' % (
                settings.RUN_ROOT,
                '_'.join([f.__name__ for f in self.functions])
            )
        self.concurrency_security()

    def concurrency_security(self):
        if os.path.exists(self.pidfile):
            f = open(self.pidfile, 'r')
            concurrent = f.read()
            f.close()
            if os.path.exists('/proc/%s' % concurrent):
                if self.killconcurrent:
                    print "Killing %s" % concurrent
                    os.kill(int(concurrent), signal.SIGKILL)

                    i = 0
                    while os.path.exists('/proc/%s' % concurrent):
                        time.sleep(1)
                        if i == 30:
                            print "Error: Sent SIGKILL to pid %s 30 seconds ago, in vain"
                            os._exit(-1)
                else:
                    print "Error: %s contains a pid (%s) which is still running !" % (
                        self.pidfile,
                        concurrent
                    )
                    os._exit(-1)
            else:
                os.remove(self.pidfile)

        f = open(self.pidfile, 'w')
        f.write(str(os.getpid()))
        f.flush()
        # Forcibly sync disk
        os.fsync(f.fileno())
        f.close()

    def run(self):
        while True:
            for function in self.functions:
                self.logger.debug('Endless loop start')

                try:
                    self.logger.info('Started %s' % function.__name__)
                    function()
                    # it should have not crashed
                    self.consecutive_exceptions[function.__name__] = 0
                    self.logger.info('Ended with success %s' % function.__name__)
                except Exception as e:
                    self.logger.warning(
                        'Exception caught running %s with message: %s' % (
                        function.__name__, e.message)
                    )

                    exc_type, exc_value, exc_tb = sys.exc_info()
                    tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

                    self.exceptions[function.__name__].append({
                        'exception': e,
                        'message': e.message,
                        'class': e.__class__.__name__,
                        'traceback': tb,
                        'datetime': datetime.datetime.now()
                    })
                    self.consecutive_exceptions[function.__name__] += 1

                    if self.consecutive_exceptions[function.__name__] > 1:
                        self.logger.error('%s failed %s times' % (
                                function.__name__, 
                                self.consecutive_exceptions[function.__name__]
                            )
                        )
                   
                    if self.consecutive_exceptions[function.__name__] >= 5 and self.consecutive_exceptions[function.__name__] % 5 == 0:
                        self.logger.critical('%s might not even work anymore: failed %s times' % (
                                function.__name__, 
                                self.consecutive_exceptions[function.__name__]
                            )
                        )

                        message = []
                        for e in self.exceptions[function.__name__]:
                            message.append('Message: ' + e['message'])
                            message.append('Date/Time: ' + str(e['datetime']))
                            message.append('Exception class: ' + e['class'])
                            message.append('Traceback:')
                            message.append(e['traceback'])
                            message.append('')

                        send_mail(
                            '[%s] Has been failing for %s consecutive times' % (
                                function.__name__,
                                self.consecutive_exceptions[function.__name__]
                            ),
                            "\n".join(message),
                            'critical@yourlabs.org',
                            ['jamespic@gmail.com'],
                            fail_silently=False
                        )
                
                if hasattr(function, 'runner_config'):
                    print function.runner_config
