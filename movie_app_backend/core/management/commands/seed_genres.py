# core/management/commands/seed_genres.py

from django.core.management.base import BaseCommand
from core.utils import seed_initial_genres

class Command(BaseCommand):
    help = 'Fetches the official TMDb genre list and populates the local Genre table.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting genre seeding process...'))
        success = seed_initial_genres()
        if success:
            self.stdout.write(self.style.SUCCESS('Successfully seeded genres from TMDb.'))
        else:
            self.stdout.write(self.style.ERROR('Failed to seed genres. Check logs for details.'))