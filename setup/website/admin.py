from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.http import HttpResponseRedirect
from unfold.forms import AdminPasswordChangeForm
from unfold.forms import UserChangeForm
from unfold.forms import UserCreationForm
from unfold.admin import StackedInline
from unfold.admin import TabularInline
from unfold.admin import ModelAdmin
from django.urls import path
from django.utils.html import format_html
from setup.tasks import executar_backup_teste, executar_backup
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from setup.models import AgendamentoBackup, ArquivoIgnorado, ConfiguracaoBackup, ExecucaoBackup, LogExecucaoDetalhado, Notificacao, Projeto
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule, ClockedSchedule
import json

# Desregistrando User e Group padrões para usar com Unfold
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class AgendamentoBackupInline(TabularInline):
    model = AgendamentoBackup
    extra = 0
    fields = ("horario", "ativo")
    show_change_link = True
    classes = ["collapse"]


class ArquivoIgnoradoInline(TabularInline):
    model = ArquivoIgnorado
    extra = 1
    classes = ["collapse"]


class ConfiguracaoBackupInline(StackedInline):
    model = ConfiguracaoBackup
    extra = 0
    show_change_link = True
    classes = ["collapse"]


@admin.register(Projeto)
class ProjetoAdmin(ModelAdmin):
    search_fields = ['nome']
    list_display = ['nome', 'tipo_projeto', 'tipo_banco']
    inlines = [ConfiguracaoBackupInline]


class ArquivoIgnoradoInline(TabularInline):
    model = ArquivoIgnorado
    extra = 1
    classes = ["collapse"]


@admin.register(ConfiguracaoBackup)
class ConfiguracaoBackupAdmin(ModelAdmin):
    inlines = [ArquivoIgnoradoInline, AgendamentoBackupInline]
    list_filter = ['tipo_backup']
    search_fields = ['projeto__nome']
    list_display = ('projeto', 'get_tipo_backup_display', 'destino_backup', 'horario_execucao', 'executar_backup_button', 'testar_notificacao_button')
    actions = ['executar_backup', 'testar_notificacao']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:config_id>/executar-backup/',
                self.admin_site.admin_view(self.executar_backup_view),
                name='executar-backup',
            ),
            path(
                '<int:config_id>/testar-notificacao/',
                self.admin_site.admin_view(self.testar_notificacao_view),
                name='testar-notificacao',
            ),
        ]
        return custom_urls + urls

    def executar_backup_button(self, obj):
        return format_html(
            '<a class="button" href="{}">▶️ {}</a>',
            f'{obj.id}/executar-backup/',
            _('Executar agora'),
        )
    executar_backup_button.short_description = _('Executar Backup')
    executar_backup_button.allow_tags = True

    def executar_backup_view(self, request, config_id):
        try:
            config = ConfiguracaoBackup.objects.get(pk=config_id)
            # executar_backup_teste.delay(config.id)
            executar_backup.delay(config.id)
            self.message_user(request, _(f"Backup inicaiado para: {config.projeto.nome}"), messages.SUCCESS)
        except Exception as e:
            self.message_user(request, _(f"Erro ao iniciar o backup: {str(e)}"), messages.ERROR)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

    def testar_notificacao_button(self, obj):
        return format_html(
            '<a class="button" href="{}">📬 {}</a>',
            f'{obj.id}/testar-notificacao/',
            _('Testar Notificação'),
        )
    testar_notificacao_button.short_description = _('Testar notificacao')
    testar_notificacao_button.allow_tags = True

    def testar_notificacao_view(self, request, config_id):
        from setup.tasks import testar_notificacoes

        try:
            resultados = testar_notificacoes(config_id)
            for msg in resultados:
                self.message_user(request, msg, messages.SUCCESS if "✅" in msg or "Email" in msg or "Telegram" in msg else messages.WARNING)
        except Exception as e:
            self.message_user(request, _(f"Erro ao testar notificações: {str(e)}"), messages.ERROR)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
    

