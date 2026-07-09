from django.apps import AppConfig


class ExpertProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expert_profiles'

    def ready(self):
        import expert_profiles.signals  # noqa: F401 — registers the signal receivers