import json
import os
from datetime import timedelta

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
from .prompts import (
    build_generator_input,
    SANDBOX_OPTIMIZER_SYSTEM,
)


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

    selected_topic_id = request.GET.get('selected_topic')
    if selected_topic_id:
        try:
            selected_topic_id = int(selected_topic_id)
        except (ValueError, TypeError):
            selected_topic_id = None

    response = StreamingHttpResponse(
        run_debate_pipeline(session, round_no, selected_topic_id=selected_topic_id),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    return response




@require_POST
def pin_topic_view(request, topic_id):
    topic = get_object_or_404(
        GeneratedTopic,
        id=topic_id,
        session__in=sessions_for_request(request),
    )
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
            custom_words = request.POST.get('custom_interests', '') or request.POST.get('keywords', '')
            if custom_words:
                session.keywords = custom_words.strip()
                request.session['guest_custom_interests'] = custom_words.strip()

            session.specialty = request.POST.get('specialty', '')
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
    MAX_ITERATIONS = 5

    def _validate_topics_json(raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, f'Невалідний JSON: {e}'
        if not isinstance(data, list) or len(data) != 5:
            return None, 'Очікується масив рівно з 5 елементів'
        required = {'id', 'title', 'why', 'difficulty'}
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                return None, f'Елемент {i} — не об\'єкт'
            missing = required - item.keys()
            if missing:
                return None, f'Елемент {i} без полів: {", ".join(sorted(missing))}'
            if item['difficulty'] not in ('easy', 'medium', 'hard'):
                return None, f'Елемент {i}: некоректний difficulty "{item["difficulty"]}"'
        return data, None

    def _looks_like_topics_json(text):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'title' in data:
                return True
            if isinstance(data, list) and data and isinstance(data[0], dict) and 'title' in data[0]:
                return True
        except (json.JSONDecodeError, IndexError):
            pass
        return False

    if request.method == 'POST':
        form = SandboxForm(request.POST)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if form.is_valid():
            cd = form.cleaned_data
            current_prompt = cd['system_prompt']
            specialty = cd['specialty']
            education = cd['education']
            interests = cd['interests']
            iterations = cd['iterations']

            if iterations > MAX_ITERATIONS:
                iterations = MAX_ITERATIONS

            log = []
            consecutive_fails = 0

            for i in range(1, iterations + 1):
                ctx = {
                    'specialty': specialty,
                    'education': education,
                    'interests': [(j.strip(), 'high') for j in interests.split(',') if j.strip()],
                }

                # ── ГЕНЕРАЦІЯ ──
                try:
                    raw_gen, provider_gen = call_with_fallback(
                        'generator', current_prompt, build_generator_input(ctx),
                        user_obj=request.user,
                    )
                except (LLMError, Exception) as e:
                    log.append({'step': i, 'action': 'Генерація', 'status': 'error', 'error': str(e)})
                    consecutive_fails += 1
                    if consecutive_fails >= 2:
                        break
                    continue

                data, err = _validate_topics_json(raw_gen)
                if err:
                    log.append({
                        'step': i, 'action': 'Генерація', 'status': 'error',
                        'prompt': current_prompt, 'response': raw_gen,
                        'error': f'Формат порушено: {err}', 'provider': provider_gen,
                    })
                    consecutive_fails += 1
                    if consecutive_fails >= 2:
                        break
                    continue

                log.append({
                    'step': i, 'action': 'Генерація', 'status': 'ok',
                    'prompt': current_prompt, 'response': raw_gen,
                    'provider': provider_gen,
                })
                consecutive_fails = 0

                if i < iterations:
                    optimizer_user = (
                        f"<PROMPT>\n{current_prompt}\n</PROMPT>\n\n"
                        f"<SAMPLE_OUTPUT>\n{raw_gen[:600]}\n</SAMPLE_OUTPUT>\n\n"
                        f"Перепиши САМЕ СИСТЕМНИЙ ПРОМПТ (не відповідь). "
                        f"Поверни ТІЛЬКИ новий текст промпту:"
                    )

                    try:
                        new_prompt, provider_opt = call_with_fallback(
                            'critic', SANDBOX_OPTIMIZER_SYSTEM, optimizer_user,
                            user_obj=request.user,
                        )
                    except (LLMError, Exception) as e:
                        log.append({'step': i, 'action': 'Оновлення промпту', 'status': 'error', 'error': str(e)})
                        consecutive_fails += 1
                        if consecutive_fails >= 2:
                            break
                        continue

                    new_prompt = (new_prompt or '').strip()

                    if not new_prompt:
                        log.append({
                            'step': i, 'action': 'Оновлення промпту', 'status': 'error',
                            'error': 'Оптимізатор повернув порожній промпт. Ітерацію пропущено.',
                            'provider': provider_opt,
                        })
                        consecutive_fails += 1
                        if consecutive_fails >= 2:
                            break
                        continue

                    # Якщо повернув JSON — одна повторна спроба
                    if _looks_like_topics_json(new_prompt):
                        retry_user = (
                            f"<PROMPT>\n{current_prompt}\n</PROMPT>\n\n"
                            f"<SAMPLE_OUTPUT>\n{raw_gen[:600]}\n</SAMPLE_OUTPUT>\n\n"
                            f"Ти повернув JSON з темами. Це НЕПРАВИЛЬНО. "
                            f"Поверни лише текст інструкції (системний промпт), а НЕ JSON."
                        )
                        try:
                            new_prompt, provider_opt = call_with_fallback(
                                'critic', SANDBOX_OPTIMIZER_SYSTEM, retry_user,
                                user_obj=request.user,
                            )
                            new_prompt = (new_prompt or '').strip()
                        except (LLMError, Exception):
                            new_prompt = ''

                        if not new_prompt or _looks_like_topics_json(new_prompt):
                            log.append({
                                'step': i, 'action': 'Оновлення промпту', 'status': 'error',
                                'old_prompt': current_prompt, 'new_prompt': new_prompt,
                                'error': 'Оптимізатор повторно повернув JSON замість промпту. Ітерацію пропущено.',
                                'provider': provider_opt,
                            })
                            consecutive_fails += 1
                            if consecutive_fails >= 2:
                                break
                            continue

                    if len(new_prompt) < len(current_prompt) * 0.7:
                        log.append({
                            'step': i, 'action': 'Оновлення промпту', 'status': 'error',
                            'old_prompt': current_prompt, 'new_prompt': new_prompt,
                            'error': f'Новий промпт занадто короткий ({len(new_prompt)} vs {len(current_prompt)} симв.). Ітерацію пропущено.',
                            'provider': provider_opt,
                        })
                        consecutive_fails += 1
                        if consecutive_fails >= 2:
                            break
                        continue

                    log.append({
                        'step': i, 'action': 'Оновлення промпту', 'status': 'ok',
                        'old_prompt': current_prompt, 'new_prompt': new_prompt,
                        'provider': provider_opt,
                    })
                    current_prompt = new_prompt
                    consecutive_fails = 0

            ok_count = sum(1 for e in log if e.get('action') == 'Генерація' and e.get('status') == 'ok')
            err_count = sum(1 for e in log if e.get('status') == 'error')
            summary_text = f'Успішних генерацій: {ok_count} / Помилок: {err_count} з {iterations} ітерацій'
            if consecutive_fails >= 2:
                summary_text += ' | Цикл зупинено: 2 послідовні помилки.'
            log.append({
                'step': '—',
                'action': 'Підсумок',
                'summary': summary_text,
            })

            if is_ajax:
                return JsonResponse({'log': log})

            return render(request, 'topics/sandbox.html', {'form': form, 'log': log})

        else:
            if is_ajax:
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
            from .models import UserApiKey
            has_own_key = UserApiKey.objects.filter(user=request.user, is_valid=True).exists()
            limit = 50 if has_own_key else 10
            if used >= limit:
                messages.error(request, 'Ліміт генерацій на сьогодні вичерпано.')
                return redirect('topics:history')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.student = self.request.user
        form.instance.status = 'running'
        form.instance.specialty = self.request.POST.get('specialty', '')
        custom_words = self.request.POST.get('custom_interests', '') or self.request.POST.get('keywords', '')
        if custom_words:
            form.instance.keywords = custom_words.strip()
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
            qs = qs.filter(
                Q(specialty__icontains=q) |
                Q(interests__name__icontains=q) |
                Q(keywords__icontains=q)
            ).distinct()

        status = self.request.GET.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)

        institution_type = self.request.GET.get('institution_type', '').strip()
        if institution_type:
            qs = qs.filter(institution_type=institution_type)

        sort = self.request.GET.get('sort', 'newest').strip()
        if sort == 'oldest':
            qs = qs.order_by('created_at')
        else:
            qs = qs.order_by('-created_at')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['selected_institution'] = self.request.GET.get('institution_type', '').strip()
        context['selected_sort'] = self.request.GET.get('sort', 'newest').strip()
        context['status_choices'] = GenerationSession.STATUS_CHOICES
        context['institution_choices'] = GenerationSession.INSTITUTION_CHOICES
        

        query_params = self.request.GET.copy()
        if 'page' in query_params:
            query_params.pop('page')
        context['filter_querystring'] = query_params.urlencode()

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


@login_required
def api_keys_view(request):
    """Список власних API-ключів + форма додавання (з rate limiting)."""
    from django.core.cache import cache
    from .forms import UserApiKeyForm
    from .models import UserApiKey
    from .crypto import encrypt

    keys = UserApiKey.objects.filter(user=request.user)
    error = None
    form = UserApiKeyForm()

    if request.method == 'POST':
        cache_key = f'api_key_add_attempts_{request.user.id}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 5:
            error = (
                'Перевищено ліміт спроб додавання ключа. '
                'Спробуйте через годину.'
            )
        else:
            form = UserApiKeyForm(request.POST)
            if form.is_valid():
                provider = form.cleaned_data['provider']
                raw_key = form.cleaned_data['api_key']
                UserApiKey.objects.update_or_create(
                    user=request.user,
                    provider=provider,
                    defaults={
                        'encrypted_key': encrypt(raw_key),
                        'last4': raw_key[-4:],
                        'is_valid': True,
                        'last_used_at': None,
                    }
                )
                cache.delete(cache_key)
                messages.success(
                    request,
                    f'Ключ для {dict(UserApiKey.PROVIDER_CHOICES)[provider]} '
                    f'успішно збережено.',
                )
                return redirect('topics:api_keys')
            else:
                cache.set(cache_key, attempts + 1, timeout=3600)

    return render(request, 'topics/api_keys.html', {
        'keys': keys,
        'form': form,
        'error': error,
    })


@login_required
@require_POST
def api_key_delete_view(request, key_id):
    """Видалення власного API-ключа."""
    from .models import UserApiKey
    key = get_object_or_404(UserApiKey, id=key_id, user=request.user)
    key.delete()
    messages.success(request, 'API-ключ видалено.')
    return redirect('topics:api_keys')


@staff_member_required
def admin_activity_view(request):
    """
    Аналітична панель активності користувачів (суто для адміністратора).
    """
    from django.contrib.auth import get_user_model
    from .models import UserApiKey
    
    User = get_user_model()
    
    total_users = User.objects.count()
    week_ago = timezone.now() - timedelta(days=7)
    active_users_7d = User.objects.filter(last_login__gte=week_ago).count()
    total_sessions = GenerationSession.objects.count()
    total_topics = GeneratedTopic.objects.count()
    total_byok_keys = UserApiKey.objects.filter(is_valid=True).count()
    
    users_list = (
        User.objects
        .annotate(
            sessions_count=Count('sessions', distinct=True),
            pinned_count=Count('sessions__topics', filter=Q(sessions__topics__is_pinned=True), distinct=True),
        )
        .prefetch_related('api_keys')
        .order_by('-date_joined')
    )
    
    recent_sessions = (
        GenerationSession.objects
        .select_related('student')
        .annotate(topics_count=Count('topics'))
        .order_by('-created_at')[:25]
    )
    
    context = {
        'total_users': total_users,
        'active_users_7d': active_users_7d,
        'total_sessions': total_sessions,
        'total_topics': total_topics,
        'total_byok_keys': total_byok_keys,
        'users_list': users_list,
        'recent_sessions': recent_sessions,
    }
    return render(request, 'topics/admin_activity.html', context)
