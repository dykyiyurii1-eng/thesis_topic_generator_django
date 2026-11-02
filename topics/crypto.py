import base64
import hashlib
import logging
import os
from django.conf import settings
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet_instance() -> MultiFernet:
    """
    Ініціалізує MultiFernet на основі змінної оточення FERNET_KEYS.
    Підтримує ротацію ключів: перший ключ у списку використовується для шифрування,
    усі ключі — для дешифрування.
    Якщо змінна не задана, генерує стабільний ключ на основі Django SECRET_KEY (для dev-режиму).
    """
    raw_keys = os.environ.get('FERNET_KEYS', '').strip()

    keys = []
    if raw_keys:
        for k in raw_keys.split(','):
            k = k.strip()
            if k:
                try:
                    keys.append(Fernet(k.encode('utf-8')))
                except Exception as e:
                    logger.warning("[CRYPTO] Некоректний ключ у FERNET_KEYS: %s", e)

    if not keys:
        # Fallback на основі Django SECRET_KEY: створюємо валідний 32-байтний base64 url-safe ключ
        secret = getattr(settings, 'SECRET_KEY', 'default-thesis-gen-secret-key-12345')
        digest = hashlib.sha256(secret.encode('utf-8')).digest()
        urlsafe_key = base64.urlsafe_b64encode(digest)
        keys = [Fernet(urlsafe_key)]

    return MultiFernet(keys)


def encrypt(plain_text: str) -> str:
    """
    Шифрує відкритий рядок (API-ключ) та повертає зашифрований рядок.
    """
    if not plain_text:
        return ""
    fernet = _get_fernet_instance()
    cipher_bytes = fernet.encrypt(plain_text.strip().encode('utf-8'))
    return cipher_bytes.decode('utf-8')


def decrypt(cipher_text: str) -> str:
    """
    Дешифрує зашифрований рядок у відкритий текст.
    При невалідному токені кидає InvalidToken або повертає порожній рядок.
    """
    if not cipher_text:
        return ""
    fernet = _get_fernet_instance()
    try:
        plain_bytes = fernet.decrypt(cipher_text.strip().encode('utf-8'))
        return plain_bytes.decode('utf-8')
    except InvalidToken:
        logger.error("[CRYPTO] Не вдалося дешифрувати API-ключ: недійсний токен.")
        raise

