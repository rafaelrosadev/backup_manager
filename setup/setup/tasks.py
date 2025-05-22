import os
import re
import yaml
import shutil
import logging
import subprocess
from celery import shared_task
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta, datetime
from setup.models import ConfiguracaoBackup, ExecucaoBackup, LogExecucaoDetalhado, ArquivoIgnorado, Notificacao
from website.utils.notificacao import enviar_email, enviar_telegram

logger = logging.getLogger(__name__)

@shared_task
def executar_backup_teste(configuracao_id):
    try:
        config = ConfiguracaoBackup.objects.get(pk=configuracao_id)

        if not config.destino_backup:
            raise ValueError(f"Destino de backup não definido para a configuração {configuracao_id}")
        
        if not config.origem_arquivos:
            raise ValueError(f"Origem de arquivos não definida para a configuração {configuracao_id}")
        
        projeto = config.projeto
        timestap = now().strftime("%Y%m%d_%H%M%S")

        destino = os.path.join(config.destino_backup, f"{projeto.nome}_{timestap}")
        os.makedirs(destino, exist_ok=True)

        logger.info(f"Iniciando o backup do projeto: {projeto.nome}")
        
        if config.tipo_backup == 1:
            logger.info(f"Backup com dump selecionado")
            # Backup com dump do banco + rsync dos arquivos
            executar_pg_dump(config, destino)
            executar_rsync(config, destino)

        elif config.tipo_backup == 2:
            logger.info(f"Backup via rsync selecionado")
            # Apenas rsync
            executar_rsync(config, destino)

        logger.info(f"Backup finalizado para: {projeto.nome}")
        return f"Backup finalizado com sucesso para: {projeto.nome}"
    except ConfiguracaoBackup.DoesNotExist:
        logger.info(f"Configuração ID {configuracao_id} não encontrada")
        return f"Configuração ID {configuracao_id} não encontrada"
    except Exception as e:
        logger.exception("Erro ao executar backup")
        return f"Erro ao executar backup: {str(e)}"
    

def ler_dados_banco_docker_compose(caminho_yaml):
    try:
        with open(caminho_yaml, 'r') as f:
            conteudo = yaml.safe_load(f)

        db_service = conteudo.get('services', {}).get('db', {})
        environment = db_service.get('environment', [])
        env_dict = {}
        if isinstance(environment, list):
            for var in environment:
                if '=' in var:
                    k, v = var.split('=', 1)
                    env_dict[k] = v
        elif isinstance(environment, dict):
            env_dict = environment

        host = 'localhost'  # padrão
        user = env_dict.get('POSTGRES_USER', '')
        password = env_dict.get('POSTGRES_PASSWORD', '')
        dbname = env_dict.get('POSTGRES_DB', '')

        return {
            'host': host,
            'user': user,
            'password': password,
            'dbname': dbname
        }
    except Exception as e:
        raise Exception(f"Erro lendo docker-compose.yaml: {str(e)}")


