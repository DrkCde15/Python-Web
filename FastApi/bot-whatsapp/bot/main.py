# Bot WhatsApp — FastAPI + Groq + Baileys
# Recebe webhooks do gateway Node.js, processa menu/IA e envia respostas de volta.
import re
import hashlib
import secrets
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from httpx import AsyncClient, Limits
from sqlalchemy.orm import Session

from config import GATEWAY_URL
from database import init_db, get_db, SessionLocal, Cliente, Conversa, Agendamento, get_config, set_config
from handlers.menu import get_menu_text
from handlers.ai import ask_ai, is_configured as ai_configured
from security import hash_password, verify_password, encrypt_value, decrypt_value
from schemas import (
    WebhookPayload,
    SendMessageRequest,
    SetupRequest,
    LoginRequest,
    WhitelistUpdate,
    SettingsUpdate,
    AgendamentoUpdate,
    ClienteNomeUpdate,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o banco ao iniciar o servidor
    init_db()
    logger.info('database_initialized')
    yield
    # Fecha o HTTP client ao desligar o servidor
    global _http
    if _http:
        await _http.aclose()


app = FastAPI(lifespan=lifespan)
_http = None


async def get_http():
    # Singleton do HTTP client para comunicação com o gateway
    global _http
    if _http is None:
        _http = AsyncClient(
            base_url=GATEWAY_URL,
            timeout=15,
            limits=Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _http


async def send_whatsapp(to: str, text: str):
    # Envia mensagem de texto para o gateway (que entrega no WhatsApp)
    try:
        http = await get_http()
        await http.post('/send', json={'to': to, 'text': text})
    except Exception as e:
        logger.error('send_failed', to=to, error=str(e))


async def get_cliente(telefone: str, db: Session):
    # Busca cliente pelo telefone ou cria um novo com estado inicial 'inicio'
    cliente = db.query(Cliente).filter_by(telefone=telefone).first()
    if not cliente:
        cliente = Cliente(telefone=telefone, estado='inicio', dados={})
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    return cliente


async def save_conversa(telefone: str, mensagem: str, resposta: str = '', tipo: str = 'texto', db: Session = None):
    # Persiste uma mensagem no histórico. Aceita db opcional (fallback pra sessão própria).
    close = db is None
    if close:
        db = SessionLocal()
    try:
        db.add(Conversa(telefone=telefone, mensagem=mensagem, resposta=resposta, tipo=tipo))
        db.commit()
    finally:
        if close:
            db.close()


async def update_cliente_estado(telefone: str, estado: str, dados: dict = None, db: Session = None):
    # Atualiza o estado do cliente na máquina de estados do menu.
    # Opcionalmente mescla dados temporários (ex: nome, serviço, data) no campo JSON.
    close = db is None
    if close:
        db = SessionLocal()
    try:
        cliente = db.query(Cliente).filter_by(telefone=telefone).first()
        if cliente:
            cliente.estado = estado
            if dados:
                cliente.dados = {**cliente.dados, **dados}
            db.commit()
    finally:
        if close:
            db.close()


async def processar_menu(telefone: str, texto: str, cliente: Cliente, db: Session) -> str | None:
    # Máquina de estados do menu interativo.
    # Cada estado mapeia para um conjunto de respostas possíveis.
    # Retorna a mensagem a ser enviada ou None (delega pro AI).
    texto_clean = texto.strip()

    if cliente.estado == 'inicio':
        if texto_clean == '1':
            await update_cliente_estado(telefone, 'informacoes', db=db)
            return get_menu_text('informacoes')
        elif texto_clean == '2':
            await update_cliente_estado(telefone, 'agendar_nome', db=db)
            return get_menu_text('agendar_nome')
        elif texto_clean == '3':
            await update_cliente_estado(telefone, 'falando_bot', db=db)
            return get_menu_text('falando_bot')
        elif texto_clean == '4':
            await update_cliente_estado(telefone, 'falando_atendente', db=db)
            return get_menu_text('falando_atendente')
        elif texto_clean == '5':
            return 'Obrigado pelo contato! 😊 Estamos sempre à disposição. Digite *Olá* quando precisar.'
        else:
            return get_menu_text('inicio')

    if cliente.estado == 'informacoes':
        if texto_clean == '0':
            await update_cliente_estado(telefone, 'inicio', db=db)
            return get_menu_text('inicio')
        return get_menu_text('informacoes')

    if cliente.estado == 'agendar_nome':
        dados = {'nome': texto}
        await update_cliente_estado(telefone, 'agendar_servico', dados, db)
        return get_menu_text('agendar_servico')

    if cliente.estado == 'agendar_servico':
        dados = cliente.dados.copy()
        dados['servico'] = texto
        await update_cliente_estado(telefone, 'agendar_data', dados, db)
        return get_menu_text('agendar_data')

    if cliente.estado == 'agendar_data':
        dados = cliente.dados.copy()
        dados['data_hora'] = texto
        await update_cliente_estado(telefone, 'agendar_confirmar', dados, db)
        return get_menu_text('agendar_confirmar', dados)

    if cliente.estado == 'agendar_confirmar':
        if texto_clean == '1':
            try:
                data_hora = datetime.strptime(cliente.dados.get('data_hora', ''), '%d/%m %H:%M')
                data_hora = data_hora.replace(year=datetime.now().year)
            except ValueError:
                data_hora = datetime.now()

            db.add(Agendamento(
                telefone=telefone,
                nome=cliente.dados.get('nome', ''),
                data_hora=data_hora,
                servico=cliente.dados.get('servico', ''),
                observacao='',
            ))
            db.commit()

            await update_cliente_estado(telefone, 'inicio', {}, db)
            return get_menu_text('agendamento_sucesso')
        else:
            await update_cliente_estado(telefone, 'inicio', {}, db)
            return get_menu_text('agendamento_cancelado')

    # Modo 'falando_bot': texto livre é delegado à IA. 0/menu/inicio volta ao menu.
    if cliente.estado == 'falando_bot':
        if texto_clean in ('0', 'menu', 'inicio'):
            await update_cliente_estado(telefone, 'inicio', db=db)
            return get_menu_text('inicio')
        return None  # None sinaliza que o texto deve ser enviado à IA

    # Modo 'falando_atendente': mostra mensagem fixa de transferência
    if cliente.estado == 'falando_atendente':
        return get_menu_text('falando_atendente')

    # Fallback: mostra o menu principal
    return get_menu_text('inicio')


@app.post('/webhook')
async def webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    # Endpoint chamado pelo gateway quando chega uma mensagem nova no WhatsApp
    from_number = payload.from_
    text = payload.text.strip()
    msg_type = payload.type or 'text'

    # Verifica whitelist (se ativa)
    number_only = from_number.split('@')[0] if '@' in from_number else from_number
    whitelist = _get_whitelist(db)
    whitelist_enabled = get_config('whitelist_enabled', '1', db) == '1'

    if whitelist_enabled and whitelist and number_only not in whitelist:
        logger.info('blocked_message', number=number_only)
        return {'ok': True, 'blocked': True}

    cliente = await get_cliente(from_number, db)
    await save_conversa(from_number, text, tipo=msg_type, db=db)

    # Decide se processa menu ou delega pra IA
    if re.match(r'^[0-9]$', text) or text.lower() in ('olá', 'oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'menu', 'inicio', '0'):
        resposta = await processar_menu(from_number, text, cliente, db)
    else:
        if cliente.estado == 'falando_bot':
            resposta = await ask_ai(text)
        elif cliente.estado == 'falando_atendente':
            resposta = get_menu_text('falando_atendente')
        else:
            resposta = await ask_ai(text)
            await update_cliente_estado(from_number, 'inicio', db=db)

    # Se o menu retornou None, o texto deve ser processado pela IA
    if resposta is None:
        resposta = await ask_ai(text)

    await save_conversa(from_number, text, resposta, 'resposta', db=db)
    await send_whatsapp(from_number, resposta)

    return {'ok': True}


# ─── Admin / Autenticação ──────────────────────────────────────────
# Sistema simples de token bearer: login gera token SHA-256, armazenado em memória.
# Tokens são voláteis (perdidos ao reiniciar o servidor).

ADMIN_TOKEN = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token() -> str:
    return secrets.token_hex(32)


def _check_auth(request: Request):
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
    if not token or _hash_token(token) not in ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail='Unauthorized')
    return True


def _get_admin_password(db: Session = None) -> str:
    return get_config('admin_password', '', db)


def _is_admin_configured(db: Session = None) -> bool:
    return bool(_get_admin_password(db))


def _get_whitelist(db: Session = None) -> set:
    # Lê a whitelist do banco (números separados por vírgula) e retorna como set
    raw = get_config('whitelist', '', db)
    return set(n.strip() for n in raw.split(',') if n.strip()) if raw else set()


@app.get('/api/setup-status')
async def api_setup_status(db: Session = Depends(get_db)):
    # Verifica se o admin e a IA já foram configurados
    return {
        'configured': _is_admin_configured(db),
        'groq_configured': ai_configured(),
    }


@app.post('/api/setup')
async def api_setup(body: SetupRequest, db: Session = Depends(get_db)):
    # Configuração inicial única: cria senha admin (bcrypt) e opcionalmente chave da IA
    if _is_admin_configured(db):
        raise HTTPException(status_code=400, detail='Admin já configurado')
    set_config('admin_password', hash_password(body.password), db)
    if body.groq_api_key:
        set_config('groq_api_key', body.groq_api_key, db)
    if body.groq_model:
        set_config('groq_model', body.groq_model, db)
    if body.groq_base_url:
        set_config('groq_base_url', body.groq_base_url, db)
    logger.info('setup_completed')
    return {'ok': True}


@app.post('/admin/login')
async def admin_login(body: LoginRequest, db: Session = Depends(get_db)):
    # Login: verifica senha com bcrypt, retorna token bearer
    stored = _get_admin_password(db)
    if not stored or not verify_password(body.password, stored):
        raise HTTPException(status_code=401, detail='Senha inválida')
    token = _generate_token()
    ADMIN_TOKEN[_hash_token(token)] = True
    logger.info('admin_logged_in')
    return {'token': token}


@app.get('/admin/')
async def admin_dashboard():
    # Servir dashboard HTML estático
    html_path = Path(__file__).parent / 'static' / 'dashboard.html'
    if not html_path.exists():
        return HTMLResponse('<h1>Dashboard not found</h1>', status_code=404)
    return HTMLResponse(html_path.read_text(encoding='utf-8'))


@app.get('/api/stats')
async def api_stats(request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    total_clientes = db.query(Cliente).count()
    total_conversas = db.query(Conversa).count()
    total_agendamentos = db.query(Agendamento).count()
    agendamentos_hoje = db.query(Agendamento).filter(
        Agendamento.data_hora >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    whitelist = _get_whitelist(db)
    whitelist_enabled = get_config('whitelist_enabled', '1', db) == '1'
    return {
        'total_clientes': total_clientes,
        'total_conversas': total_conversas,
        'total_agendamentos': total_agendamentos,
        'agendamentos_hoje': agendamentos_hoje,
        'whitelist_enabled': whitelist_enabled,
        'whitelist_count': len(whitelist) if whitelist_enabled else 0,
        'whitelist_active': whitelist_enabled,
        'groq_configured': ai_configured(),
    }


@app.get('/api/conversas/{telefone}')
async def api_conversas(telefone: str, request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    conversas = db.query(Conversa).filter_by(telefone=telefone).order_by(Conversa.created_at.asc()).limit(100).all()
    return [
        {
            'id': c.id,
            'mensagem': c.mensagem,
            'resposta': c.resposta,
            'tipo': c.tipo,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        }
        for c in conversas
    ]


@app.put('/api/agendamentos/{agendamento_id}')
async def api_update_agendamento(agendamento_id: int, body: AgendamentoUpdate, request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    agendamento = db.query(Agendamento).filter_by(id=agendamento_id).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail='Agendamento not found')
    if body.status is not None:
        agendamento.status = body.status
    if body.observacao is not None:
        agendamento.observacao = body.observacao
    db.commit()
    return {'ok': True}


@app.put('/api/clientes/{telefone}/nome')
async def api_update_cliente_nome(telefone: str, body: ClienteNomeUpdate, request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    cliente = db.query(Cliente).filter_by(telefone=telefone).first()
    if not cliente:
        raise HTTPException(status_code=404, detail='Cliente not found')
    cliente.nome = body.nome
    db.commit()
    return {'ok': True}


@app.get('/api/whitelist')
async def api_get_whitelist(request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    enabled = get_config('whitelist_enabled', '1', db) == '1'
    return {
        'enabled': enabled,
        'numbers': sorted(_get_whitelist(db)),
    }


@app.put('/api/whitelist')
async def api_put_whitelist(body: WhitelistUpdate, request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    set_config('whitelist', ','.join(body.numbers), db)
    if body.enabled is not None:
        set_config('whitelist_enabled', '1' if body.enabled else '0', db)
    logger.info('whitelist_updated')
    return {'ok': True}


@app.get('/api/settings')
async def api_get_settings(request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    return {
        'groq_api_key': get_config('groq_api_key', '', db),
        'groq_model': get_config('groq_model', 'grok-2-1212', db),
        'groq_base_url': get_config('groq_base_url', 'https://api.groq.com/openai/v1', db),
    }


@app.put('/api/settings')
async def api_put_settings(body: SettingsUpdate, request: Request, db: Session = Depends(get_db)):
    _check_auth(request)
    for key in ('groq_api_key', 'groq_model', 'groq_base_url'):
        val = getattr(body, key, None)
        if val is not None:
            set_config(key, val, db)
    logger.info('settings_updated')
    return {'ok': True}


@app.post('/api/send')
async def api_send(body: SendMessageRequest, request: Request, db: Session = Depends(get_db)):
    # Envia mensagem manualmente pelo dashboard admin
    _check_auth(request)
    cliente = await get_cliente(body.to, db)
    await save_conversa(body.to, body.text, f'[Admin] {body.text}', 'admin', db=db)
    await send_whatsapp(body.to, body.text)
    return {'ok': True}


@app.get('/clientes')
async def list_clientes(db: Session = Depends(get_db)):
    # Lista todos os clientes (endpoint público)
    clientes = db.query(Cliente).all()
    return [
        {
            'id': c.id,
            'telefone': c.telefone,
            'nome': c.nome,
            'estado': c.estado,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        }
        for c in clientes
    ]


@app.get('/agendamentos')
async def list_agendamentos(db: Session = Depends(get_db)):
    # Lista todos os agendamentos (endpoint público)
    agendamentos = db.query(Agendamento).order_by(Agendamento.data_hora.desc()).all()
    return [
        {
            'id': a.id,
            'telefone': a.telefone,
            'nome': a.nome,
            'data_hora': a.data_hora.isoformat() if a.data_hora else None,
            'servico': a.servico,
            'status': a.status,
        }
        for a in agendamentos
    ]


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
