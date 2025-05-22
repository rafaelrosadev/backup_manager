from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from setup.models import AgendamentoBackup
import json

@receiver(post_save, sender=AgendamentoBackup)
def criar_ou_atualizar_periodic_task(sender, instance, **kwargs):
    config = instance.configuracao
    projeto = config.projeto

    # Cria ou obtém o agendamento do tipo crontab
    horario = instance.horario
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=str(horario.minute),
        hour=str(horario.hour),
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone=timezone.get_current_timezone_name()
    )

    task_name = f"Backup | {projeto.nome} | {config.id} | {horario.strftime('%H:%M')}"

    PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            "task": "website.tasks.executar_backup_teste",
            "crontab": crontab,
            "args": json.dumps([config.id]),
            "enabled": instance.ativo,
        }
    )


@receiver(post_delete, sender=AgendamentoBackup)
def deletar_periodic_task(sender, instance, **kwargs):
    config = instance.configuracao
    projeto = config.projeto
    horario = instance.horario

    task_name = f"Backup | {projeto.nome} | {config.id} | {horario.strftime('%H:%M')}"
    PeriodicTask.objects.filter(name=task_name).delete()