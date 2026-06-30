import re
import hashlib
import secrets
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from httpx import AsyncClient

from config import GATEWAY_URL
from database import init_db, SessionLocal, Cliente, Conversa, Agendamento, get_config, set_config
from handlers.menu import get_menu_text, AGENDAR_SUCESSO, AGENDAR_CANCELADO
from handlers.ai import ask_ai, is_configured as ai_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print('[Bot] Database initialized')
    yield
    global _http
    if _http:
        await _http.aclose()


app = FastAPI(lifespan=lifespan)
_http = None


async def get_http():
    global _http
    if _http is None:
        _http = AsyncClient(base_url=GATEWAY_URL, timeout=15)
    return _http


async def send_whatsapp(to: str, text: str):
    try:
        http = await get_http()
        await http.post('/send', json={'to': to, 'text': text})
    except Exception as e:
        print(f'[Bot] Error sending to {to}: {e}')


async def get_cliente(telefone: str):
    db = SessionLocal()
    try:
        cliente = db.query(Cliente).filter_by(telefone=telefone).first()
        if not cliente:
            cliente = Cliente(telefone=telefone, estado='inicio', dados={})
            db.add(cliente)
            db.commit()
            db.refresh(cliente)
        return cliente
    finally:
        db.close()


async def save_conversa(telefone: str, mensagem: str, resposta: str = '', tipo: str = 'texto'):
    db = SessionLocal()
    try:
        db.add(Conversa(telefone=telefone, mensagem=mensagem, resposta=resposta, tipo=tipo))
        db.commit()
    finally:
        db.close()


async def update_cliente_estado(telefone: str, estado: str, dados: dict = None):
    db = SessionLocal()
    try:
        cliente = db.query(Cliente).filter_by(telefone=telefone).first()
        if cliente:
            cliente.estado = estado
            if dados:
                cliente.dados = {**cliente.dados, **dados}
            db.commit()
    finally:
        db.close()


async def processar_menu(telefone: str, texto: str, cliente: Cliente) -> str:
    texto_clean = texto.strip()

    if cliente.estado == 'inicio':
        if texto_clean == '1':
            await update_cliente_estado(telefone, 'informacoes')
            return get_menu_text('informacoes')
        elif texto_clean == '2':
            await update_cliente_estado(telefone, 'agendar_nome')
            return get_menu_text('agendar_nome')
        elif texto_clean == '3':
            await update_cliente_estado(telefone, 'falando_bot')
            return get_menu_text('falando_bot')
        elif texto_clean == '4':
            await update_cliente_estado(telefone, 'falando_atendente')
            return get_menu_text('falando_atendente')
        elif texto_clean == '5':
            return 'Obrigado pelo contato! 😊 Estamos sempre à disposição. Digite *Olá* quando precisar.'
        else:
            return get_menu_text('inicio')

    if cliente.estado == 'informacoes':
        if texto_clean == '0':
            await update_cliente_estado(telefone, 'inicio')
            return get_menu_text('inicio')
        return get_menu_text('informacoes')

    if cliente.estado == 'agendar_nome':
        dados = {'nome': texto}
        await update_cliente_estado(telefone, 'agendar_servico', dados)
        return get_menu_text('agendar_servico')

    if cliente.estado == 'agendar_servico':
        dados = cliente.dados.copy()
        dados['servico'] = texto
        await update_cliente_estado(telefone, 'agendar_data', dados)
        return get_menu_text('agendar_data')

    if cliente.estado == 'agendar_data':
        dados = cliente.dados.copy()
        dados['data_hora'] = texto
        await update_cliente_estado(telefone, 'agendar_confirmar', dados)
        return get_menu_text('agendar_confirmar', dados)

    if cliente.estado == 'agendar_confirmar':
        if texto_clean == '1':
            try:
                data_hora = datetime.strptime(cliente.dados.get('data_hora', ''), '%d/%m %H:%M')
                data_hora = data_hora.replace(year=datetime.now().year)
            except ValueError:
                data_hora = datetime.now()

            db = SessionLocal()
            try:
                db.add(Agendamento(
                    telefone=telefone,
                    nome=cliente.dados.get('nome', ''),
                    data_hora=data_hora,
                    servico=cliente.dados.get('servico', ''),
                    observacao='',
                ))
                db.commit()
            finally:
                db.close()

            await update_cliente_estado(telefone, 'inicio', {})
            return get_menu_text('agendamento_sucesso') or AGENDAR_SUCESSO
        else:
            await update_cliente_estado(telefone, 'inicio', {})
            return get_menu_text('agendamento_cancelado') or AGENDAR_CANCELADO

    if cliente.estado == 'falando_bot':
        if texto_clean in ('0', 'menu', 'inicio'):
            await update_cliente_estado(telefone, 'inicio')
            return get_menu_text('inicio')
        return None

    if cliente.estado == 'falando_atendente':
        return get_menu_text('falando_atendente')

    return get_menu_text('inicio')


