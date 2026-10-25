from datetime import timedelta
import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (ListView, DetailView, CreateView,
                                  UpdateView, DeleteView)

from .forms import GenerationSessionForm, EmailSendForm, SandboxForm
from .models import (Interest, Question, GenerationSession, GeneratedTopic,
                     AgentMessage, HomePageImage, StudentInterest)
from .services import process_quiz_results, run_debate_pipeline
from .llm import call_with_fallback, LLMError
from .prompts import build_generator_input


def sessions_for_request(request):
    if request.user.is_authenticated:
        return GenerationSession.objects.filter(student=request.user)
    key = request.session.session_key
    if not key:
        return GenerationSession.objects.none()
    return GenerationSession.objects.filter(student__isnull=True, guest_key=key)


def home_view(request):
    interests = Interest.objects.all()[:6]
    hero_image = HomePageImage.objects.filter(is_active=True).first()
    ai_models = {
        'gemini': os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
        'groq': os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        'openrouter': os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct:free')
    }
    return render(request, 'topics/home.html', {
        'interests': interests, 
        'hero_image': hero_image,
        'ai_models': ai_models
    })


def quiz_view(request):
    if request.method == 'POST':
        selected_options = request.POST.getlist('options')
        results = process_quiz_results(request.user, selected_options)
        
        if request.user.is_authenticated:
            user_interests = StudentInterest.objects.filter(student=request.user, interest__in=results)
            for interest in results:
                si = user_interests.filter(interest=interest).first()
                interest.is_default = si.is_default if si else False
        else:
            request.session['guest_interests'] = [i.id for i in results]
            
        return render(request, 'topics/quiz.html', {
            'questions': Question.objects.prefetch_related('options').all(), 
            'results': results
        })
        
    questions = Question.objects.prefetch_related('options').all()
    return render(request, 'topics/quiz.html', {'questions': questions})


@login_required
@require_POST
def save_default_interests_view(request):
    selected_ids = request.POST.getlist('default_interests')
    StudentInterest.objects.filter(student=request.user).update(is_default=False)
    if selected_ids:
        StudentInterest.objects.filter(student=request.user, interest_id__in=selected_ids).update(is_default=True)
    messages.success(request, 'Ваші інтереси за замовчуванням оновлено.')
    return redirect('topics:home')


def suggest_interests_view(request):
    query = request.GET.get('q', '').strip()
    if query:
        interests = Interest.objects.filter(name__icontains=query)[:10]
    else:
        interests = Interest.objects.all()[:10]
    results = [{'id': i.id, 'text': f"{i.name} ({i.category})"} for i in interests]
    return JsonResponse({'results': results})


