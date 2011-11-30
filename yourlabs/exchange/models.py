from django.db import models
from django.utils.translation import ugettext_lazy as _

from picklefield.fields import PickledObjectField

from settings import *

class Upload(models.Model):
    name = models.CharField(max_length=100, unique=True)
    creation_datetime = models.DateTimeField(auto_now_add=True)
    modification_datetime = models.DateTimeField(auto_now=True)
    creation_user = models.ForeignKey('auth.user')
    upload = models.FileField(upload_to='csv')
    template = models.ForeignKey('Template', null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def load(self):
        self.template.parser.load(self)

class Template(models.Model):
    name = models.CharField(max_length=100, unique=True)
    creation_datetime = models.DateTimeField(auto_now_add=True)
    modification_datetime = models.DateTimeField(auto_now=True)
    creation_user = models.ForeignKey('auth.user')
    
    contenttype = models.ForeignKey('contenttypes.contenttype', 
        verbose_name=_('database table'), 
        help_text=_('you are about to configure a form preset for this type'))
    upload_sample = models.TextField(
        help_text=_('A sample upload for which this template should work'))
    parser_class = models.CharField(max_length=150, 
        choices=EXCHANGE_PARSER_CHOICES)
    parser = PickledObjectField(null=True, blank=True)
    
    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name