def executar_pg_dump(config, destino):
    projeto = config.projeto
    nome_arquivo = os.path.join(destino, f"{projeto.nome}_dump.sql")

    comando = [
        "pg_dump",
        "-U", config.usuario_banco,
        "-h", config.host_banco,
        "-p", str(config.porta_banco),
        "-d", config.nome_banco,
        "-F", "c", # formato custom
        "-f", nome_arquivo
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = config.senha_banco

    logger.info(f"Executando pg_dump para {projeto.nome}")
    try:
        subprocess.run(comando, check=True, env=env)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar pg_dump: {e.stderr}")
        raise

def executar_rsync(config, destino):
    caminho_origem = config.origem_arquivos.rstrip("/") + "/"
    caminho_destino = os.path.join(destino, "arquivos")

    os.makedirs(caminho_destino, exist_ok=True)

    comando = [
        "rsync",
        "-av",
        caminho_origem,
        caminho_destino,
    ]

    logger.info(f"Executando rsync de {caminho_origem} para {caminho_destino}")

    try:
        subprocess.run(comando, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar rsync: {e.stderr}")
        raise


@shared_task(bind=True)
def executar_backup(self, config_id):
    execucao = None
    try:
        config = ConfiguracaoBackup.objects.select_related('projeto').get(pk=config_id)

        # Criar registro de execução
        execucao = ExecucaoBackup.objects.create(
            configuracao=config,
            data_inicio=now(),
            status='executando',
            mensagem='Backup iniciado'
        )

        projeto = config.projeto
        origem = projeto.diretorio_origem
        destino = config.destino_backup
        ignorados = ArquivoIgnorado.objects.filter(configuracao=config).values_list('caminho', flat=True)

        logs = []

        def log(tipo, msg):
            LogExecucaoDetalhado.objects.create(execucao=execucao, tipo=tipo, mensagem=msg)
            logs.append(f"[{tipo}] {msg}")

        log("INFO", f"Iniciando backup do projeto '{projeto.nome}'")

        if not os.path.exists(origem):
            raise Exception(f"Diretório de origem não encontrado: {origem}")

        if not os.path.exists(destino):
            os.makedirs(destino)
            log("INFO", f"Diretório de destino criado: {destino}")

        for root, dirs, files in os.walk(origem):
            rel_path = os.path.relpath(root, origem)

            if any(rel_path.startswith(ign) for ign in ignorados):
                log("IGNORADO", f"Pasta ignorada: {rel_path}")
                continue

            dest_dir = os.path.join(destino, rel_path)
            os.makedirs(dest_dir, exist_ok=True)

            for file in files:
                file_rel_path = os.path.join(rel_path, file)
                if any(file_rel_path.startswith(ign) for ign in ignorados):
                    log("IGNORADO", f"Arquivo ignorado: {file_rel_path}")
                    continue

                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_dir, file)

                shutil.copy2(src_file, dest_file)
                log("COPIA", f"Copiado: {file_rel_path}")
        
        # Sucesso
        execucao.status = 'sucesso'
        execucao.data_fim = now()
        execucao.mensagem = 'Backup concluído com sucesso'
        execucao.save()
        notificar_resultado(config, execucao.status, 'Backup concluído com sucesso')

        # Log detalhado
        LogExecucaoDetalhado.objects.create(
            execucao=execucao,
            tipo='info',
            mensagem='Backup executado com sucesso',
            timestamp=now()
        )

        return "Backup concluído"

    except Exception as e:
        if execucao:
            execucao.status = 'falha'
            execucao.data_fim = now()
            execucao.mensagem = str(e)
            execucao.save()
            notificar_resultado(config, execucao.status, 'Falha ao executar o backup')

            LogExecucaoDetalhado.objects.create(
                execucao=execucao,
                tipo='erro',
                mensagem=str(e),
                timestamp=now()
            )

        raise self.retry(exc=e, countdown=60, max_retries=3)


def notificar_resultado(config, status, mensagem_final):
    notificacoes = Notificacao.objects.filter(configuracao=config, ativo=True)
    for n in notificacoes:
        if (status == 'sucesso' and not n.enviar_sucesso) or (status == 'falha' and not n.enviar_falha):
            continue

        if n.meio == 'email' and n.destino_email:
            enviar_email(n.destino_email, f"[Backup] Resultado: {status.upper()}", mensagem_final)
        elif n.meio == 'telegram' and n.telegram_chat_id:
            enviar_telegram(n.telegram_chat_id, mensagem_final)


@shared_task
def limpar_backups_antigos():
    configuracoes = ConfiguracaoBackup.objects.exclude(destino_backup__isnull=True).exclude(destino_backup__exact='')

    for config in configuracoes:
        destino = config.destino_backup
        dias_a_manter = config.dias_reter_backup or 7 # 7 dias é o padrão definido
        data_limite = now() - timedelta(days=dias_a_manter)

        if not os.path.exists(destino):
            continue

        try:
            for pasta in os.listdir(destino):
                caminho_completo = os.path.join(destino, pasta)

                if not os.path.exists(caminho_completo):
                    continue
                
                # Tenta extrair a data do nome da pasta: NOME_PROJETO_YYYYMMDD_HHMMSS
                match = re.search(r'_(\d{8}_\d{6})$', pasta)
                if not match:
                    continue

                data_str = match.group(1)
                try:
                    data_backup = datetime.strptime(data_str, "%Y%m%d_%H%M%S")
                except ValueError:
                    continue

                # Verifica se é mais antigo do que a data limite
                if timezone.make_aware(data_backup) < data_limite:
                    shutil.rmtree(caminho_completo)
                    logger.info(f"Backup antigo removido: {caminho_completo}")

        except Exception as e:
            logger.exception(f"Erro ao limpar backups para a config id {config.id}: {str(e)}")