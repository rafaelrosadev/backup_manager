from celery import shared_task
import logging

from setup.setup.models import ConfiguracaoBackup

logger = logging.getLogger(__name__)

@shared_task
def executar_backup_teste(configuracao_id):
    try:
        config = ConfiguracaoBackup.objects.get(pk=configuracao_id)

        logger.info(f"Iniciando o backup para: {config.projeto.nome}")
        
        # adicionar a logica do backup dentro dos ifs
        if config.tipo_backup == 1:
            logger.info(f"Backup com dump selecionado")
        elif config.tipo_backup == 2:
            logger.info(f"Backup via rsync selecionado")

        logger.info(f"Backup finalizado para: {config.projeto.nome}")
        return f"Backup finalizado para: {config.projeto.nome}"
    except ConfiguracaoBackup.DoesNotExist:
        logger.info(f"Configuração ID {configuracao_id} não encontrada")
        return f"Configuração ID {configuracao_id} não encontrada"
    except Exception as e:
        logger.exception("Erro ao executar backup")
        return f"Erro ao executar backup: {str(e)}"
