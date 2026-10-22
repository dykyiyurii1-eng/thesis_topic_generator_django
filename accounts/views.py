from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('topics:home')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})