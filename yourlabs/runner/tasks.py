class Divide(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def divide(self):
        return self.x / self.y

def divide_by_zero():
    divide = Divide(1, 0)
    divide.divide()
