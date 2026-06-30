# Textos do menu interativo — cada constante representa uma tela do fluxo do bot
MENU_PRINCIPAL = """╔══════════════════════╗
║       *ATENDIMENTO*     ║
╚══════════════════════╝

Olá! Como posso ajudar?

1️⃣ *Informações*
2️⃣ *Agendar horário*
3️⃣ *Falar com o Bot* 🤖
4️⃣ *Falar com atendente*
5️⃣ *Sair*

Digite o número da opção desejada:"""

INFORMACOES = """╔══════════════════════╗
║      *INFORMAÇÕES*     ║
╚══════════════════════╝

📌 *Horários:* Seg-Sex 8h-18h | Sáb 8h-15h
📌 *Formas de pagamento:* Cartão, PIX, Boleto
📌 *Prazo de entrega:* Até 3 dias úteis
📌 *Suporte:* suporte@exemplo.com

Digite *0* para voltar ao menu principal."""

AGENDAR_NOME = "Informe seu *nome* completo:"
AGENDAR_SERVICO = "Qual *serviço* você deseja?"
AGENDAR_DATA = "Informe a *data e horário* desejados (ex: 15/07 14:30):"
AGENDAR_CONFIRMA = "Confirma o agendamento?\n\n📌 *Nome:* {nome}\n📌 *Serviço:* {servico}\n📌 *Data/Hora:* {data_hora}\n\nDigite *1* para confirmar ou *0* para cancelar."
AGENDAR_SUCESSO = "✅ *Agendamento confirmado!*\n\nEm breve você receberá um lembrete. Digite *0* para voltar ao menu."
AGENDAR_CANCELADO = "❌ Agendamento cancelado. Digite *0* para voltar ao menu."

FALAR_BOT = "🤖 *Modo conversa ativado!*\n\nPode me perguntar qualquer coisa sobre nossos produtos ou serviços. Digite *0* ou *menu* a qualquer momento para voltar ao menu principal."

FALAR_ATENDENTE = "🔁 Transferindo para um atendente...\n\nEm breve alguém da nossa equipe irá atendê-lo. Caso seja urgente, ligue para (11) 99999-8888."


def get_menu_text(estado, dados=None):
    # Retorna o texto da tela correspondente ao estado atual do cliente
    if estado == 'inicio':
        return MENU_PRINCIPAL
    if estado == 'informacoes':
        return INFORMACOES
    if estado == 'agendar_nome':
        return AGENDAR_NOME
    if estado == 'agendar_servico':
        return AGENDAR_SERVICO
    if estado == 'agendar_data':
        return AGENDAR_DATA
    if estado == 'agendar_confirmar':
        return AGENDAR_CONFIRMA.format(**dados) if dados else AGENDAR_CONFIRMA
    if estado == 'agendamento_sucesso':
        return AGENDAR_SUCESSO
    if estado == 'agendamento_cancelado':
        return AGENDAR_CANCELADO
    if estado == 'falando_atendente':
        return FALAR_ATENDENTE
    if estado == 'falando_bot':
        return FALAR_BOT
    return MENU_PRINCIPAL
