from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Interest, Question
from .services import process_quiz_results
from django.shortcuts import render, redirect
from .forms import GenerationSessionForm

from django.http import JsonResponse
from .models import Interest

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


def session_create_view(request):
    if request.method == 'POST':
        form = GenerationSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            if request.user.is_authenticated:
                session.student = request.user
            else:
                if not request.session.session_key:
                    request.session.create()
                session.guest_key = request.session.session_key
            session.status = 'running'
            session.save()
            form.save_m2m()
            return redirect('topics:home')
    else:
        form = GenerationSessionForm()
    
    return render(request, 'topics/generate.html', {'form': form})

def suggest_interests_view(request):
    query = request.GET.get('q', '')
    if query:
        interests = Interest.objects.filter(name__icontains=query)[:10]
    else:
        interests = Interest.objects.all()[:10]
        
    results = [{'id': i.id, 'text': f"{i.name} ({i.category})"} for i in interests]
    return JsonResponse({'results': results})