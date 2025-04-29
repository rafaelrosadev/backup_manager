from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.forms import AdminPasswordChangeForm
from unfold.forms import UserChangeForm
from unfold.forms import UserCreationForm
from unfold.admin import StackedInline
from unfold.admin import TabularInline
from unfold.admin import ModelAdmin

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
    list_display = ('projeto', 'tipo_backup_display', 'destino_backup', 'horario_execucao')

    def tipo_backup_display(self, obj):
        return obj.get_tipo_backup_display()
    tipo_backup_display.short_description = "Tipo de Backup"


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