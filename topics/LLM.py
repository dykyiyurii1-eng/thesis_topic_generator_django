import os
import json
import time
import requests
from dotenv import load_dotenv
load_dotenv()
class LLMError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after
def is_api_configured():
    return bool(os.getenv('GEMINI_API_KEY') or os.getenv('GROQ_API_KEY') or os.getenv('OPENROUTER_API_KEY'))
def parse_json_response(raw):
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
def call_gemini(system, user, temperature=0.7):
    api_key = os.getenv('GEMINI_API_KEY')
    model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    if not api_key:
        raise LLMError("Ключ Gemini не налаштовано.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "maxOutputTokens": 2048
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі Gemini: {e}")
    if response.status_code == 429:
        retry_after = response.headers.get('retry-after', 5)
        raise LLMError("Перевищено ліміт запитів Gemini.", retry_after=int(retry_after))
    elif response.status_code in (400, 401, 403, 404):
        raise LLMError(f"Помилка доступу до Gemini (Код {response.status_code}). Перевірте API-ключ.")
    elif response.status_code != 200:
        raise LLMError(f"Помилка сервера Gemini: {response.status_code}")
    try:
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від Gemini.")
def call_groq(system, user, temperature=0.4):
    api_key = os.getenv('GROQ_API_KEY')
    model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
    if not api_key:
        raise LLMError("Ключ Groq не налаштовано.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі Groq: {e}")
    if response.status_code == 429:
        retry_after = response.headers.get('retry-after', 5)
        raise LLMError("Перевищено ліміт запитів Groq.", retry_after=int(retry_after))
    elif response.status_code in (400, 401, 403, 404):
        raise LLMError(f"Помилка доступу до Groq (Код {response.status_code}). Перевірте API-ключ.")
    elif response.status_code != 200:
        raise LLMError(f"Помилка сервера Groq: {response.status_code}")
    try:
        data = response.json()
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від Groq.")
def call_openrouter(system, user, temperature=0.7):
    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3-8b-instruct:free')
    if not api_key:
        raise LLMError("Ключ OpenRouter не налаштовано.")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMError(f"Помилка мережі OpenRouter: {e}")
    if response.status_code == 429:
        retry_after = response.headers.get('retry-after', 5)
        raise LLMError("Перевищено ліміт запитів OpenRouter.", retry_after=int(retry_after))
    elif response.status_code in (400, 401, 403, 404):
        raise LLMError(f"Помилка доступу до OpenRouter (Код {response.status_code}). Перевірте API-ключ.")
    elif response.status_code != 200:
        raise LLMError(f"Помилка сервера OpenRouter: {response.status_code}")
    try:
        data = response.json()
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise LLMError("Неочікуваний формат відповіді від OpenRouter.")
def call_with_fallback(role, system, user):
    if role == 'generator':
        providers = [(call_gemini, 'Gemini'), (call_openrouter, 'OpenRouter'), (call_groq, 'Groq')]
    elif role == 'critic':
        providers = [(call_groq, 'Groq'), (call_gemini, 'Gemini'), (call_openrouter, 'OpenRouter')]
    else:  # judge
        providers = [(call_openrouter, 'OpenRouter'), (call_groq, 'Groq'), (call_gemini, 'Gemini')]
    last_error = None
    for func, name in providers:
        try:
            text = func(system, user)
            return text, name
        except LLMError as e:
            last_error = e
            if e.retry_after and e.retry_after <= 20:
                time.sleep(e.retry_after)
                try:
                    text = func(system, user)
                    return text, name
                except LLMError:
                    pass
            continue
    raise LLMError(f"Усі ШІ-провайдери недоступні. Остання помилка: {last_error}")