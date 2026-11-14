import logging
import requests

logger = logging.getLogger(__name__)

USER_FACING_INVALID_MSG = (
    "Не вдалося підтвердити дійсність API-ключа. "
    "Будь ласка, перевірте правильність введеного ключа або стан вашого облікового запису у провайдера."
)


def validate_provider_key(provider: str, api_key: str) -> tuple[bool, str]:
    """
    Виконує швидкий та дешевий перевірочний запит до API провайдера для валідації ключа.
    Повертає (is_valid, error_message).
    Якщо ключ недійсний або сталася помилка, повертає зрозуміле повідомлення БЕЗ технічного тексту провайдера.
    """
    key = (api_key or "").strip()
    if not key:
        return False, "API-ключ не може бути порожнім."

    timeout = (4, 10)

    try:
        if provider == 'gemini':
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                return True, ""
            logger.warning("[KEY_VALIDATION] Gemini rejected key: status=%s", resp.status_code)
            return False, USER_FACING_INVALID_MSG

        elif provider == 'groq':
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {key}"}
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return True, ""
            logger.warning("[KEY_VALIDATION] Groq rejected key: status=%s", resp.status_code)
            return False, USER_FACING_INVALID_MSG

        elif provider == 'openrouter':
            url = "https://openrouter.ai/api/v1/auth/key"
            headers = {"Authorization": f"Bearer {key}"}
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return True, ""
            logger.warning("[KEY_VALIDATION] OpenRouter rejected key: status=%s", resp.status_code)
            return False, USER_FACING_INVALID_MSG

        else:
            return False, "Невідомий провайдер."

    except requests.RequestException as e:
        logger.warning("[KEY_VALIDATION] Мережева помилка при перевірці ключа (%s): %s", provider, e)
        return False, "Не вдалося з'єднатися із сервером провайдера для перевірки ключа. Спробуйте пізніше."

