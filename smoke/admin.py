from django.contrib import admin

class BugsAdmin(admin.ModelAdmin):
    list_display = ('url', 'creation_datetime')
    list_filter = ('creation_datetime',)

