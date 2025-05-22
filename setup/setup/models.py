from django.db import models
from django.utils.translation import gettext_lazy as _ # usado para internacionalização das strings informar com _("")

# Create your models here.
# dicas
    # CharField == usado para input de string
    # TextField == usado para input multilite de string (ex: descrições)
    # EmailField == usado para input de email
    # choices == restringe os valores do input aos choices informados na varieavel
    # help_text == é o texto de ajuda exibido em baixo do input
    # blank=True == permite deixar o input vazio
    # null=True == permite null
    # unique == campo unico por exemplo no usuário (ex: cpf, email, username)
    # ForeignKey == relaciona essa o model atual ao model indicado
    # BooleanField == switch true ou false


# Representa cada sistema que precisa de backup.
class Projeto(models.Model):

    TIPO_PROJETO_CHOICES = [
        ('com_dump', _('Com Dump Automático')),
        ('sem_dump', _('Sem Dump')),
    ]
    TIPO_BANCO_CHOICES = [
        ('postgresql', 'PostgreSQL'),
        ('sqlite3', 'SQLite3'),
    ]
    nome = models.CharField(verbose_name=_("Nome"), max_length=100, blank=False, null=False)
    tipo_projeto = models.CharField(verbose_name=_("Tipo do projeto"), max_length=10, blank=False, null=False, choices=TIPO_PROJETO_CHOICES)
    caminho_media = models.CharField(verbose_name=_("Caminho das midias"), max_length=255, blank=False, null=False, help_text=_("Caminho para o diretório de mídia a ser backupeado."))
    caminho_docker_compose = models.CharField(verbose_name=_("Caminho do docker compose"), max_length=255, blank=True, null=True, help_text=_("Caminho para o docker-compose.yaml, se necessário."))
    tipo_banco = models.CharField(verbose_name=_("Tipo do banco"), max_length=50, blank=False, null=False, choices=TIPO_BANCO_CHOICES, default="PostgreSQL")

    class Meta:
        verbose_name = _("Projeto")
        verbose_name_plural = _("Projetos")

    def __str__(self):
        return self.nome