class LogExecucaoDetalhadoInline(admin.TabularInline):
    model = LogExecucaoDetalhado
    extra = 0
    readonly_fields = ('timestamp', 'tipo', 'mensagem')
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExecucaoBackup)
class ExecucaoBackupAdmin(ModelAdmin):
    list_display = (
        'projeto',
        'configuracao',
        'data_inicio',
        'data_fim',
        'status_colorido',
        'duracao',
    )
    list_filter = ('status', 'data_inicio')
    search_fields = ('configuracao__projeto__nome', 'mensagem')
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio',)
    list_select_related = ('configuracao__projeto',)
    inlines = [LogExecucaoDetalhadoInline]

    def projeto(self, obj):
        return obj.configuracao.projeto.nome
    projeto.short_description = "Projeto"

    def status_colorido(self, obj):
        cores = {
            'sucesso': 'green',
            'falha': 'red',
            'executando': 'orange',
        }
        cor = cores.get(obj.status, 'black')
        return format_html(
            '<strong style="color: {};">{}</strong>',
            cor,
            obj.get_status_display()
        )
    status_colorido.short_description = "Status"

    def has_add_permission(self, request):
        # Impede a adição manual via admin (se só forem criadas por script/tarefa)
        return False


@admin.register(Notificacao)
class NotificacaoAdmin(ModelAdmin):
    list_display = ('configuracao', 'meio', 'ativo', 'enviar_sucesso', 'enviar_falha')
    list_filter = ('meio', 'ativo')
    search_fields = ('configuracao__projeto__nome', 'destino_email', 'telegram_chat_id')


@admin.register(AgendamentoBackup)
class AgendamentoBackupAdmin(ModelAdmin):
    list_display = ('configuracao', 'horario_formatado', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('configuracao__projeto__nome', 'horario')
    list_editable = ('ativo',)

    def horario_formatado(self, obj):
        return obj.horario.strftime("%d/%m/%Y %H:%M")
    horario_formatado.short_description = "Horário"


@admin.register(LogExecucaoDetalhado)
class LogExecucaoDetalhadoAdmin(ModelAdmin):
    list_display = ('execucao', 'timestamp', 'tipo', 'mensagem_curta')
    list_filter = ('tipo', 'timestamp')
    search_fields = ('mensagem',)
    date_hierarchy = 'timestamp'

    def mensagem_curta(self, obj):
        return obj.mensagem[:60] + "..." if len(obj.mensagem) > 60 else obj.mensagem
    mensagem_curta.short_description = "Mensagem"


admin.site.unregister(PeriodicTask)
@admin.register(PeriodicTask)
class PeriodicTaskAdmin(ModelAdmin):
    list_display = ('name', 'task', 'get_projeto', 'get_configuracao', 'get_crontab', 'enabled', 'last_run_at', 'total_run_count', 'date_changed',)
    list_filter = ('enabled', 'task')
    search_fields = ('name', 'task')
    ordering = ('name',)

    def get_crontab(self, obj):
        return str(obj.crontab) if obj.crontab else "-"
    get_crontab.short_description = "Agendamento"

    def get_configuracao(self, obj):
        configuracao = self._get_configuracao(obj)
        return f"{configuracao.id}" if configuracao else "-"
    get_configuracao.short_description = "ID Configuração"

    def get_projeto(self, obj):
        configuracao = self._get_configuracao(obj)
        return configuracao.projeto.nome if configuracao else "-"
    get_projeto.short_description = "Projeto"

    def _get_configuracao(self, obj):
        try:
            args = json.loads(obj.args)
            configuracao_id = args[0] if args else None
            return ConfiguracaoBackup.objects.select_related("projeto").filter(pk=configuracao_id).first()
        except Exception:
            return None


admin.site.unregister(CrontabSchedule)
@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(ModelAdmin):
    list_display = ('expressao_cron','minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')
    search_fields = ('minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')

    def expressao_cron(self, obj):
        return f"{obj.minute} {obj.hour} {obj.day_of_month} {obj.month_of_year} {obj.day_of_week}"
    expressao_cron.short_description = "Expressão Cron"


admin.site.unregister(IntervalSchedule)
@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):
    list_display = ('every', 'period')
    search_fields = ('every', 'period')


admin.site.unregister(ClockedSchedule)
@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(ModelAdmin):
    list_display = ('clocked_time',)
    search_fields = ('clocked_time',)
    ordering = ('-clocked_time',)