from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control rounded-0 border-dark'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control rounded-0 border-dark'

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email або Логін",
        widget=forms.TextInput(attrs={'class': 'form-control rounded-0 border-dark', 'placeholder': 'Email або Логін'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email або Логін'
        self.fields['password'].widget.attrs['class'] = 'form-control rounded-0 border-dark'