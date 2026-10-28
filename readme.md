# Генератор тем кваліфікаційних робіт

Веб-застосунок на Django, у якому три ШІ-агенти ведуть дебати про теми кваліфікаційних робіт, а користувач бачить хід дебатів у реальному часі.

- **Генератор** (Gemini) пропонує 5 тем.
- **Критик** (Groq) шукає слабкі місця.
- **Суддя** (OpenRouter) ставить оцінки від 1 до 10.

Якщо основний провайдер недоступний, спрацьовує запасний ланцюжок. Користувач обирає спеціальність, тип закладу, інтереси та кількість кіл (1–3). Для тих, хто не знає, що йому цікаво, є тест інтересів.

## Можливості

- Тест інтересів (30 інтересів, 8 питань із вагами, початкові дані додає data-міграція).
- Форма генерації з автодоповненням і вибором інтересів.
- Дебати агентів у реальному часі (Server-Sent Events), повний діалог зберігається в базі.
- Пробна генерація для гостя без реєстрації.
- Реєстрація, вхід і вихід.
- Історія власних сесій: список, пошук, пагінація, перегляд, редагування, видалення.
- Надсилання згенерованих тем на email.
- Закріплення тем (API готове, інтерфейс у розробці).

## Технології

| Компонент | Версія |
|---|---|
| Python | 3.14 |
| Django | 6.1.2 |
| СУБД | MySQL 8.4.11 |
| Драйвер БД | mysqlclient 2.3.0 |
| Інтерфейс | Bootstrap 5 + власний CSS |
| ШІ | Gemini, Groq, OpenRouter (REST API, `requests`) |

Точні версії всіх пакетів зафіксовано в `requirements.txt`.

## Структура проєкту

```
thesis_topic/
├── manage.py
├── config/            # налаштування, головні маршрути
├── accounts/          # реєстрація, вхід, вихід
├── topics/            # основний застосунок
│   ├── models.py      # моделі
│   ├── views.py       # представлення (CBV і FBV)
│   ├── forms.py       # форми
│   ├── services.py    # логіка дебатів і тесту інтересів
│   ├── llm.py         # виклики Gemini / Groq / OpenRouter
│   ├── prompts.py     # системні промпти (лише на сервері)
│   ├── urls.py
│   └── migrations/    # у т. ч. data-міграція з початковими даними
├── templates/         # base.html, topics/...
├── static/css/        # brytal_style.css
├── media/             # завантажені картинки (не в git)
├── .env.example       # назви змінних оточення без значень
└── requirements.txt
```

## Запуск

### 1. Вимоги

- Python 3.14
- MySQL 8.4 (у проєкті використано порт 3307)
- Безкоштовні API-ключі: [Google AI Studio](https://aistudio.google.com), [Groq](https://console.groq.com), [OpenRouter](https://openrouter.ai)

### 2. Встановлення

```powershell
git clone https://github.com/dykyiyurii1-eng/thesis_topic_generator_django.git
cd thesis_topic_generator_django\thesis_topic

py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. База даних

У MySQL створіть базу й користувача:

```sql
CREATE DATABASE thesis_topics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'thesis_user'@'localhost' IDENTIFIED BY '<пароль>';
GRANT ALL PRIVILEGES ON thesis_topics.* TO 'thesis_user'@'localhost';
GRANT ALL PRIVILEGES ON test_thesis_topics.* TO 'thesis_user'@'localhost';
FLUSH PRIVILEGES;
```

Права на `test_thesis_topics` потрібні, щоб Django міг створювати тестову базу.

### 4. Змінні оточення

```powershell
copy .env.example .env
```

Заповніть `.env` (файл у `.gitignore`, у репозиторій не потрапляє):

| Змінна | Призначення |
|---|---|
| `DJANGO_SECRET_KEY` | секретний ключ Django |
| `DEBUG` | `True` для розробки |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | підключення до MySQL |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Генератор (напр. `gemini-2.5-flash`) |
| `GROQ_API_KEY`, `GROQ_MODEL` | Критик (напр. `openai/gpt-oss-120b`) |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Суддя (безкоштовна модель із суфіксом `:free`) |
| `<змінні пошти>` | налаштування SMTP для надсилання листів |

Кожна змінна має стояти на окремому рядку, без лапок і без дублів.

### 5. Міграції та запуск

```powershell
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```

Застосунок відкриється на http://127.0.0.1:8000/. Адмінка: http://127.0.0.1:8000/admin/. Картинку для головної сторінки можна завантажити в адмінці (модель «Картинка на головну»).

## Основні маршрути

| URL | Ім'я | Призначення |
|---|---|---|
| `/` | `topics:home` | головна |
| `/quiz/` | `topics:quiz` | тест інтересів |
| `/trial/` | `topics:trial` | пробна генерація для гостя |
| `/generate/` | `topics:generate` | нова сесія (потрібен вхід) |
| `/session/<id>/` | `topics:debate_page` | сторінка дебатів |
| `/session/<id>/stream/` | `topics:debate_stream` | потік подій (SSE) |
| `/session/<id>/email/` | `topics:send_email` | надсилання тем на пошту |
| `/topic/<id>/pin/` | `topics:pin_topic` | закріпити тему (POST) |
| `/history/` | `topics:history` | історія сесій |
| `/history/<pk>/` | `topics:history_detail` | деталі сесії |
| `/history/<pk>/edit/` | `topics:session_edit` | редагування |
| `/history/<pk>/delete/` | `topics:session_delete` | видалення |
| `/interests/suggest/` | `topics:suggest_interests` | підказки інтересів (JSON) |

## Безпека

- Ключі API, `SECRET_KEY` і дані БД лише в `.env`, у репозиторії тільки `.env.example`.
- Системні промпти й виклики ШІ виконуються на сервері, браузер ключів не бачить.
- Доступ до сесій перевіряється на сервері: автор бачить свої, гість лише свою пробну (за ключем сесії).
- Текст, який пише ШІ, виводиться без `|safe` і без `innerHTML`.
- Усі форми мають `{% csrf_token %}`, ORM використовується без склеювання SQL.

## Тестування

```powershell
py manage.py test
```



## Автор

Дикий Юрій