import os
import json
import time
import logging
import requests
from django.utils import timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMError(Exception):
    def __init__(self, message, retry_after=None, is_auth_error=False):
        super().__init__(message)
        self.retry_after = retry_after
        self.is_auth_error = is_auth_error


def _raise_for_status(response, name):
    if response.status_code == 200:
        return
    if response.status_code in (401, 403):
        raise LLMError(f"{name}: недійсний або неавторизований API-ключ (код {response.status_code}).", is_auth_error=True)
    if response.status_code == 429:
        try:
            retry_after = int(float(response.headers.get('retry-after', 5)))
        except ValueError:
            retry_after = 5
        raise LLMError(f"Перевищено ліміт запитів {name}.", retry_after=retry_after)
    raise LLMError(f"{name}: помилка {response.status_code}. {response.text[:300]}")


def is_api_configured():
    return bool(os.getenv('GEMINI_API_KEY') or os.getenv('GROQ_API_KEY') or os.getenv('OPENROUTER_API_KEY'))


def parse_json_response(raw):
    if not raw or not raw.strip():
        raise LLMError("ШІ повернув порожню відповідь. Спробуйте ще раз.")

    raw = raw.strip()
    if raw.startswith('```json'):
        raw = raw[7:]
    if raw.startswith('```'):
        raw = raw[3:]
    if raw.endswith('```'):
        raw = raw[:-3]

    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1:
        raw = raw[start:end+1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"Не вдалося розпізнати відповідь ШІ як JSON. Помилка: {e}")


def _short_reason(e):
    t = str(e).lower()
    if "429" in t or "rate" in t or "quota" in t or "ліміт" in t:
        return "ліміт вичерпано"
    if "json_validate_failed" in t or "failed_generation" in t:
        return "неправильний формат відповіді"
    if "nameresolution" in t or "getaddrinfo" in t:
        return "немає з'єднання з мережею"
    if "401" in t or "403" in t or "ключ" in t or "auth" in t:
        return "недійсний або відсутній ключ"
    if "timeout" in t or "час очікування" in t:
        return "таймаут відповіді"
    return "збій сервісу"


def call_gemini(system, user, temperature=0.7, api_key=None):
    key = api_key or os.getenv('GEMINI_API_KEY')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    if not key:
        raise LLMError("Ключ Gemini не налаштовано.", is_auth_error=True)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(5, 25))
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі Gemini: {e}")

    _raise_for_status(response, 'Gemini')

    try:
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від Gemini.")


def call_groq(system, user, temperature=0.4, api_key=None):
    key = api_key or os.getenv('GROQ_API_KEY')
    model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    if not key:
        raise LLMError("Ключ Groq не налаштовано.", is_auth_error=True)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(5, 25))
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі Groq: {e}")

    _raise_for_status(response, 'Groq')

    try:
        data = response.json()
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від Groq.")


def call_openrouter(system, user, temperature=0.7, api_key=None):
    key = api_key or os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct:free')
    if not key:
        raise LLMError("Ключ OpenRouter не налаштовано.", is_auth_error=True)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(5, 25))
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі OpenRouter: {e}")

    _raise_for_status(response, 'OpenRouter')

    try:
        data = response.json()
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від OpenRouter.")


def _get_user_api_key(user_obj, provider_name: str):
    """
    Повертає об'єкт UserApiKey та розшифрований ключ для вказаного користувача та провайдера, якщо такий є.
    """
    if not user_obj or not getattr(user_obj, 'is_authenticated', False):
        return None, None

    from .models import UserApiKey
    from .crypto import decrypt

    provider_code = provider_name.lower()
    user_key_obj = UserApiKey.objects.filter(
        user=user_obj,
        provider=provider_code,
        is_valid=True
    ).first()

    if not user_key_obj:
        return None, None

    try:
        raw_key = decrypt(user_key_obj.encrypted_key)
        return user_key_obj, raw_key
    except Exception as e:
        logger.error("[LLM] Помилка дешифрування ключа користувача: %s", e)
        return None, None


def call_with_fallback(role, system, user_prompt, user_obj=None):
    """
    Виконує виклик LLM за ланцюжком провайдерів.
    Якщо у користувача налаштований власний валідний API-ключ (BYOK),
    пріоритетно використовується він.
    Якщо ключ користувача повертає помилку автентифікації (401/403),
    він позначається як is_valid=False, і виконується автоматичний fallback на системний ключ.
    """
    if role == 'generator':
        providers = [
            (call_gemini, 'Gemini', 'gemini'),
            (call_openrouter, 'OpenRouter', 'openrouter'),
            (call_groq, 'Groq', 'groq')
        ]
    elif role == 'judge':
        providers = [
            (call_gemini, 'Gemini', 'gemini'),
            (call_groq, 'Groq', 'groq'),
            (call_openrouter, 'OpenRouter', 'openrouter')
        ]
    else:
        providers = [
            (call_groq, 'Groq', 'groq'),
            (call_gemini, 'Gemini', 'gemini'),
            (call_openrouter, 'OpenRouter', 'openrouter')
        ]

    errors = []
    for func, name, code in providers:
        user_key_obj, custom_key = _get_user_api_key(user_obj, code)

        # 1. Спроба з власним ключем користувача (якщо є)
        if custom_key:
            try:
                text = func(system, user_prompt, api_key=custom_key)
                user_key_obj.last_used_at = timezone.now()
                user_key_obj.save(update_fields=['last_used_at'])
                return text, f"{name} (власний ключ)"
            except LLMError as e:
                logger.warning("[LLM] Власний ключ користувача для %s не спрацював: %s", name, e)
                if e.is_auth_error:
                    user_key_obj.is_valid = False
                    user_key_obj.save(update_fields=['is_valid'])
                    logger.info("[LLM] Ключ користувача для %s позначено як недійсний.", name)
                # Переходимо до спроби із системним ключем для цього ж провайдера

        # 2. Спроба із системним ключем сервера
        try:
            text = func(system, user_prompt)
            return text, name
        except Exception as e:
            logger.warning("[LLM] %s (серверний) не спрацював: %s", name, e)
            reason = _short_reason(e)
            errors.append(f"{name}: {reason}")
            continue

    err_summary = "; ".join(errors)
    raise LLMError(f"Усі ШІ-провайдери недоступні ({err_summary}).")
