import os
from celery import Celery
from celery.schedules import crontab

# Define o módulo de settings do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

# Criação da instância do Celery
app = Celery('setup')

# Configurações: busca por CELERY_* no Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre automaticamente tarefas em todos os apps registrados no Django
app.autodiscover_tasks()

# Agenda as tarefas com o Celery Beat no horario definido no crontab
app.conf.beat_schedule = {
    'limpar-backups-antigos-diariamente': {
        'task': 'setup.tasks.limpar_backups_antigos',
        'schedule': crontab(hour=3, minute=0),  # todos os dias às 3h da manhã
    },
}

# Task de debug (útil para testar se o celery está rodando corretamente)
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')