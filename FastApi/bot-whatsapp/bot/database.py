from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Cliente(Base):
    __tablename__ = 'clientes'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), unique=True, nullable=False, index=True)
    nome = Column(String(100), default='')
    estado = Column(String(50), default='inicio')
    dados = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversa(Base):
    __tablename__ = 'conversas'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), nullable=False, index=True)
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text, default='')
    tipo = Column(String(20), default='texto')
    created_at = Column(DateTime, default=datetime.utcnow)


class Agendamento(Base):
    __tablename__ = 'agendamentos'

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), nullable=False, index=True)
    nome = Column(String(100), default='')
    data_hora = Column(DateTime, nullable=False)
    servico = Column(String(100), default='')
    observacao = Column(Text, default='')
    status = Column(String(20), default='pendente')
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminConfig(Base):
    __tablename__ = 'admin_config'

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def get_config(key: str, default: str = '') -> str:
    db = SessionLocal()
    try:
        cfg = db.query(AdminConfig).filter_by(key=key).first()
        return cfg.value if cfg else default
    finally:
        db.close()


def set_config(key: str, value: str):
    db = SessionLocal()
    try:
        cfg = db.query(AdminConfig).filter_by(key=key).first()
        if cfg:
            cfg.value = value
        else:
            db.add(AdminConfig(key=key, value=value))
        db.commit()
    finally:
        db.close()
