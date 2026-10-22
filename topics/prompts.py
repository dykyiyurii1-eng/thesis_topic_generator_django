import json
TOPICS_COUNT = 5
def sanitize(text):
    if not text:
        return ""
    return str(text).strip()[:500]
GENERATOR_SYSTEM = """Ти — досвідчений науковий керівник.
Згенеруй рівно 5 тем для кваліфікаційних робіт. Пиши українською.
Відповідай ВИКЛЮЧНО JSON-об'єктом, без тексту до або після нього.
Формат:
{"topics": [
  {"id": "r1_1", "title": "Назва теми", "why": "Чому це цікаво (до 240 символів)", "difficulty": "easy|medium|hard"}
]}
Складність (easy, medium або hard) має відповідати рівню освіти.
"""
CRITIC_SYSTEM = """Ти — Критик. Твоя роль — знайти слабкі місця в темах, а не хвалити.
Для кожної теми вкажи, що в ній не так: завелика, нереалізовна, застаріла, не відповідає рівню.
Пиши українською, 1–2 речення на тему.
Відповідай ВИКЛЮЧНО JSON-об'єктом:
{"reviews": [{"id": "r1_1", "verdict": "keep|revise|drop", "problems": "..."}]}
"""
JUDGE_SYSTEM = """Ти — Суддя в дебатах між Генератором і Критиком.
Тобі дано теми та зауваження Критика. Оціни кожну тему від 1 до 10,
враховуючи і якість теми, і те, чи справедливі зауваження Критика.
Пиши українською, 1–2 речення на тему.
Відповідай ВИКЛЮЧНО JSON-об'єктом:
{"verdicts": [{"id": "r1_1", "score": 8, "reason": "..."}]}
"""
def build_generator_input(ctx):
    specialty = ctx.get('specialty', '')
    education = ctx.get('education', 'bachelor')
    interests_list = ctx.get('interests', [])
    interests = ", ".join([i[0] for i in interests_list]) if interests_list else "не вказано"
    return f"Спеціальність: {specialty}. Рівень освіти: {education}. Інтереси: {interests}. Згенеруй {TOPICS_COUNT} тем."
def build_critic_input(ctx, topics):
    return (f"Спеціальність: {ctx.get('specialty', '')}.\n"
            f"Теми для аналізу:\n{json.dumps(topics, ensure_ascii=False)}")
def build_judge_input(ctx, items):
    return (f"Спеціальність: {ctx.get('specialty', '')}.\n"
            f"Теми та зауваження Критика:\n{json.dumps(items, ensure_ascii=False)}")