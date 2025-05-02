from celery import shared_task

@shared_task
def executar_backup_teste():
    print("Backup executado com sucesso.")
    return "Backup OK"
