from django.contrib import admin

from models import *

class FailUrlAdmin(admin.ModelAdmin):
    list_display = ('url', 'creation_datetime')
    list_filter = ('creation_datetime',)

admin.site.register(FailUrl, FailUrlAdmin)
