import pytest
from handlers.menu import get_menu_text


class FakeCliente:
    def __init__(self, estado='inicio', dados=None):
        self.estado = estado
        self.dados = dados or {}


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def query(self, *args):
        return FakeQuery()


class FakeQuery:
    def filter_by(self, **kwargs):
        return self

    def first(self):
        return None


@pytest.mark.asyncio
async def test_processar_menu_inicio_mostra_menu(monkeypatch):
    from main import processar_menu

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', 'qualquer coisa', cliente, db)
    assert resposta == get_menu_text('inicio')


@pytest.mark.asyncio
async def test_processar_menu_opcao_1_informacoes(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', '1', cliente, db)
    assert updates == [('informacoes', None)]
    assert resposta == get_menu_text('informacoes')


@pytest.mark.asyncio
async def test_processar_menu_opcao_2_agendar(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', '2', cliente, db)
    assert updates == [('agendar_nome', None)]
    assert resposta == get_menu_text('agendar_nome')


@pytest.mark.asyncio
async def test_processar_menu_opcao_3_falar_bot(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', '3', cliente, db)
    assert updates == [('falando_bot', None)]
    assert resposta == get_menu_text('falando_bot')


@pytest.mark.asyncio
async def test_processar_menu_opcao_4_atendente(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', '4', cliente, db)
    assert updates == [('falando_atendente', None)]
    assert resposta == get_menu_text('falando_atendente')


@pytest.mark.asyncio
async def test_processar_menu_opcao_5_sair(monkeypatch):
    from main import processar_menu

    db = FakeDB()
    cliente = FakeCliente('inicio')
    resposta = await processar_menu('5511999998888', '5', cliente, db)
    assert 'Obrigado' in resposta


@pytest.mark.asyncio
async def test_processar_menu_voltar_ao_inicio(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('informacoes')
    resposta = await processar_menu('5511999998888', '0', cliente, db)
    assert updates == [('inicio', None)]
    assert resposta == get_menu_text('inicio')


@pytest.mark.asyncio
async def test_processar_menu_falando_bot_volta_ao_inicio(monkeypatch):
    from main import processar_menu

    updates = []
    async def fake_update(telefone, estado, dados=None, db=None):
        updates.append((estado, dados))

    monkeypatch.setattr('main.update_cliente_estado', fake_update)

    db = FakeDB()
    cliente = FakeCliente('falando_bot')
    resposta = await processar_menu('5511999998888', '0', cliente, db)
    assert updates == [('inicio', None)]
    assert resposta == get_menu_text('inicio')


@pytest.mark.asyncio
async def test_processar_menu_falando_bot_mantem_estado(monkeypatch):
    from main import processar_menu

    db = FakeDB()
    cliente = FakeCliente('falando_bot')
    resposta = await processar_menu('5511999998888', 'qual é o horário?', cliente, db)
    assert resposta is None  # None = passa pro AI
