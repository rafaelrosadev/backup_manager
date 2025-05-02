import os
from celery import Celery

# Define o settings padrão do Django para configuração do celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

app = Celery('setup')

# Carrega configurações do Django e busca por tarefas em todos os apps
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')