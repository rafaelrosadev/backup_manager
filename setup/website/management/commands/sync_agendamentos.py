from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from setup.models import AgendamentoBackup
import json


class Command(BaseCommand):
    # Sincroniza agendamentos do modelo AgendamentoBackup com django-celery-beat

    def handle(self, *args, **kwargs):
        for agendamento in AgendamentoBackup.objects.filter(ativo=True):
            config = agendamento.configuracao
            projeto = config.projeto
            config_id = config.id
            nome_tarefa = f"Backup: {projeto.nome} ({agendamento.horario})"

            partes = agendamento.horario.strip().split()
            if len(partes) == 5:
                # Formato crontab
                minute, hour, day_of_month, month_of_year, day_of_week = partes
            elif len(partes) == 1 and ":" in partes[0]:
                # Formato horário fixo ex: 03:00
                try:
                    hour, minute = partes[0].split(":")
                    day_of_month = "*"
                    month_of_year = "*"
                    day_of_week = "*"
                except ValueError:
                    self.stdout.write(self.style.WARNING(f"Formato de hora inválido: {agendamento.horario}"))
                    continue
            else:
                self.stdout.write(self.style.WARNING(f"Formato de agendamento inválido: {agendamento.horario}"))
                continue

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week,
            )

            task, created = PeriodicTask.objects.update_or_create(
                name=nome_tarefa,
                defaults={
                    "task": "setup.tasks.executar_backup_teste",  # ajuste se sua task estiver em outro módulo
                    "crontab": schedule,
                    "args": json.dumps([config_id]),
                    "enabled": True,
                }
            )

            status = "Criado" if created else "Atualizado"
            self.stdout.write(self.style.SUCCESS(f"{status}: {nome_tarefa}"))

        self.stdout.write(self.style.SUCCESS("Todos os agendamentos foram sincronizados."))