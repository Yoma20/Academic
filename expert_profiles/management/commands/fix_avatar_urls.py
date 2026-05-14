from django.core.management.base import BaseCommand
from expert_profiles.models import ExpertProfile

class Command(BaseCommand):
    help = 'Fix relative avatar URLs to absolute'

    def handle(self, *args, **kwargs):
        base = "https://web-production-d2ca9.up.railway.app"
        updated = 0
        for p in ExpertProfile.objects.exclude(avatar_url=""):
            if p.avatar_url.startswith("/"):
                p.avatar_url = f"{base}{p.avatar_url}"
                p.save(update_fields=["avatar_url"])
                updated += 1
        self.stdout.write(f"Updated {updated} profiles.")