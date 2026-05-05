from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count


@receiver(post_save, sender='users.CustomUser')
def create_expert_profile(sender, instance, created, **kwargs):
    """Automatically create an ExpertProfile whenever an expert account is saved.
    Also runs on existing users when user_type is changed to 'expert'.
    """
    from expert_profiles.models import ExpertProfile
    if instance.user_type == 'expert':
        ExpertProfile.objects.get_or_create(user=instance)


def _recalculate_expert_rating(expert):
    from gigs.models import Review  # ← was assignments.models

    aggregates = Review.objects.filter(expert=expert).aggregate(
        avg_rating=Avg('rating'),
        avg_rubric=Avg('rubric_adherence_score'),
        avg_timeliness=Avg('timeliness_score'),
        avg_communication=Avg('communication_score'),
        total=Count('id'),
    )

    total = aggregates['total'] or 0
    recommend_count = Review.objects.filter(
        expert=expert, would_recommend=True
    ).count()
    recommendation_rate = round(
        (recommend_count / total) * 100, 2
    ) if total > 0 else 0.00

    expert.rating = round(aggregates['avg_rating'], 2) if aggregates['avg_rating'] else 0.00
    expert.avg_rubric_adherence = round(aggregates['avg_rubric'], 2) if aggregates['avg_rubric'] else 0.00
    expert.avg_timeliness = round(aggregates['avg_timeliness'], 2) if aggregates['avg_timeliness'] else 0.00
    expert.avg_communication = round(aggregates['avg_communication'], 2) if aggregates['avg_communication'] else 0.00
    expert.total_reviews = total
    expert.recommendation_rate = recommendation_rate

    expert.save(update_fields=[
        'rating', 'avg_rubric_adherence', 'avg_timeliness',
        'avg_communication', 'total_reviews', 'recommendation_rate',
    ])


@receiver(post_save, sender='gigs.Review')   # ← was assignments.Review
def update_expert_rating_on_save(sender, instance, **kwargs):
    _recalculate_expert_rating(instance.expert)


@receiver(post_delete, sender='gigs.Review')  # ← was assignments.Review
def update_expert_rating_on_delete(sender, instance, **kwargs):
    _recalculate_expert_rating(instance.expert)