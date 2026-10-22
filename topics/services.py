import json
import time
from collections import defaultdict
from .llm import call_with_fallback, parse_json_response, LLMError
from .models import StudentInterest, Interest, OptionInterest, GeneratedTopic, AgentMessage
from .prompts import (GENERATOR_SYSTEM, CRITIC_SYSTEM, JUDGE_SYSTEM,
                      build_generator_input, build_critic_input, build_judge_input)

def process_quiz_results(user, selected_option_ids):
    if not selected_option_ids:
        return []
    weights = defaultdict(float)
    option_interests = OptionInterest.objects.filter(option_id__in=selected_option_ids)
    for oi in option_interests:
        weights[oi.interest_id] += oi.weight
    sorted_interests = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]
    result_interests = []
    if user.is_authenticated:
        StudentInterest.objects.filter(student=user, source='quiz').delete()
        for interest_id, weight in sorted_interests:
            interest = Interest.objects.get(id=interest_id)
            StudentInterest.objects.create(student=user, interest=interest, weight=weight, source='quiz')
            result_interests.append(interest)
    else:
        for interest_id, weight in sorted_interests:
            result_interests.append(Interest.objects.get(id=interest_id))
    return result_interests

def sse(**payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def _fail(session, text):
    session.status = 'error'
    session.save(update_fields=['status'])
    yield sse(type='error', text=text)

def _clean_score(value):
    try:
        score = round(float(value), 1)
    except (TypeError, ValueError):
        return None
    return score if 1 <= score <= 10 else None

def _save_message(session, agent, provider, text, seq):
    AgentMessage.objects.create(session=session, agent=agent, provider=provider,
                                content=text, sequence_number=seq)

def run_debate_pipeline(session, round_no):
    if not 1 <= round_no <= session.rounds:
        yield sse(type='error', text='Некоректний номер кола.')
        return
        
    last_msg = session.messages.order_by('-sequence_number').first()
    base_seq = last_msg.sequence_number if last_msg else 0

    ctx = {
        'specialty': session.specialty,
        'education': session.level or session.institution_type,
        'interests': [(i.name, 'high') for i in session.interests.all()],
    }

    yield sse(type='status', text=f'Генератор пише... (коло {round_no} з {session.rounds})')
    try:
        raw, provider = call_with_fallback('generator', GENERATOR_SYSTEM, build_generator_input(ctx))
        data = parse_json_response(raw)
    except LLMError as e:
        yield from _fail(session, str(e))
        return
    items = [t for t in data if isinstance(t, dict)] if isinstance(data, list) else []
    if not items:
        yield from _fail(session, 'Генератор повернув порожню відповідь.')
        return
        
    saved = []
    timestamp = int(time.time())
    for n, t in enumerate(items, 1):
        difficulty = t.get('difficulty')
        unique_key = f"r{round_no}_{n}_{timestamp}"
        saved.append(GeneratedTopic.objects.create(
            session=session,
            topic_key=unique_key,
            title=str(t.get('title', 'Без назви'))[:300],
            why=str(t.get('why', '')),
            difficulty=difficulty if difficulty in ('easy', 'medium', 'hard') else 'medium',
            round=round_no,
        ))
        
    text = "\n\n".join(f"{n}. {t.title} ({t.get_difficulty_display()})\n{t.why}"
                       for n, t in enumerate(saved, 1))
    _save_message(session, 'generator', provider, text, base_seq + 1)
    yield sse(type='agent', agent='generator', provider=provider, round=round_no, text=text)
    
    yield sse(type='status', text='Критик шукає слабкі місця...')
    by_key = {t.topic_key: t for t in saved}
    for_critic = [{'id': t.topic_key, 'title': t.title, 'why': t.why} for t in saved]
    try:
        raw, provider = call_with_fallback('critic', CRITIC_SYSTEM, build_critic_input(ctx, for_critic))
        data = parse_json_response(raw)
    except LLMError as e:
        yield from _fail(session, f'Критик недоступний: {e}')
        return
    reviews = [c for c in data if isinstance(c, dict) and c.get('id') in by_key] if isinstance(data, list) else []
    lines = []
    for c in reviews:
        t = by_key[c['id']]
        t.critic_comment = str(c.get('problems', ''))
        t.save(update_fields=['critic_comment'])
        lines.append(f"{t.title}\n→ {c.get('verdict', '?')}: {t.critic_comment}")
    text = "\n\n".join(lines) or 'Критик не надав зауважень.'
    _save_message(session, 'critic', provider, text, base_seq + 2)
    yield sse(type='agent', agent='critic', provider=provider, round=round_no, text=text)
    
    yield sse(type='status', text='Суддя виносить оцінки...')
    for_judge = [{'id': t.topic_key, 'title': t.title, 'why': t.why, 'critic': t.critic_comment}
                 for t in saved]
    try:
        raw, provider = call_with_fallback('judge', JUDGE_SYSTEM, build_judge_input(ctx, for_judge))
        data = parse_json_response(raw)
    except LLMError as e:
        yield from _fail(session, f'Суддя недоступний: {e}')
        return
    verdicts = [v for v in data if isinstance(v, dict) and v.get('id') in by_key] if isinstance(data, list) else []
    lines = []
    for v in verdicts:
        t = by_key[v['id']]
        score = _clean_score(v.get('score'))
        if score is not None:
            t.score = score
            t.save(update_fields=['score'])
        lines.append(f"{t.title}\n→ {score if score is not None else '—'}/10. {v.get('reason', '')}")
    text = "\n\n".join(lines) or 'Суддя не виніс оцінок.'
    _save_message(session, 'judge', provider, text, base_seq + 3)
    yield sse(type='agent', agent='judge', provider=provider, round=round_no, text=text)
    
    if round_no == session.rounds:
        session.status = 'done'
        session.save(update_fields=['status'])
        
    yield sse(type='round_done', round=round_no, topics=[
        {'db_id': t.id, 'title': t.title, 'why': t.why, 'critic_comment': t.critic_comment,
         'difficulty': t.get_difficulty_display(),
         'score': float(t.score) if t.score is not None else None}
        for t in saved
    ])