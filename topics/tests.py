from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class CryptoRoundtripTest(TestCase):
    """Шифрування → розшифрування повертає оригінальний рядок."""

    def test_encrypt_decrypt(self):
        from topics.crypto import encrypt, decrypt
        plain = 'test-api-key-sk-1234567890abcdef'
        self.assertEqual(decrypt(encrypt(plain)), plain)

    def test_different_ciphertexts(self):
        """Fernet використовує випадковий IV — два шифрування дають різні результати."""
        from topics.crypto import encrypt
        plain = 'same-key'
        self.assertNotEqual(encrypt(plain), encrypt(plain))


class UserApiKeyIsolationTest(TestCase):
    """Один користувач не бачить ключів іншого."""

    def setUp(self):
        self.user1 = User.objects.create_user('user1_byok', password='pass1234!')
        self.user2 = User.objects.create_user('user2_byok', password='pass1234!')
        from topics.crypto import encrypt
        from topics.models import UserApiKey
        self.key = UserApiKey.objects.create(
            user=self.user1,
            provider='groq',
            encrypted_key=encrypt('sk-groq-supersecret1234'),
            last4='1234',
            is_valid=True,
        )

    def test_other_user_cannot_see_key(self):
        self.client.force_login(self.user2)
        resp = self.client.get(reverse('topics:api_keys'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'sk-groq-supersecret1234')
        self.assertNotContains(resp, '1234')  # last4 of user1's key

    def test_anon_redirected_to_login(self):
        resp = self.client.get(reverse('topics:api_keys'))
        self.assertRedirects(resp, '/accounts/login/?next=/api-keys/')

    def test_key_not_in_owner_response(self):
        """Власник бачить лише замасковану версію, а не повний ключ."""
        self.client.force_login(self.user1)
        resp = self.client.get(reverse('topics:api_keys'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'sk-groq-supersecret1234')
        # Mask is shown:
        self.assertContains(resp, '1234')

    def test_delete_own_key(self):
        self.client.force_login(self.user1)
        resp = self.client.post(
            reverse('topics:api_key_delete', args=[self.key.id])
        )
        self.assertRedirects(resp, reverse('topics:api_keys'))
        from topics.models import UserApiKey
        self.assertFalse(UserApiKey.objects.filter(id=self.key.id).exists())

    def test_delete_other_user_key_returns_404(self):
        self.client.force_login(self.user2)
        resp = self.client.post(
            reverse('topics:api_key_delete', args=[self.key.id])
        )
        self.assertEqual(resp.status_code, 404)


class AdminActivityAccessTest(TestCase):
    """Перевірка розмежування доступу до аналітичної адмін-панелі."""

    def setUp(self):
        self.staff_user = User.objects.create_user('admin_user', password='pass', is_staff=True)
        self.student_user = User.objects.create_user('student_user', password='pass', is_staff=False)

    def test_anon_redirected_to_admin_login(self):
        resp = self.client.get(reverse('topics:admin_activity'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/login/', resp.url)

    def test_regular_user_redirected_to_admin_login(self):
        self.client.force_login(self.student_user)
        resp = self.client.get(reverse('topics:admin_activity'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/login/', resp.url)

    def test_staff_user_can_access(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse('topics:admin_activity'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'АКТИВНІСТЬ КОРИСТУВАЧІВ')
        self.assertContains(resp, 'student_user')


class CustomErrorPagesTest(TestCase):
    """Перевірка доступності сторінок кастомних помилок."""

    def test_custom_404_template(self):
        resp = self.client.get('/404/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'СТОРІНКУ НЕ ЗНАЙДЕНО')
        self.assertContains(resp, '404')

    def test_custom_500_template(self):
        resp = self.client.get('/500/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ВНУТРІШНЯ ПОМИЛКА СЕРВЕРА')
        self.assertContains(resp, '500')


class TopicLikeAndInterventionTest(TestCase):
    """Перевірка функціоналу лайків та втручання користувача."""

    def setUp(self):
        self.user = User.objects.create_user('tester', password='pass1234!')
        from topics.models import GenerationSession, GeneratedTopic
        self.session = GenerationSession.objects.create(
            student=self.user,
            specialty='Комп’ютерні науки',
            institution_type='university',
            work_type='practical',
            rounds=3
        )
        self.topic = GeneratedTopic.objects.create(
            session=self.session,
            topic_key='t1',
            title='Тестова тема',
            is_liked=False
        )

    def test_toggle_like_topic(self):
        self.client.force_login(self.user)
        # 1-й виклик: ставимо лайк
        resp = self.client.post(reverse('topics:like_topic', args=[self.topic.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('liked'))
        self.topic.refresh_from_db()
        self.assertTrue(self.topic.is_liked)

        # 2-й виклик: знімаємо лайк
        resp2 = self.client.post(reverse('topics:like_topic', args=[self.topic.id]))
        self.assertEqual(resp2.status_code, 200)
        self.assertFalse(resp2.json().get('liked'))
        self.topic.refresh_from_db()
        self.assertFalse(self.topic.is_liked)