# Configurações detalhadas por projeto
class ConfiguracaoBackup(models.Model):
    TIPO_BACKUP_CHOICES = [
        (1, _('Com dump de banco de dados')),
        (2, _('Apenas via rsync')),
    ]

    projeto = models.ForeignKey(Projeto, verbose_name=_("Projeto"), blank=False, null=False, on_delete=models.CASCADE, related_name='configuracoes')
    tipo_backup = models.PositiveSmallIntegerField(verbose_name=_("Tipo de backup"), blank=False, null=False, choices=TIPO_BACKUP_CHOICES)

    caminho_bases_dados = models.CharField(verbose_name=_("Caminho da base de dados"), max_length=255, blank=True, null=True, help_text=_("Usado apenas ao selecionar o tipo rsync"))
    banco_host = models.CharField(verbose_name=_("Banco host"), max_length=100, blank=True, null=True)
    banco_nome = models.CharField(verbose_name=_("Banco nome"), max_length=100, blank=True, null=True)
    banco_usuario = models.CharField(verbose_name=_("Banco usuário"), max_length=100, blank=True, null=True)
    banco_senha = models.CharField(verbose_name=_("Banco senha"), max_length=100, blank=True, null=True)

    ssh_ip = models.GenericIPAddressField(verbose_name=_("IP SSH"), blank=True, null=True)
    ssh_porta = models.PositiveIntegerField(verbose_name=_("Porta SSH"), blank=True, null=True, default=22)
    destino_backup = models.CharField(verbose_name=_("Caminho destino do backup"), max_length=255, blank=True, null=True)

    manter_permissoes = models.BooleanField(verbose_name=_("Manter permissões"), default=True)
    deletar_arquivos_remotos = models.BooleanField(verbose_name=_("Deletar arquivos remotos"), default=False)

    horario_execucao = models.CharField(verbose_name=_("Horário de execução"), max_length=100, blank=True, null=True, help_text=_("Horário(s) no formato crontab ou texto"))
    dias_reter_backup = models.PositiveIntegerField(verbose_name=_("Dias retenção de backup"), default=7)

    # ignorar_arquivos = models.TextField(verbose_name=_("Arquivos a serem ignorados"), blank=True, null=True, help_text="Um por linha")

    email_notificacao = models.EmailField(verbose_name=_("E-mail (para envio de notificações)"), blank=True, null=True)
    telegram_chat_id = models.CharField(verbose_name=_("Telegram chat id (para envio de notificações)"), max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _("Configuração do backup")
        verbose_name_plural = _("Configurações dos backups")

    def __str__(self):
        return f"Backup de {self.projeto.nome} ({'Tipo ' + str(self.tipo_backup)})"


# Registra execuções manuais ou agendadas
class ExecucaoBackup(models.Model):
    STATUS_CHOICES = [
        ('sucesso', _('Sucesso')),
        ('falha', _('Falha')),
        ('executando', _('Executando')),
    ]

    configuracao = models.ForeignKey(
        ConfiguracaoBackup,
        verbose_name=_("Configuração do backup"),
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='execucoes'
    )
    data_inicio = models.DateTimeField(verbose_name=_("Data de início"), blank=False, null=False)
    data_fim = models.DateTimeField(verbose_name=_("Data de término"), blank=True, null=True)
    status = models.CharField(verbose_name=_("Status da execução"), max_length=20, blank=False, null=False, choices=STATUS_CHOICES)
    mensagem = models.TextField(verbose_name=_("Mensagem / log"), blank=True, null=True)
    duracao = models.DurationField(verbose_name=_("Duração"), blank=True, null=True)

    class Meta:
        verbose_name = _("Execução do backup")
        verbose_name_plural = _("Execuções dos backups")
        ordering = ['-data_inicio']

    def __str__(self):
        return f"{self.configuracao.projeto.nome} - {self.get_status_display()} ({self.data_inicio.strftime('%Y-%m-%d %H:%M')})"


# Define como e para onde notificar em caso de erro/sucesso
class Notificacao(models.Model):
    MEIO_CHOICES = [
        ('email', _('E-mail')),
        ('telegram', _('Telegram')),
    ]

    configuracao = models.ForeignKey(ConfiguracaoBackup, verbose_name=_("Configuração do backup"), on_delete=models.CASCADE, blank=False, null=False, related_name='notificacoes')
    meio = models.CharField(verbose_name=_("Meio de notificação"), max_length=20, blank=False, null=False, choices=MEIO_CHOICES)
    ativo = models.BooleanField(verbose_name=_("Ativo"), default=True)
    enviar_sucesso = models.BooleanField(verbose_name=_("Enviar em caso de sucesso"), default=False)
    enviar_falha = models.BooleanField(verbose_name=_("Enviar em caso de falha"), default=True)
    destino_email = models.EmailField(verbose_name=_("E-mail de destino"), blank=True, null=True)
    telegram_chat_id = models.CharField(verbose_name=_("Chat ID do Telegram"), max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _("Notificação")
        verbose_name_plural = _("Notificações")

    def __str__(self):
        return f"{self.get_meio_display()} - {self.configuracao.projeto.nome}"


class AgendamentoBackup(models.Model):
    configuracao = models.ForeignKey(ConfiguracaoBackup, verbose_name=_("Configuração do backup"), on_delete=models.CASCADE, blank=False, null=False, related_name='agendamentos')
    horario = models.CharField(verbose_name=_("Horário de execução"), max_length=100, blank=False, null=False, help_text=_("Pode ser um horário fixo (ex: 03:00) ou expressão crontab (ex: 0 3 * * *)."))
    ativo = models.BooleanField(verbose_name=_("Ativo"), default=True)

    class Meta:
        verbose_name = _("Agendamento do backup")
        verbose_name_plural = _("Agendamentos dos backups")

    def __str__(self):
        return f"{self.configuracao.projeto.nome} - {self.horario}"


# Logs técnicos de cada execução
class LogExecucaoDetalhado(models.Model):
    TIPO_CHOICES=[
        ('info', _('Informação')),
        ('warning', _('Aviso')),
        ('error', _('Erro')),
        ('stdout', _('Saída padrão')),
        ('stderr', _('Saída de erro')),
    ]

    execucao = models.ForeignKey(ExecucaoBackup, verbose_name=_("Execução do backup"), on_delete=models.CASCADE, blank=False, null=False, related_name='logs_detalhados')
    timestamp = models.DateTimeField(verbose_name=_("Data e hora"), auto_now_add=True)
    tipo = models.CharField(verbose_name=_("Tipo"), max_length=20, choices=TIPO_CHOICES, blank=False, null=False)
    mensagem = models.TextField(verbose_name=_("Mensagem"), blank=False, null=False)

    class Meta:
        verbose_name = _("Log detalhado da execução")
        verbose_name_plural = _("Logs detalhados das execuções")

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.get_tipo_display()}"
    

# Caminhos específicos a serem ignorados (substitui o campo TextField anterior)
class ArquivoIgnorado(models.Model):
    configuracao = models.ForeignKey(ConfiguracaoBackup, verbose_name=_("Configuração do backup"), on_delete=models.CASCADE, blank=False, null=False, related_name='arquivos_ignorados')
    caminho = models.CharField(verbose_name=_("Caminho a ser ignorado"), max_length=255, blank=False, null=False, help_text=_("Informe o caminho do arquivo ou pasta a ser ignorado."))

    class Meta:
        verbose_name = _("Arquivo/Pasta ignorado(a)")
        verbose_name_plural = _("Arquivos/Pastas ignorados(as)")

    def __str__(self):
        return self.caminho