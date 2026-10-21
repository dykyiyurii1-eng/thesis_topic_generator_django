from .models import StudentInterest, Interest, OptionInterest
from collections import defaultdict

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