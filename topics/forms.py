from django import forms
from .models import GenerationSession, UserApiKey
from .prompts import GENERATOR_SYSTEM, SANDBOX_GENERATOR_SYSTEM
from .key_validation import validate_provider_key


class GenerationSessionForm(forms.ModelForm):
    class Meta:
        model = GenerationSession
        fields = ['specialty', 'industry', 'institution_type', 'level', 'work_type', 'rounds', 'has_real_object', 'methods', 'complexity', 'goal', 'keywords', 'interests']
        widgets = {
            'specialty': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'industry': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'institution_type': forms.Select(attrs={'class': 'form-select rounded-0 border-dark font-monospace'}),
            'level': forms.Select(attrs={'class': 'form-select rounded-0 border-dark font-monospace'}),
            'work_type': forms.Select(attrs={'class': 'form-select rounded-0 border-dark font-monospace'}),
            'rounds': forms.NumberInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace', 'min': 1, 'max': 3}),
            'has_real_object': forms.CheckboxInput(attrs={'class': 'form-check-input rounded-0 border-dark'}),
            'methods': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'complexity': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'goal': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
            'interests': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['institution_type', 'level', 'work_type']:
            if field_name in self.fields:
                choices = list(self.fields[field_name].choices)
                if choices and choices[0][0] == '':
                    choices[0] = ('', '- Оберіть варіант -')
                    self.fields[field_name].choices = choices

    def clean_specialty(self):
        value = self.cleaned_data.get('specialty', '').strip()
        if len(value) < 3:
            raise forms.ValidationError('Спеціальність має містити щонайменше 3 символи.')
        return value


class EmailSendForm(forms.Form):
    email = forms.EmailField(
        label="Введіть ваш Email",
        widget=forms.EmailInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )


def validate_json_mentioned(value):
    if 'json' not in value.lower():
        raise forms.ValidationError('У промпті має бути слово «JSON»: провайдери повертають відповідь у JSON-режимі.')


class SandboxForm(forms.Form):
    system_prompt = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 12,
            'class': 'form-control rounded-0 border-dark font-monospace',
        }),
        initial=SANDBOX_GENERATOR_SYSTEM,
        label='Системний промпт',
        validators=[validate_json_mentioned],
    )
    specialty = forms.CharField(
        max_length=200,
        label='Спеціальність',
        widget=forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
    )
    education = forms.CharField(
        max_length=100,
        label='Освітній рівень',
        widget=forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
    )
    interests = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control rounded-0 border-dark font-monospace',
        }),
        label='Інтереси (через кому)',
    )
    iterations = forms.IntegerField(
        min_value=1, max_value=5, initial=2,
        label='Кількість ітерацій',
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'}),
    )


class UserApiKeyForm(forms.Form):
    provider = forms.ChoiceField(
        choices=UserApiKey.PROVIDER_CHOICES,
        label="Провайдер",
        widget=forms.Select(attrs={'class': 'form-select rounded-0 border-dark font-monospace'})
    )
    api_key = forms.CharField(
        label="API-ключ",
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control rounded-0 border-dark font-monospace',
                'placeholder': 'Вставте ваш API-ключ сюди',
                'autocomplete': 'off',
            },
            render_value=False
        )
    )

    def clean_api_key(self):
        key = self.cleaned_data.get('api_key', '').strip()
        if len(key) < 8:
            raise forms.ValidationError('API-ключ занадто короткий.')
        return key

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get('provider')
        api_key = cleaned_data.get('api_key')

        if provider and api_key:
            is_valid, error_msg = validate_provider_key(provider, api_key)
            if not is_valid:
                raise forms.ValidationError(error_msg)

        return cleaned_data
