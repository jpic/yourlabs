from django_ztask.decorators import task

from models import *

@task()
def upload_import(upload_pk):
    upload = Upload.objects.get(pk=upload_pk)
    upload.load()
