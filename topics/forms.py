from django import forms
from .models import GenerationSession
from .prompts import GENERATOR_SYSTEM

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

class EmailSendForm(forms.Form):
    email = forms.EmailField(
        label="Введіть ваш Email",
        widget=forms.EmailInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )

def validate_json_mentioned(value):
    if 'json' not in value.lower():
        raise forms.ValidationError('У промпті має бути слово «JSON»: провайдери повертають відповідь у JSON-режимі.')

class SandboxForm(forms.Form):
    EDUCATION_CHOICES = (('school', 'Школа'), ('college', 'Коледж'), ('bachelor', 'Бакалавр'), ('master', 'Магістр'))
    
    system_prompt = forms.CharField(
        label='Системний промпт', 
        widget=forms.Textarea(attrs={'rows': 8, 'class': 'form-control rounded-0 border-dark font-monospace'}),
        initial=GENERATOR_SYSTEM, 
        max_length=4000, 
        validators=[validate_json_mentioned]
    )
    specialty = forms.CharField(
        label='Спеціальність', 
        max_length=100, 
        initial='Інформатика',
        widget=forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )
    education = forms.ChoiceField(
        label='Рівень освіти', 
        choices=EDUCATION_CHOICES, 
        initial='bachelor',
        widget=forms.Select(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )
    interests = forms.CharField(
        label='Інтереси (через кому)', 
        max_length=200, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )
    iterations = forms.IntegerField(
        label='Ітерацій (1–5)', 
        min_value=1, 
        max_value=5, 
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-0 border-dark font-monospace'})
    )