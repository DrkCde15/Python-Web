import pytest
from security import hash_password, verify_password, encrypt_value, decrypt_value


def test_hash_and_verify_password():
    hashed = hash_password('minha_senha')
    assert hashed != 'minha_senha'
    assert verify_password('minha_senha', hashed) is True
    assert verify_password('senha_errada', hashed) is False


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv('ENCRYPTION_KEY', 'SLAAiqIJ9BixA5hBjI1Lm1_QfPyFmbH3W4ylm4AVZWA=')
    from security import encrypt_value, decrypt_value

    original = 'minha_api_key_super_secreta'
    encrypted = encrypt_value(original)
    assert encrypted != original
    decrypted = decrypt_value(encrypted)
    assert decrypted == original


def test_decrypt_plain_text_returns_original():
    assert decrypt_value('texto_sem_criptografia') == 'texto_sem_criptografia'


def test_empty_values():
    hashed = hash_password('')
    assert verify_password('', hashed) is True
