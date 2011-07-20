#class Autocomplete(object):
#
#class ModelAutocomplete(object):
#    def __init__(self):
#        if hasattr(self.__class__, 'model'):
#            # allow subclasses to set the model
#            self._model = self.__class__.model
#        if hasattr(self.__class__, 'queryset'):
#            # allow subclasses to set the queryset
#            self._queryset = self.__class__.queryset
#            self._model = self._queryset.model
#
#    def get_queryset(self):
#        if self.model
#
#    def _get_queryset(self):
#        if not hasattr(self, '_queryset'):
#            if hasattr(self, 'get_queryset'):
#                self._queryset = self.get_queryset()
#        return self._queryset
#
#    def _set_queryset(self, value):
#        self._queryset = value
#        self._model = self._queryset.model
#    
#    queryset = property(get_queryset, set_queryset)
