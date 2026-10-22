from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (ListView, DetailView, CreateView,
                                  UpdateView, DeleteView)

from .forms import GenerationSessionForm, EmailSendForm
from .models import Interest, Question, GenerationSession, GeneratedTopic, HomePageImage
from .services import process_quiz_results, run_debate_pipeline


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
    return render(request, 'topics/home.html', {'interests': interests, 'hero_image': hero_image})


def quiz_view(request):
    if request.method == 'POST':
        selected_options = request.POST.getlist('options')
        results = process_quiz_results(request.user, selected_options)
        if not request.user.is_authenticated:
            request.session['guest_interests'] = [i.id for i in results]
        return redirect('topics:home')

    questions = Question.objects.prefetch_related('options').all()
    return render(request, 'topics/quiz.html', {'questions': questions})


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
            session.save()
            form.save_m2m()
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


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = GenerationSession
    form_class = GenerationSessionForm
    template_name = 'topics/generate.html'

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
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('topics:debate_page', kwargs={'session_id': self.object.id})


class DebatePageView(DetailView):
    template_name = 'topics/debate.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'

    def get_queryset(self):
        return sessions_for_request(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        done_rounds = session.messages.filter(agent='judge').count()
        context['history'] = session.messages.all()
        context['next_round'] = done_rounds + 1
        context['finished'] = done_rounds >= session.rounds
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