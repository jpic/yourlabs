from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from tasks import *
from models import *

class UploadAdmin(admin.ModelAdmin):
    fields = (
        'name',
        'upload',
        'template',
    )

    list_display = (
        'name',
        'creation_user',
        'creation_datetime',
        'modification_datetime',
    )

    def load_data(modeladmin, request, queryset):
        for obj in queryset:
            upload_import.async(obj.pk)
    load_data.short_description = _('Launch data import in background')

    actions = [
        load_data,
    ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creation_user = request.user
        obj.save()


admin.site.register(Upload, UploadAdmin)

class TemplateAdmin(admin.ModelAdmin):
    exclude = (
        'creation_user',
    )

    list_display = (
        'name',
        'creation_user',
        'creation_datetime',
        'modification_datetime',
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creation_user = request.user
        obj.save()
admin.site.register(Template, TemplateAdmin)
