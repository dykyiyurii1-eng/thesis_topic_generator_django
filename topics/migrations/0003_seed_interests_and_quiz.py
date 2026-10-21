from django.db import migrations

INTERESTS = [
    ('Штучний інтелект', 'ai', 'Дані й ШІ'),
    ('Машинне навчання', 'machine-learning', 'Дані й ШІ'),
    ('Аналіз даних', 'data-analysis', 'Дані й ШІ'),
    ('Обробка природної мови', 'nlp', 'Дані й ШІ'),
    ('Комп’ютерний зір', 'computer-vision', 'Дані й ШІ'),
    ('Чат-боти', 'chatbots', 'Дані й ШІ'),
    ('Веб-розробка', 'web-development', 'Веб'),
    ('Мобільні застосунки', 'mobile-apps', 'Веб'),
    ('UX/UI дизайн', 'ux-ui-design', 'Веб'),
    ('Електронна комерція', 'e-commerce', 'Веб'),
    ('Backend та API', 'backend-api', 'Веб'),
    ('Хмарні технології', 'cloud', 'Інфраструктура'),
    ('DevOps', 'devops', 'Інфраструктура'),
    ('Інтернет речей', 'iot', 'Інфраструктура'),
    ('Бази даних', 'databases', 'Інфраструктура'),
    ('Комп’ютерні мережі', 'networking', 'Інфраструктура'),
    ('Робототехніка', 'robotics', 'Інфраструктура'),
    ('Кібербезпека', 'cybersecurity', 'Безпека'),
    ('Захист персональних даних', 'data-privacy', 'Безпека'),
    ('Освітні технології', 'edtech', 'Освіта'),
    ('Дистанційне навчання', 'e-learning', 'Освіта'),
    ('Геймифікація навчання', 'gamification', 'Освіта'),
    ('Бізнес-аналітика', 'business-analytics', 'Бізнес-аналітика'),
    ('Управління проєктами', 'project-management', 'Бізнес-аналітика'),
    ('Фінансові технології', 'fintech', 'Бізнес-аналітика'),
    ('Автоматизація процесів', 'process-automation', 'Бізнес-аналітика'),
    ('Маркетинг та SEO', 'marketing-seo', 'Бізнес-аналітика'),
    ('Розробка ігор', 'game-development', 'Ігри'),
    ('Віртуальна реальність', 'vr-ar', 'Ігри'),
    ('Інтерактивні медіа', 'interactive-media', 'Ігри'),
]

QUESTIONS = [
    ('Що вам цікавіше робити в проєкті?', [
        ('Навчати програму знаходити закономірності в даних', [('machine-learning', 2), ('data-analysis', 1)]),
        ('Створювати зручний сайт чи застосунок', [('web-development', 2), ('ux-ui-design', 1)]),
        ('Захищати систему від зловмисників', [('cybersecurity', 2), ('data-privacy', 1)]),
        ('Налаштовувати серверну інфраструктуру', [('cloud', 2), ('devops', 1)]),
    ]),
    ('Яке завдання виглядає найприємнішим?', [
        ('Допомогти учням краще засвоювати матеріал', [('edtech', 2), ('e-learning', 1)]),
        ('Зробити гру чи інтерактивну історію', [('game-development', 2), ('interactive-media', 1)]),
        ('Автоматизувати рутинну роботу компанії', [('process-automation', 2), ('business-analytics', 1)]),
        ('Створити розумного помічника для спілкування', [('chatbots', 2), ('nlp', 1)]),
    ]),
    ('З чого ви б почали проєкт?', [
        ('Зібрав би дані й побудував графіки', [('data-analysis', 2), ('business-analytics', 1)]),
        ('Намалював би макет інтерфейсу', [('ux-ui-design', 2), ('web-development', 1)]),
        ('Спроєктував би базу даних', [('databases', 2), ('backend-api', 1)]),
        ('Підключив би датчики й пристрої', [('iot', 2), ('robotics', 1)]),
    ]),
    ('Який результат вас найбільше надихає?', [
        ('Програма, що розпізнає зображення', [('computer-vision', 2), ('ai', 1)]),
        ('Сайт, яким користуються тисячі людей', [('web-development', 2), ('e-commerce', 1)]),
        ('Застосунок на телефоні', [('mobile-apps', 2)]),
        ('Віртуальний світ, у який хочеться зануритись', [('vr-ar', 2), ('game-development', 1)]),
    ]),
    ('Що вам ближче в роботі з людьми?', [
        ('Пояснювати складне простими словами', [('edtech', 2), ('gamification', 1)]),
        ('Планувати роботу команди й терміни', [('project-management', 2), ('business-analytics', 1)]),
        ('З’ясовувати, що потрібно клієнтам', [('marketing-seo', 2), ('business-analytics', 1)]),
        ('Працювати самому над технічною задачею', [('backend-api', 2), ('networking', 1)]),
    ]),
    ('Яка тема здається найактуальнішою?', [
        ('Штучний інтелект у повсякденному житті', [('ai', 2), ('nlp', 1)]),
        ('Безпека персональних даних', [('data-privacy', 2), ('cybersecurity', 1)]),
        ('Онлайн-платежі та фінанси', [('fintech', 2), ('e-commerce', 1)]),
        ('Дистанційна освіта', [('e-learning', 2), ('edtech', 1)]),
    ]),
    ('Яка технологія викликає найбільшу цікавість?', [
        ('Нейронні мережі', [('machine-learning', 2), ('ai', 1)]),
        ('Хмарні сервіси', [('cloud', 2), ('devops', 1)]),
        ('Розумні пристрої', [('iot', 2), ('robotics', 1)]),
        ('Комп’ютерні мережі', [('networking', 2), ('cybersecurity', 1)]),
    ]),
    ('Який формат роботи ви обрали б?', [
        ('Дослідити дані й зробити висновки', [('data-analysis', 2), ('machine-learning', 1)]),
        ('Розробити готовий продукт з інтерфейсом', [('web-development', 1), ('mobile-apps', 1), ('ux-ui-design', 1)]),
        ('Автоматизувати процес або сервіс', [('process-automation', 2), ('devops', 1)]),
        ('Створити розвагу чи навчальну гру', [('gamification', 2), ('game-development', 1)]),
    ]),
]


def seed(apps, schema_editor):
    Interest = apps.get_model('topics', 'Interest')
    Question = apps.get_model('topics', 'Question')
    Option = apps.get_model('topics', 'Option')
    OptionInterest = apps.get_model('topics', 'OptionInterest')

    by_slug = {}
    for name, slug, category in INTERESTS:
        obj, _ = Interest.objects.get_or_create(
            slug=slug, defaults={'name': name, 'category': category}
        )
        by_slug[slug] = obj

    for order, (text, options) in enumerate(QUESTIONS, start=1):
        question, _ = Question.objects.get_or_create(text=text, defaults={'order': order})
        for option_text, links in options:
            option, _ = Option.objects.get_or_create(question=question, text=option_text)
            for slug, weight in links:
                OptionInterest.objects.get_or_create(
                    option=option, interest=by_slug[slug], defaults={'weight': weight}
                )


def unseed(apps, schema_editor):
    Interest = apps.get_model('topics', 'Interest')
    Question = apps.get_model('topics', 'Question')
    Question.objects.filter(text__in=[q[0] for q in QUESTIONS]).delete()
    Interest.objects.filter(slug__in=[i[1] for i in INTERESTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0002_interest_option_question_generationsession_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]