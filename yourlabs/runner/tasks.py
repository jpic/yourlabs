from datetime import timedelta as td

from yourlabs import runner

class Divide(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def divide(self):
        return self.x / self.y

# always fails, has traceback
@runner.task(fail_cooldown=td(seconds=1), non_recoverable_downtime=td(seconds=3))
def divide_by_zero():
    divide = Divide(1, 0)
    divide.divide()
