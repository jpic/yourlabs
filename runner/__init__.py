import datetime

from django.core.management import call_command

from gsm.management.commands.gsm_sync import Command as GsmSyncCommand

class Runner(object):
    def __init__(self, functions, logger):
        self.functions = functions
        self.logger = logger
        self.exceptions = {}
        self.consecutive_exceptions = {}

        for function in self.functions:
            self.exceptions[function.__name__] = []
            self.consecutive_exceptions[function.__name__] = 0

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

                    self.exceptions[function.__name__].append({
                        'exception': e,
                        'datetime': datetime.datetime.now()
                    })
                    self.consecutive_exceptions[function.__name__] += 1

                    if self.consecutive_exceptions[function.__name__] > 1:
                        self.logger.error('%s failed %s times' % (
                                function.__name__, 
                                self.consecutive_exceptions[function.__name__]
                            )
                        )
                   
                    if self.consecutive_exceptions[function.__name__] > 5:
                         self.logger.critical('%s might not even work anymore: failed %s times' % (
                                function.__name__, 
                                self.consecutive_exceptions[function.__name__]
                            )
                        )
