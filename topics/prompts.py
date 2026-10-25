TOPICS_COUNT = 5

def sanitize(text):
    if not text:
        return ""
    return str(text).strip()[:500]

GENERATOR_SYSTEM = """Ти — досвідчений науковий керівник.
Твоє завдання — згенерувати рівно 5 тем для кваліфікаційних робіт.
Ти ПОВИНЕН відповідати ВИКЛЮЧНО у форматі JSON-масиву. Без жодного тексту до або після масиву.
Формат:
[
  {"id": "r1_1", "title": "Назва теми", "why": "Чому це цікаво (до 240 символів)", "difficulty": "easy|medium|hard"}
]
Складність: easy, medium або hard. Вона відповідає рівню, а не вигадується.
Поверни ЛИШЕ цей JSON-масив."""

CRITIC_SYSTEM = """Ти — суворий науковий керівник. Оціни теми від 1 до 10.
Ти ПОВИНЕН відповідати ВИКЛЮЧНО у форматі JSON-масиву. Без жодного тексту до або після масиву.
Формат відповіді:
[
  {"id": "r1_1", "score": 8, "verdict": "keep|revise|drop", "problems": "Опис проблем"}
]
Поверни ЛИШЕ цей JSON-масив."""

JUDGE_SYSTEM = """Ти — незалежний суддя. Оціни теми від 1 до 10 на основі коментарів Критика.
Ти ПОВИНЕН відповідати ВИКЛЮЧНО у форматі JSON-масиву. Без жодного тексту до або після масиву.
Формат відповіді:
[
  {"id": "r1_1", "score": 8.5, "reason": "Чому така оцінка"}
]
Поверни ЛИШЕ цей JSON-масив."""

def build_generator_input(ctx):
    specialty = ctx.get('specialty', '')
    education = ctx.get('education', 'bachelor')
    interests_list = ctx.get('interests', [])
    interests = ", ".join([i[0] for i in interests_list]) if interests_list else "не вказано"
    
    return f"Спеціальність: {specialty}. Рівень освіти: {education}. Інтереси: {interests}. Згенеруй {TOPICS_COUNT} тем."

def build_critic_input(ctx, topics):
    return f"Спеціальність: {ctx.get('specialty', '')}.\nОціни ці теми:\n{topics}"

def build_judge_input(ctx, topics):
    return f"Спеціальність: {ctx.get('specialty', '')}.\nОціни ці теми:\n{topics}"