# Textos do menu interativo — cada constante representa uma tela do fluxo do bot
MENU_PRINCIPAL = """╔══════════════════════╗
║       *ATENDIMENTO*     ║
╚══════════════════════╝

Olá! Como posso ajudar?

1️⃣ *Informações*
2️⃣ *Agendar horário*
3️⃣ *Falar com o Bot* 🤖
4️⃣ *Falar com atendente*
5️⃣ *Abrir chamado* 🎯
6️⃣ *Agendar reunião* 📅
7️⃣ *Sair*

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

CHAMADO_TITULO = "📋 *Abrir chamado*\n\nQual o *título* do chamado? (ex: Sistema de vendas)"
CHAMADO_DESCRICAO = "📋 Descreva o que precisa ser desenvolvido ou o problema encontrado:"
CHAMADO_CONFIRMA = "Confirma a abertura do chamado?\n\n📌 *Título:* {titulo}\n📌 *Descrição:* {descricao}\n\nDigite *1* para confirmar ou *0* para cancelar."
CHAMADO_SUCESSO = "✅ *Chamado aberto com sucesso!*\n\nNossa equipe vai analisar e entraremos em contato. Digite *0* para voltar ao menu."
CHAMADO_CANCELADO = "❌ Chamado cancelado. Digite *0* para voltar ao menu."

REUNIAO_TITULO = "📅 *Agendar reunião*\n\nQual o *assunto* da reunião?"
REUNIAO_DATA = "📅 Informe a *data e horário* desejados (ex: 15/07 14:30):"
REUNIAO_CONFIRMA = "Confirma o agendamento da reunião?\n\n📌 *Assunto:* {titulo}\n📌 *Data/Hora:* {data_hora}\n\nDigite *1* para confirmar ou *0* para cancelar."
REUNIAO_SUCESSO = "✅ *Reunião agendada!*\n\nVocê receberá um lembrete próximo da data. Digite *0* para voltar ao menu."
REUNIAO_CANCELADO = "❌ Reunião cancelada. Digite *0* para voltar ao menu."


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
    if estado == 'chamado_titulo':
        return CHAMADO_TITULO
    if estado == 'chamado_descricao':
        return CHAMADO_DESCRICAO
    if estado == 'chamado_confirmar':
        return CHAMADO_CONFIRMA.format(**dados) if dados else CHAMADO_CONFIRMA
    if estado == 'chamado_sucesso':
        return CHAMADO_SUCESSO
    if estado == 'chamado_cancelado':
        return CHAMADO_CANCELADO
    if estado == 'reuniao_titulo':
        return REUNIAO_TITULO
    if estado == 'reuniao_data':
        return REUNIAO_DATA
    if estado == 'reuniao_confirmar':
        return REUNIAO_CONFIRMA.format(**dados) if dados else REUNIAO_CONFIRMA
    if estado == 'reuniao_sucesso':
        return REUNIAO_SUCESSO
    if estado == 'reuniao_cancelado':
        return REUNIAO_CANCELADO
    if estado == 'falando_atendente':
        return FALAR_ATENDENTE
    if estado == 'falando_bot':
        return FALAR_BOT
    return MENU_PRINCIPAL
