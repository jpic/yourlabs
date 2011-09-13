import os
import logging
import time

class Daemon(object):
    def __init__(self, pidfile, logger=None, allow_concurrent=False):
        self.pidfile = pidfile
        self.logger = logger
        self.allow_concurrent = allow_concurrent

    def log(self, level, message, *args):
        if self.logger is None:
            print level, self.name, self.message % args
        elif isinstance(self.logger, str):
            self.logger = logging.getLogger(self.logger)
        level = getattr(logging, level.upper())
        self.logger.log(level, message % args)
    
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
                self.log('debug', 'Could not find /proc/%s, wiping pidfile %s', 
                        concurrent, self.pidfile)
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
        self.log('debug', 'Wrote pidfile %s', self.pidfile)
