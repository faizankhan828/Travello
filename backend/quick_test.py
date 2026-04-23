import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

print("[1] Testing imports...")
try:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')
    
    import django
    print("[2] Django imported")
    
    django.setup()
    print("[3] Django setup complete")
    
    from itineraries.models import Itinerary
    print("[4] Itinerary model imported")
    
    from itineraries.ai_ranker_service import LearningToRankService
    print("[5] Ranker service imported")
    
    ranker = LearningToRankService()
    print("[6] Ranker instantiated")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