@app.post('/webhook')
async def webhook(request: Request):
    data = await request.json()
    from_number = data['from']
    text = data['text'].strip()
    msg_type = data.get('type', 'text')

    number_only = from_number.split('@')[0] if '@' in from_number else from_number
    whitelist = _get_whitelist()
    whitelist_enabled = get_config('whitelist_enabled', '1') == '1'

    if whitelist_enabled and whitelist and number_only not in whitelist:
        print(f'[Bot] Blocked message from {number_only} (not in whitelist)')
        return {'ok': True, 'blocked': True}

    cliente = await get_cliente(from_number)
    await save_conversa(from_number, text, tipo=msg_type)

    if re.match(r'^[0-9]$', text) or text.lower() in ('olá', 'oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'menu', 'inicio', '0'):
        resposta = await processar_menu(from_number, text, cliente)
    else:
        if cliente.estado == 'falando_bot':
            resposta = await ask_ai(text)
        elif cliente.estado == 'falando_atendente':
            resposta = get_menu_text('falando_atendente')
        else:
            resposta = await ask_ai(text)
            await update_cliente_estado(from_number, 'inicio')

    if resposta is None:
        resposta = await ask_ai(text)

    await save_conversa(from_number, text, resposta, 'resposta')
    await send_whatsapp(from_number, resposta)

    return {'ok': True}


# ─── Admin Dashboard ─────────────────────────────────────────────

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


def _get_admin_password() -> str:
    return get_config('admin_password', '')


def _is_admin_configured() -> bool:
    return bool(_get_admin_password())


def _get_whitelist() -> set:
    raw = get_config('whitelist', '')
    return set(n.strip() for n in raw.split(',') if n.strip()) if raw else set()


@app.get('/api/setup-status')
async def api_setup_status():
    return {
        'configured': _is_admin_configured(),
        'groq_configured': ai_configured(),
    }


@app.post('/api/setup')
async def api_setup(request: Request):
    if _is_admin_configured():
        raise HTTPException(status_code=400, detail='Admin já configurado')
    data = await request.json()
    password = data.get('password', '')
    if len(password) < 4:
        raise HTTPException(status_code=400, detail='Senha deve ter no mínimo 4 caracteres')
    set_config('admin_password', password)
    if data.get('groq_api_key'):
        set_config('groq_api_key', data['groq_api_key'])
    if data.get('groq_model'):
        set_config('groq_model', data['groq_model'])
    if data.get('groq_base_url'):
        set_config('groq_base_url', data['groq_base_url'])
    print('[Admin] Full setup completed')
    return {'ok': True}


@app.post('/admin/login')
async def admin_login(request: Request):
    data = await request.json()
    if data.get('password') != _get_admin_password():
        raise HTTPException(status_code=401, detail='Senha inválida')
    token = _generate_token()
    ADMIN_TOKEN[_hash_token(token)] = True
    return {'token': token}


@app.get('/admin/')
async def admin_dashboard():
    html_path = Path(__file__).parent / 'static' / 'dashboard.html'
    if not html_path.exists():
        return HTMLResponse('<h1>Dashboard not found</h1>', status_code=404)
    return HTMLResponse(html_path.read_text(encoding='utf-8'))


@app.get('/api/stats')
async def api_stats(request: Request):
    _check_auth(request)
    db = SessionLocal()
    try:
        total_clientes = db.query(Cliente).count()
        total_conversas = db.query(Conversa).count()
        total_agendamentos = db.query(Agendamento).count()
        agendamentos_hoje = db.query(Agendamento).filter(
            Agendamento.data_hora >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        whitelist = _get_whitelist()
        whitelist_enabled = get_config('whitelist_enabled', '1') == '1'
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
    finally:
        db.close()


@app.get('/api/conversas/{telefone}')
async def api_conversas(telefone: str, request: Request):
    _check_auth(request)
    db = SessionLocal()
    try:
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
    finally:
        db.close()


@app.put('/api/agendamentos/{agendamento_id}')
async def api_update_agendamento(agendamento_id: int, request: Request):
    _check_auth(request)
    data = await request.json()
    db = SessionLocal()
    try:
        agendamento = db.query(Agendamento).filter_by(id=agendamento_id).first()
        if not agendamento:
            raise HTTPException(status_code=404, detail='Agendamento not found')
        if 'status' in data:
            agendamento.status = data['status']
        if 'observacao' in data:
            agendamento.observacao = data['observacao']
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@app.put('/api/clientes/{telefone}/nome')
async def api_update_cliente_nome(telefone: str, request: Request):
    _check_auth(request)
    data = await request.json()
    db = SessionLocal()
    try:
        cliente = db.query(Cliente).filter_by(telefone=telefone).first()
        if not cliente:
            raise HTTPException(status_code=404, detail='Cliente not found')
        cliente.nome = data.get('nome', cliente.nome)
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@app.get('/api/whitelist')
async def api_get_whitelist(request: Request):
    _check_auth(request)
    enabled = get_config('whitelist_enabled', '1') == '1'
    return {
        'enabled': enabled,
        'numbers': sorted(_get_whitelist()),
    }


@app.put('/api/whitelist')
async def api_put_whitelist(request: Request):
    _check_auth(request)
    data = await request.json()
    numbers = data.get('numbers', [])
    set_config('whitelist', ','.join(numbers))
    if 'enabled' in data:
        set_config('whitelist_enabled', '1' if data['enabled'] else '0')
    print(f'[Admin] Whitelist updated')
    return {'ok': True}


@app.get('/api/settings')
async def api_get_settings(request: Request):
    _check_auth(request)
    return {
        'groq_api_key': get_config('groq_api_key', ''),
        'groq_model': get_config('groq_model', 'grok-2-1212'),
        'groq_base_url': get_config('groq_base_url', 'https://api.groq.com/openai/v1'),
    }


@app.put('/api/settings')
async def api_put_settings(request: Request):
    _check_auth(request)
    data = await request.json()
    for key in ('groq_api_key', 'groq_model', 'groq_base_url'):
        if key in data:
            set_config(key, data[key])
    print(f'[Admin] Settings updated')
    return {'ok': True}


@app.post('/api/send')
async def api_send(request: Request):
    _check_auth(request)
    data = await request.json()
    to = data.get('to')
    text = data.get('text')
    if not to or not text:
        raise HTTPException(status_code=400, detail='Missing "to" or "text"')

    cliente = await get_cliente(to)
    await save_conversa(to, text, f'[Admin] {text}', 'admin')
    await send_whatsapp(to, text)
    return {'ok': True}


@app.get('/clientes')
async def list_clientes():
    db = SessionLocal()
    try:
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
    finally:
        db.close()


@app.get('/agendamentos')
async def list_agendamentos():
    db = SessionLocal()
    try:
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
    finally:
        db.close()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
