from django import http
from django.views.decorators.csrf import csrf_exempt

from models import *
from utils import *

@csrf_exempt
def parser_form(request):
    template = Template.objects.get(pk=request.POST['pk'])
    
    if template.parser:
        parser = template.parser
    else:
        parser_class = get_class(request.POST.get('parser_class'))
        parser = template.parser = parser_class()
    
    response = parser.configuration_form(request)
    template.save()
    return response
