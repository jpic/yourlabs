from django.utils.importlib import import_module

def get_class(name):
    class_name = name.split('.')[-1]
    module_name = '.'.join(name.split('.')[:-1])
    mod = import_module(module_name)
    cls = getattr(mod, class_name)
    return cls

