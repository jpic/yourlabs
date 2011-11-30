import csv

from django import shortcuts
from django import http

from models import *

class CsvParser(object):
    def __init__(self):
        self.actions = None

    def load(self, upload):
        model_class = upload.template.contenttype.model_class()
        
        f = open(upload.upload.path, 'rb')
        reader = csv.reader(f)

        for row in reader:
            i = 0
            model = model_class()

            for action in self.actions:
                value = row[i]
                self.execute(model, action, value)
                i += 1

            model.save()

        f.close()

    def execute(self, model, action, value):
        setattr(model, action, value)

    def configuration_form(self, request):
        reader = unicode_csv_reader(request.POST['upload_sample'].split("\n"),
            skipinitialspace=True)
        rows = [row for row in reader]

        if '_parser_action' in request.POST.keys():
            self.actions = request.POST.getlist('_parser_action')
        elif self.actions is None:
            self.actions = ['' for x in rows[0]]

        context = {
            'rows': rows,
            'actions': self.actions,
        }

        return shortcuts.render(request, 
            'exchange/parsers/csv_parser/configuration_form.html',
            context)

# from http://docs.python.org/library/csv.html#csv-examples
def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')
