# from django.shortcuts import render
from django.http import HttpResponse
from website.tasks import executar_backup_teste

def testar_celery(request):
    executar_backup_teste.delay()
    return HttpResponse("Tarefa Celery enviada!")