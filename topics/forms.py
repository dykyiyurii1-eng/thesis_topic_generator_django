from django import forms
from .models import GenerationSession

class GenerationSessionForm(forms.ModelForm):
    class Meta:
        model = GenerationSession
        fields = ['specialty', 'institution_type', 'level', 'work_type', 'rounds', 'interests']
        widgets = {
            'specialty': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Наприклад: Інформаційні технології'}),
            'institution_type': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'work_type': forms.Select(attrs={'class': 'form-select'}),
            'rounds': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 3}),
            'interests': forms.CheckboxSelectMultiple(),
        }