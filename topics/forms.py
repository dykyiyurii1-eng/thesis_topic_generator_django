from django import forms
from .models import GenerationSession
from .prompts import GENERATOR_SYSTEM, SANDBOX_GENERATOR_SYSTEM


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
    