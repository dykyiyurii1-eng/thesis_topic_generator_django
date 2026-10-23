from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from .forms import RegistrationForm, EmailAuthenticationForm

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
            return redirect('topics:home')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/auth.html', {'reg_form': form})

class CustomLoginView(LoginView):
    template_name = 'accounts/auth.html'
    authentication_form = EmailAuthenticationForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reg_form'] = RegistrationForm()
        return context