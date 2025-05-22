# from django.shortcuts import render
from django.http import HttpResponse
from setup.tasks import executar_backup_teste

def testar_celery(request, configuracao_id):
    executar_backup_teste.delay(configuracao_id=configuracao_id)
    return HttpResponse(f"Tarefa Celery iniciada para Configuração #{configuracao_id}")