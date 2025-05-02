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
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from setup.models import AgendamentoBackup, ArquivoIgnorado, ConfiguracaoBackup, ExecucaoBackup, LogExecucaoDetalhado, Notificacao, Projeto

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


@admin.register(Projeto)
class ProjetoAdmin(ModelAdmin):
    search_fields = ['nome']
    list_display = ['nome', 'tipo_projeto', 'tipo_banco']


class ArquivoIgnoradoInline(TabularInline):
    model = ArquivoIgnorado
    extra = 1
    classes = ["collapse"]


@admin.register(ConfiguracaoBackup)
class ConfiguracaoBackupAdmin(ModelAdmin):
    inlines = [ArquivoIgnoradoInline]
    list_filter = ['tipo_backup']
    search_fields = ['projeto__nome']
    list_display = ('projeto', 'get_tipo_backup_display', 'destino_backup', 'horario_execucao', 'executar_backup_button')
    actions = ['executar_backup']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:config_id>/executar-backup/',
                self.admin_site.admin_view(self.executar_backup_view),
                name='executar-backup',
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

            # Implementar a lógica do backup
            print(f"Executando backup manual para: {config.projeto.nome}")

            self.message_user(request, _(f"Backup executado com sucesso para: {config.projeto.nome}"), messages.SUCCESS)
        except Exception as e:
            self.message_user(request, _(f"Erro ao executar o backup: {str(e)}"), messages.ERROR)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))


@admin.register(ExecucaoBackup)
class ExecucaoBackupAdmin(ModelAdmin):
    list_display = (
        'projeto',
        'configuracao',
        'data_inicio',
        'data_fim',
        'status',
        'duracao',
    )
    list_filter = ('status', 'data_inicio')
    search_fields = ('configuracao__projeto__nome', 'mensagem')
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio',)
    list_select_related = ('configuracao__projeto',)

    def projeto(self, obj):
        return obj.configuracao.projeto.nome
    projeto.short_description = "Projeto"


@admin.register(Notificacao)
class NotificacaoAdmin(ModelAdmin):
    list_display = ('configuracao', 'meio', 'ativo', 'enviar_sucesso', 'enviar_falha')
    list_filter = ('meio', 'ativo')
    search_fields = ('configuracao__projeto__nome', 'destino_email', 'telegram_chat_id')


@admin.register(AgendamentoBackup)
class AgendamentoBackupAdmin(ModelAdmin):
    list_display = ('configuracao', 'horario', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('configuracao__projeto__nome', 'horario')


@admin.register(LogExecucaoDetalhado)
class LogExecucaoDetalhadoAdmin(ModelAdmin):
    list_display = ('execucao', 'timestamp', 'tipo', 'mensagem_curta')
    list_filter = ('tipo', 'timestamp')
    search_fields = ('mensagem',)
    date_hierarchy = 'timestamp'

    def mensagem_curta(self, obj):
        return obj.mensagem[:60] + "..." if len(obj.mensagem) > 60 else obj.mensagem
    mensagem_curta.short_description = "Mensagem"