def debate_stream_view(request, session_id):
    session = get_object_or_404(sessions_for_request(request), id=session_id)
    try:
        round_no = int(request.GET.get('round', 1))
    except ValueError:
        return JsonResponse({'error': 'Некоректний номер кола.'}, status=400)
    response = StreamingHttpResponse(run_debate_pipeline(session, round_no),
                                     content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response


@login_required
@require_POST
def pin_topic_view(request, topic_id):
    topic = get_object_or_404(GeneratedTopic, id=topic_id, session__student=request.user)
    topic.is_pinned = not topic.is_pinned
    topic.save(update_fields=['is_pinned'])
    return JsonResponse({'pinned': topic.is_pinned})


def trial_generate_view(request):
    if request.user.is_authenticated:
        return redirect('topics:generate')
    if not request.session.session_key:
        request.session.create()
    used = GenerationSession.objects.filter(
        student__isnull=True, guest_key=request.session.session_key).first()
    if used:
        messages.info(request, 'Пробну генерацію вже використано. Зареєструйтесь, щоб продовжити.')
        return redirect('topics:debate_page', session_id=used.id)

    if request.method == 'POST':
        form = GenerationSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.guest_key = request.session.session_key
            session.status = 'running'
            session.specialty = request.POST.get('specialty', '')
            session.save()
            form.save_m2m()
            
            custom_interests = request.POST.get('custom_interests', '')
            if custom_interests:
                request.session['guest_custom_interests'] = custom_interests
                
            return redirect('topics:debate_page', session_id=session.id)
    else:
        form = GenerationSessionForm()
    return render(request, 'topics/generate.html', {'form': form})


def send_session_email_view(request, session_id):
    session = get_object_or_404(sessions_for_request(request), id=session_id)
    if request.method == 'POST':
        form = EmailSendForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            lines = [f"Ваші згенеровані теми для спеціальності '{session.specialty}':\n"]
            for i, t in enumerate(session.topics.all(), 1):
                lines.append(f"{i}. {t.title}\n   Оцінка: {t.score or '—'}/10\n   Коментар: {t.critic_comment}\n")
            send_mail(
                subject="Ваші згенеровані теми",
                message="\n".join(lines),
                from_email='noreply@thesis-gen.com',
                recipient_list=[email],
            )
            messages.success(request, f'Теми надіслано на {email}.')
            return redirect('topics:debate_page', session_id=session.id)
    else:
        form = EmailSendForm()
    return render(request, 'topics/email_form.html', {'form': form, 'session': session})


@login_required
@require_POST
def bulk_delete_sessions(request):
    session_ids = request.POST.getlist('session_ids')
    if session_ids:
        GenerationSession.objects.filter(id__in=session_ids, student=request.user).delete()
        messages.success(request, f'Видалено {len(session_ids)} сесій.')
    return redirect('topics:history')


@staff_member_required
def sandbox_view(request):
    if request.method == 'POST':
        form = SandboxForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ctx = {
                'specialty': cd['specialty'],
                'education': cd['education'],
                'interests': [(i.strip(), 'high') for i in cd['interests'].split(',') if i.strip()],
            }
            
            log = []
            for n in range(1, cd['iterations'] + 1):
                try:
                    raw, provider = call_with_fallback(
                        'generator', cd['system_prompt'], build_generator_input(ctx)
                    )
                    log.append({'n': n, 'provider': provider, 'raw': raw})
                except LLMError as e:
                    log.append({'n': n, 'error': str(e)})
                    break
   
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'log': log})
            
            return render(request, 'topics/sandbox.html', {'form': form, 'log': log})
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = SandboxForm()
    
    return render(request, 'topics/sandbox.html', {'form': form})


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = GenerationSession
    form_class = GenerationSessionForm
    template_name = 'topics/generate.html'

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            default_interests = StudentInterest.objects.filter(
                student=self.request.user, is_default=True
            ).values_list('interest_id', flat=True)
            initial['interests'] = default_interests
        return initial

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            since = timezone.now() - timedelta(days=1)
            used = GenerationSession.objects.filter(
                student=request.user, created_at__gte=since).count()
            if used >= 10:
                messages.error(request, 'Ліміт 10 генерацій на добу вичерпано.')
                return redirect('topics:history')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.student = self.request.user
        form.instance.status = 'running'
        form.instance.specialty = self.request.POST.get('specialty', '')
        form.instance.interests_text = self.request.POST.get('custom_interests', '')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('topics:debate_page', kwargs={'session_id': self.object.id})


class DebatePageView(DetailView):
    template_name = 'topics/debate.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return GenerationSession.objects.filter(student=self.request.user)
        key = self.request.session.session_key
        return GenerationSession.objects.filter(student__isnull=True, guest_key=key)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        done_rounds = session.messages.filter(agent='judge').count()
        
        context['history'] = session.messages.all().order_by('sequence_number')
        context['next_round'] = done_rounds + 1
        context['finished'] = done_rounds >= session.rounds
        
        context['topics_data'] = [
            {
                'db_id': t.id,
                'title': t.title,
                'why': t.why,
                'critic_comment': t.critic_comment,
                'difficulty': t.get_difficulty_display(),
                'score': float(t.score) if t.score is not None else None,
                'is_pinned': t.is_pinned,
                'round': t.round,
            }
            for t in GeneratedTopic.objects.filter(session=session).order_by('-is_pinned', 'round', '-score')
        ]
        
        return context


class SessionListView(LoginRequiredMixin, ListView):
    model = GenerationSession
    template_name = 'topics/history_list.html'
    context_object_name = 'sessions'
    paginate_by = 10

    def get_queryset(self):
        qs = (GenerationSession.objects
              .filter(student=self.request.user)
              .annotate(topics_count=Count('topics', distinct=True)))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(specialty__icontains=q) |
                           Q(interests__name__icontains=q)).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        for session in context['sessions']:
            session.pinned_topics = session.topics.filter(is_pinned=True)
        return context


class SessionDetailView(LoginRequiredMixin, DetailView):
    model = GenerationSession
    template_name = 'topics/history_detail.html'
    context_object_name = 'session'

    def get_queryset(self):
        return (GenerationSession.objects
                .filter(student=self.request.user)
                .prefetch_related('topics', 'interests'))


class SessionUpdateView(LoginRequiredMixin, UpdateView):
    form_class = GenerationSessionForm
    template_name = 'topics/generate.html'

    def get_queryset(self):
        return GenerationSession.objects.filter(student=self.request.user)


class SessionDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'topics/session_confirm_delete.html'
    context_object_name = 'session'
    success_url = reverse_lazy('topics:history')

    def get_queryset(self):
        return GenerationSession.objects.filter(student=self.request.user)