# Modelos SQLAlchemy + funções de acesso ao banco com suporte a DI (get_db)
# Valores sensíveis (admin_password, groq_api_key) são criptografados automaticamente.
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config import DATABASE_URL
from security import encrypt_value, decrypt_value

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Chaves que serão criptografadas ao salvar e descriptografadas ao ler
SENSITIVE_KEYS = {'admin_password', 'groq_api_key'}


class Cliente(Base):
    __tablename__ = 'clientes'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), unique=True, nullable=False, index=True)  # JID do WhatsApp
    nome = Column(String(100), default='')
    estado = Column(String(50), default='inicio')  # Estado da máquina de estados do menu
    dados = Column(JSON, default=dict)  # Dados temporários do fluxo de agendamento
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversa(Base):
    __tablename__ = 'conversas'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), nullable=False, index=True)
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text, default='')
    tipo = Column(String(20), default='texto')  # text, image, list_response, button_response, admin
    created_at = Column(DateTime, default=datetime.utcnow)


class Agendamento(Base):
    __tablename__ = 'agendamentos'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), nullable=False, index=True)
    nome = Column(String(100), default='')
    data_hora = Column(DateTime, nullable=False)
    servico = Column(String(100), default='')
    observacao = Column(Text, default='')
    status = Column(String(20), default='pendente')  # pendente, confirmado, cancelado, concluido
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminConfig(Base):
    # Tabela chave-valor para configurações (admin_password, groq_*, whitelist, etc.)
    __tablename__ = 'admin_config'

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def ensure_encryption_key(db: Session | None = None):
    # Garante que ENCRYPTION_KEY esteja disponível: usa do ambiente, do banco, ou gera nova.
    import os
    from cryptography.fernet import Fernet
    key = os.getenv('ENCRYPTION_KEY')
    if key:
        return
    key = get_config('encryption_key', '', db)
    if key:
        os.environ['ENCRYPTION_KEY'] = key
        return
    key = Fernet.generate_key().decode()
    set_config('encryption_key', key, db)
    os.environ['ENCRYPTION_KEY'] = key


def init_db():
    # Aplica migrações pendentes via Alembic (fallback para create_all se falhar)
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
    except Exception:
        Base.metadata.create_all(bind=engine)
    # Garante que a chave de criptografia existe (gera e persiste se necessário)
    ensure_encryption_key()


def get_db():
    # Generator para Dependency Injection do FastAPI. Fecha a sessão automaticamente.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_config(key: str, default: str = '', db: Session | None = None) -> str:
    # Lê config do banco. Se for chave sensível, descriptografa.
    close = db is None
    if close:
        db = SessionLocal()
    try:
        cfg = db.query(AdminConfig).filter_by(key=key).first()
        val = cfg.value if cfg else default
        if val and key in SENSITIVE_KEYS:
            val = decrypt_value(val)
        return val
    finally:
        if close:
            db.close()


def set_config(key: str, value: str, db: Session | None = None):
    # Salva config no banco. Se for chave sensível, criptografa antes.
    close = db is None
    if close:
        db = SessionLocal()
    try:
        if key in SENSITIVE_KEYS:
            value = encrypt_value(value)
        cfg = db.query(AdminConfig).filter_by(key=key).first()
        if cfg:
            cfg.value = value
        else:
            db.add(AdminConfig(key=key, value=value))
        db.commit()
    finally:
        if close:
            db.close()
