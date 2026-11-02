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

