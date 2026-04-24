"""
Django Management Command: fix_places_data

Cleans up procedurally-generated (fake numbered) places from the DB and
re-seeds with the curated real Lahore places list.

Usage:
    python manage.py fix_places_data
    python manage.py fix_places_data --dry-run
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from itineraries.models import Place
from itineraries.generator import (
    _FAKE_ARCHETYPE_LABELS,
    _build_extended_lahore_places,
)


class Command(BaseCommand):
    help = "Remove fake generated places and re-seed with real curated Lahore places"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted/added without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Fix Places Data — Lahore"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        # ── 1. Identify fake generated places ─────────────────────────────────
        fake_q = Q()
        for label in _FAKE_ARCHETYPE_LABELS:
            fake_q |= Q(name__startswith=label)

        fake_qs = Place.objects.filter(city='Lahore').filter(fake_q)
        fake_count = fake_qs.count()

        self.stdout.write(f"\n[SCAN] Found {fake_count} procedurally-generated (fake) places to remove:")
        for label in _FAKE_ARCHETYPE_LABELS:
            cnt = Place.objects.filter(city='Lahore', name__startswith=label).count()
            if cnt:
                self.stdout.write(f"         • '{label}...' → {cnt} records")

        # ── 2. Identify real curated places ───────────────────────────────────
        curated = _build_extended_lahore_places()
        curated_names = {p['name'] for p in curated}
        existing_real = Place.objects.filter(city='Lahore').exclude(fake_q)
        existing_real_names = set(existing_real.values_list('name', flat=True))
        new_names = curated_names - existing_real_names

        self.stdout.write(f"\n[PLAN] Real curated places total : {len(curated)}")
        self.stdout.write(f"[PLAN] Already in DB             : {len(existing_real_names)}")
        self.stdout.write(f"[PLAN] To be inserted            : {len(new_names)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made."))
            return

        # ── 3. Delete fakes ────────────────────────────────────────────────────
        if fake_count:
            deleted, _ = fake_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"\n[DELETE] Removed {deleted} fake places."))
        else:
            self.stdout.write("\n[DELETE] Nothing to remove.")

        # ── 4. Insert missing real places ──────────────────────────────────────
        objs = []
        for p in curated:
            if p['name'] not in existing_real_names:
                objs.append(Place(
                    city='Lahore',
                    name=p['name'],
                    category=p['category'],
                    tags=p['tags'],
                    estimated_visit_minutes=p['minutes'],
                    budget_level=p['budget'],
                    latitude=p['lat'],
                    longitude=p['lon'],
                    average_rating=p['rating'],
                    ideal_start_hour=p['start'],
                    ideal_end_hour=p['end'],
                ))

        if objs:
            Place.objects.bulk_create(objs, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"[INSERT] Added {len(objs)} new real places."))
        else:
            self.stdout.write("[INSERT] All curated places already present.")

        # ── 5. Summary ─────────────────────────────────────────────────────────
        total_now = Place.objects.filter(city='Lahore').count()
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(f"[DONE] Lahore places in DB : {total_now}"))
        self.stdout.write(self.style.SUCCESS(f"[DONE] All names are real, curated Lahore places."))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.WARNING(
                "\nNext step: retrain the ranking model:\n"
                "  python manage.py train_itinerary_ranker --verbose\n"
            )
        )
