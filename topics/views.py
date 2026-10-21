from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Interest, Question
from .services import process_quiz_results

def home_view(request):
    interests = Interest.objects.all()[:6]
    return render(request, 'topics/home.html', {'interests': interests})

def quiz_view(request):
    if request.method == 'POST':
        selected_options = request.POST.getlist('options')
        results = process_quiz_results(request.user, selected_options)
        
        if request.user.is_authenticated:
            return redirect('topics:home') 
        else:
            request.session['guest_interests'] = [i.id for i in results]
            return redirect('topics:home') 
            
    questions = Question.objects.prefetch_related('options').all()
    return render(request, 'topics/quiz.html', {'questions': questions})