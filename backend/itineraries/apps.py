from django.apps import AppConfig


class ItinerariesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itineraries'

    def ready(self):
        """Warm up the ranker cache once at startup so first request is fast."""
        try:
            from .hf_ranker import create_hf_ranker

            create_hf_ranker()
        except Exception:
            # Startup warmup is best-effort only; request-time fallback still works.
            pass

