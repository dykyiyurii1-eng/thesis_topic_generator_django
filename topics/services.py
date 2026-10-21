import json
from .models import GeneratedTopic, AgentMessage
from .llm import call_with_fallback, parse_json_response, LLMError
from .prompts import GENERATOR_SYSTEM, CRITIC_SYSTEM, build_generator_input, build_critic_input
from collections import defaultdict
from .models import StudentInterest, Interest, OptionInterest, GeneratedTopic, AgentMessage
from .llm import call_with_fallback, parse_json_response, LLMError
from .prompts import GENERATOR_SYSTEM, CRITIC_SYSTEM, build_generator_input, build_critic_input
import json

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

# ... далі йде твій код run_debate_pipeline ...
def run_debate_pipeline(session, round_no):
    yield f"data: {json.dumps({'type': 'status', 'text': f'Генератор пише... (Коло {round_no} з {session.rounds})'})}\n\n"
    
    ctx = {
        'specialty': session.specialty,
        'education': session.institution_type,
        'interests': [(i.name, 'high') for i in session.interests.all()],
        'round_no': round_no,
        'total_rounds': session.rounds,
        'pinned_ids': list(session.topics.filter(is_pinned=True).values_list('topic_key', flat=True)),
        'user_hint': ''
    }
    
    try:
        raw_gen, provider_gen = call_with_fallback('generator', GENERATOR_SYSTEM, build_generator_input(ctx))
        topics_data = parse_json_response(raw_gen)
    except LLMError as e:
        yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        return

    saved_topics = []
    for i, t in enumerate(topics_data):
        topic_key = f"r{round_no}_{i+1}"
        topic = GeneratedTopic.objects.create(
            session=session,
            topic_key=topic_key,
            title=t.get('title', 'Без назви'),
            why=t.get('why', ''),
            difficulty=t.get('difficulty', 'medium'),
            round=round_no
        )
        saved_topics.append(topic)

    AgentMessage.objects.create(
        session=session, agent='generator', provider=provider_gen,
        content=f"Згенеровано {len(saved_topics)} тем.", sequence_number=round_no * 2 - 1
    )
    
    yield f"data: {json.dumps({'type': 'message', 'text': f'Генератор ({provider_gen}) запропонував теми.'})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'text': 'Критик оцінює...'})}\n\n"

    topics_for_critic = [{'id': t.topic_key, 'title': t.title, 'why': t.why} for t in saved_topics]
    try:
        raw_cri, provider_cri = call_with_fallback('critic', CRITIC_SYSTEM, build_critic_input(ctx, topics_for_critic))
        critic_data = parse_json_response(raw_cri)
    except LLMError as e:
        yield f"data: {json.dumps({'type': 'error', 'text': f'Критик недоступний: {e}'})}\n\n"
        return

    for c in critic_data:
        t_id = c.get('id')
        topic = next((t for t in saved_topics if t.topic_key == t_id), None)
        if topic:
            topic.score = c.get('score', 0)
            topic.critic_comment = c.get('problems', '')
            topic.save()

    AgentMessage.objects.create(
        session=session, agent='critic', provider=provider_cri,
        content=json.dumps(critic_data, ensure_ascii=False), sequence_number=round_no * 2
    )
    
    yield f"data: {json.dumps({'type': 'message', 'text': f'Критик ({provider_cri}) завершив оцінку.'})}\n\n"
    yield f"data: {json.dumps({'type': 'round_done', 'round': round_no, 'topics': topics_for_critic})}\n\n"