from django.views.generic.list import ListView

from bet.models import *

class AutocompleteView(ListView):
    template_name_suffix = '_autocomplete'
    queryset = Bet.objects.all()
