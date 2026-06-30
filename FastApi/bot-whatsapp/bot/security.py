# Módulo de segurança: hash de senha (bcrypt) e criptografia de valores sensíveis (Fernet/AES)
# A chave Fernet é lida da variável de ambiente ENCRYPTION_KEY.
# Se não estiver definida, é gerada automaticamente na init_db() e persistida no banco
# (tabela admin_config, chave "encryption_key").
import os
import bcrypt
from cryptography.fernet import Fernet
from dotenv import load_dotenv


load_dotenv()


def _get_fernet() -> Fernet | None:
    # Lê a chave do ambiente a cada chamada (permite mock em testes)
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        return None
    return Fernet(key.encode())


def hash_password(password: str) -> str:
    # Gera hash bcrypt com salt automático
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    # Verifica senha contra hash bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())


def encrypt_value(plain_text: str) -> str:
    # Criptografa string com Fernet (AES-128-CBC + HMAC). Retorna texto puro se sem chave.
    f = _get_fernet()
    if not f:
        return plain_text
    return f.encrypt(plain_text.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    # Descriptografa string Fernet. Retorna original se sem chave ou se não for válido.
    f = _get_fernet()
    if not f:
        return encrypted
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted