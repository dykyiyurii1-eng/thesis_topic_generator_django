from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse

class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    category = models.CharField(max_length=100, verbose_name="Категорія")

    class Meta:
        verbose_name = "Інтерес"
        verbose_name_plural = "Інтереси"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.category})"

    def get_absolute_url(self):
        return reverse('topics:interest_detail', kwargs={'slug': self.slug})

class StudentInterest(models.Model):
    SOURCE_CHOICES = (('quiz', 'Тест'), ('manual', 'Вручну'))
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interests', verbose_name="Студент")
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE, verbose_name="Інтерес")
    weight = models.FloatField(default=1.0, verbose_name="Вага")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='quiz', verbose_name="Джерело")
    is_default = models.BooleanField(default=False, verbose_name="За замовчуванням")

    class Meta:
        verbose_name = "Інтерес студента"
        verbose_name_plural = "Інтереси студентів"
        constraints = [
            models.UniqueConstraint(fields=['student', 'interest'], name='unique_student_interest')
        ]

    def __str__(self):
        return f"{self.student.username} - {self.interest.name}"

class Question(models.Model):
    text = models.CharField(max_length=255, verbose_name="Текст питання")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Питання"
        verbose_name_plural = "Питання"
        ordering = ['order']

    def __str__(self):
        return self.text

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options', verbose_name="Питання")
    text = models.CharField(max_length=255, verbose_name="Текст варіанту")

    class Meta:
        verbose_name = "Варіант відповіді"
        verbose_name_plural = "Варіанти відповідей"

    def __str__(self):
        return f"{self.question.text[:20]}... - {self.text}"

class OptionInterest(models.Model):
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name='interests', verbose_name="Варіант")
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE, verbose_name="Інтерес")
    weight = models.FloatField(default=1.0, verbose_name="Вага")

    class Meta:
        verbose_name = "Зв'язок варіанту та інтересу"
        verbose_name_plural = "Зв'язки варіантів та інтересів"

    def __str__(self):
        return f"{self.option.text[:15]}... + {self.interest.name}"

class GenerationSession(models.Model):
    INSTITUTION_CHOICES = (('school', 'Школа'), ('college', 'Коледж'), ('university', 'Університет'))
    LEVEL_CHOICES = (('bachelor', 'Бакалавр'), ('master', 'Магістр'))
    WORK_TYPE_CHOICES = (('practical', 'Практична'), ('theoretical', 'Теоретична'), ('mixed', 'Змішана'))
    STATUS_CHOICES = (('running', 'В процесі'), ('done', 'Завершено'), ('error', 'Помилка'))

    student = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sessions', verbose_name="Студент")
    guest_key = models.CharField(max_length=40, blank=True, verbose_name="Ключ гостя")
    specialty = models.CharField(max_length=300, verbose_name="Спеціальність")
    industry = models.CharField(max_length=100, blank=True, verbose_name="Індустрія")
    institution_type = models.CharField(max_length=20, choices=INSTITUTION_CHOICES, verbose_name="Тип закладу")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True, verbose_name="Рівень")
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES, verbose_name="Тип роботи")
    has_real_object = models.BooleanField(default=False, verbose_name="Реальний об'єкт")
    methods = models.CharField(max_length=200, blank=True, verbose_name="Методи")
    complexity = models.CharField(max_length=20, blank=True, verbose_name="Складність")
    goal = models.CharField(max_length=20, blank=True, verbose_name="Мета")
    keywords = models.CharField(max_length=200, blank=True, verbose_name="Ключові слова")
    rounds = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)], 
        default=1,
        verbose_name="Кількість кіл"
    )
    interests = models.ManyToManyField(Interest, related_name='sessions', blank=True, verbose_name="Інтереси")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")

    class Meta:
        verbose_name = "Сесія генерації"
        verbose_name_plural = "Сесії генерації"
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(rounds__gte=1) & models.Q(rounds__lte=3), name='rounds_between_1_and_3')
        ]
        permissions = [
            ('view_statistics', 'Може переглядати статистику'),
        ]

    def __str__(self):
        return f"Сесія {self.id} - {self.specialty}"

    def get_absolute_url(self):
        return reverse('topics:debate_page', kwargs={'session_id': self.pk})

class GeneratedTopic(models.Model):
    DIFFICULTY_CHOICES = (('easy', 'Легка'), ('medium', 'Середня'), ('hard', 'Складна'))
    
    session = models.ForeignKey(GenerationSession, on_delete=models.CASCADE, related_name='topics', verbose_name="Сесія")
    topic_key = models.CharField(max_length=20, verbose_name="Ключ теми")
    title = models.CharField(max_length=300, verbose_name="Заголовок")
    why = models.TextField(blank=True, verbose_name="Чому це цікаво")
    difficulty = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, blank=True, verbose_name="Складність")
    score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name="Оцінка")
    critic_comment = models.TextField(blank=True, verbose_name="Коментар критика")
    is_selected = models.BooleanField(default=False, verbose_name="Обрано")
    is_pinned = models.BooleanField(default=False, verbose_name="Закріплено")
    round = models.PositiveIntegerField(default=1, verbose_name="Коло")

    class Meta:
        verbose_name = "Згенерована тема"
        verbose_name_plural = "Згенеровані теми"
        ordering = ['-score']
        constraints = [
            models.UniqueConstraint(fields=['session', 'topic_key'], name='unique_session_topic_key'),
            models.CheckConstraint(condition=models.Q(score__gte=1) & models.Q(score__lte=10) | models.Q(score__isnull=True), name='score_between_1_and_10')
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('topics:topic_detail', kwargs={'pk': self.pk})

class AgentMessage(models.Model):
    AGENT_CHOICES = (('generator', 'Генератор'), ('critic', 'Критик'), ('judge', 'Суддя'), ('system', 'Система'), ('user', 'Користувач'))
    session = models.ForeignKey(GenerationSession, on_delete=models.CASCADE, related_name='messages', verbose_name="Сесія")
    agent = models.CharField(max_length=20, choices=AGENT_CHOICES, verbose_name="Агент")
    provider = models.CharField(max_length=50, blank=True, verbose_name="Провайдер")
    content = models.TextField(verbose_name="Вміст")
    sequence_number = models.PositiveIntegerField(verbose_name="Номер по порядку")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")

    class Meta:
        verbose_name = "Повідомлення агента"
        verbose_name_plural = "Повідомлення агентів"
        ordering = ['sequence_number']
        constraints = [
            models.UniqueConstraint(fields=['session', 'sequence_number'], name='unique_session_sequence')
        ]

    def __str__(self):
        return f"{self.get_agent_display()} - {self.session.id}"

class HomePageImage(models.Model):
    image = models.ImageField(upload_to='home_images/', verbose_name="Картинка на головну")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return "Картинка на головну"