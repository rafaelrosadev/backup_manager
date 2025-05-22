import requests

from setup.models import ConfiguracaoBackup, Notificacao

def enviar_email(destinatario, assunto, mensagem):
    try:
        response = requests.post(
            'https://email.besoft.com.br/api/v1/email/?sync=true',
            headers={'Authorization': 'Bearer TOKEN_API_EMAIL'},
            json={
                "para": [{
                        "email": destinatario,
                        "nome": destinatario,
                    }
                ],
                "de": "suporte@besoft.com.br",
                "denome": "BeSoft",
                "responderpara": "suporte@besoft.com.br",
                "responderparanome": "BeSoft",
                "assunto": assunto,
                "conteudo": mensagem
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False


def enviar_telegram(chat_id, mensagem):
    token_bot = "BOT_TOKEN_TELEGRAM"
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token_bot}/sendMessage",
            params={
                "chat_id": chat_id,
                "message_thread_id": 1,
                "text": mensagem
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Erro ao enviar telegram: {e}")
        return False
    
def testar_notificacoes(config_id):
    try:
        config = ConfiguracaoBackup.objects.get(pk=config_id)
        notificacoes = Notificacao.objects.filter(configuracao=config, ativo=True)

        sucesso = []

        for n in notificacoes:
            mensagem_teste = f"✅ TESTE DE NOTIFICAÇÃO - Projeto: {config.projeto.nome}"
            assunto_email = "[TESTE] Notificação de Backup"

            if n.meio == 'email' and n.destino_email:
                enviado = enviar_email(n.destino_email, assunto_email, mensagem_teste)
                sucesso.append(f"Email enviado para {n.destino_email}: {enviado}")

            elif n.meio == 'telegram' and n.telegram_chat_id:
                enviado = enviar_telegram(n.telegram_chat_id, mensagem_teste)
                sucesso.append(f"Telegram enviado para {n.telegram_chat_id}: {enviado}")
        
        return sucesso or ["Nenhuma notificação ativa configurada."]
    
    except ConfiguracaoBackup.DoesNotExist:
        return ["❌ Configuração de backup não encontrada."]
    except Exception as e:
        return [f"❌ Erro ao testar notificações: {str(e)}"]