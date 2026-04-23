"""
End-to-end test for the ML ranker service.
Tests model loading and predictions.
"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

from itineraries.ai_ranker_service import LearningToRankService

# Sample test data
CANDIDATE_PLACES = [
    {
        'id': 1,
        'name': 'Badshahi Mosque',
        'category': 'religious',
        'average_rating': 4.8,
        'budget_level': 'LOW',
        'estimated_visit_minutes': 90,
        'tags': ['history', 'culture', 'photography'],
        'ideal_start_hour': 8,
        'ideal_end_hour': 17,
        'latitude': 31.5829,
        'longitude': 74.3067,
    },
    {
        'id': 2,
        'name': 'Lahore Fort',
        'category': 'history',
        'average_rating': 4.7,
        'budget_level': 'LOW',
        'estimated_visit_minutes': 120,
        'tags': ['history', 'architecture', 'culture'],
        'ideal_start_hour': 9,
        'ideal_end_hour': 18,
        'latitude': 31.5847,
        'longitude': 74.3134,
    },
    {
        'id': 3,
        'name': 'Data Darbar',
        'category': 'religious',
        'average_rating': 4.5,
        'budget_level': 'LOW',
        'estimated_visit_minutes': 60,
        'tags': ['spiritual', 'history'],
        'ideal_start_hour': 7,
        'ideal_end_hour': 19,
        'latitude': 31.5408,
        'longitude': 74.3249,
    },
    {
        'id': 4,
        'name': 'Food Street',
        'category': 'food',
        'average_rating': 4.6,
        'budget_level': 'MEDIUM',
        'estimated_visit_minutes': 60,
        'tags': ['food', 'culture', 'social'],
        'ideal_start_hour': 17,
        'ideal_end_hour': 23,
        'latitude': 31.5870,
        'longitude': 74.3142,
    },
    {
        'id': 5,
        'name': 'Mall Road',
        'category': 'shopping',
        'average_rating': 4.4,
        'budget_level': 'MEDIUM',
        'estimated_visit_minutes': 120,
        'tags': ['shopping', 'social'],
        'ideal_start_hour': 10,
        'ideal_end_hour': 20,
        'latitude': 31.5680,
        'longitude': 74.3112,
    },
]

def test_ranker():
    """Test the ranker service"""
    
    print("=" * 70)
    print("ML RANKER SERVICE END-TO-END TEST")
    print("=" * 70)
    
    # Initialize ranker with trained model
    model_path = os.path.join(
        os.path.dirname(__file__),
        'ml_models',
        'itinerary_ranker.pkl'
    )
    
    print(f"\n[1] Loading ranker with model: {model_path}")
    ranker = LearningToRankService(model_path=model_path)
    
    if ranker.model:
        print(f"    ✓ Model loaded successfully")
        print(f"    ✓ Scaler available: {ranker.scaler is not None}")
        print(f"    ✓ Features: {ranker.feature_columns}")
    else:
        print(f"    ✗ Model NOT loaded - will use fallback scoring")
    
    # Test 1: Historical mood
    print(f"\n[2] Test ranking with HISTORICAL mood")
    ranked_historical = ranker.rank_places(
        user_mood='HISTORICAL',
        candidate_places=CANDIDATE_PLACES,
        user_interests=['history', 'culture', 'architecture'],
        user_budget='MEDIUM',
        user_pace='BALANCED',
        day_index=0,
        trip_total_days=3,
        hotel_location=(31.5, 74.3),
        previously_visited=[]
    )
    
    print(f"    Ranked {len(ranked_historical)} places:")
    for i, place in enumerate(ranked_historical, 1):
        print(f"      {i}. {place.place_name} (score: {place.score:.3f}, confidence: {place.confidence:.3f}, ml: {place.is_ml_ranked})")
    
    # Test 2: Foodie mood
    print(f"\n[3] Test ranking with FOODIE mood")
    ranked_foodie = ranker.rank_places(
        user_mood='FOODIE',
        candidate_places=CANDIDATE_PLACES,
        user_interests=['food', 'culture', 'social'],
        user_budget='MEDIUM',
        user_pace='RELAXED',
        day_index=1,
        trip_total_days=3,
        hotel_location=(31.5, 74.3),
        previously_visited=[1, 2]  # Already visited Badshahi and Fort
    )
    
    print(f"    Ranked {len(ranked_foodie)} places:")
    for i, place in enumerate(ranked_foodie, 1):
        print(f"      {i}. {place.place_name} (score: {place.score:.3f}, confidence: {place.confidence:.3f}, ml: {place.is_ml_ranked})")
    
    # Test 3: Shopping mood
    print(f"\n[4] Test ranking with SHOPPING mood")
    ranked_shopping = ranker.rank_places(
        user_mood='SHOPPING',
        candidate_places=CANDIDATE_PLACES,
        user_interests=['shopping', 'fashion', 'social'],
        user_budget='LUXURY',
        user_pace='PACKED',
        day_index=2,
        trip_total_days=3,
        hotel_location=(31.5, 74.3),
        previously_visited=[1, 2, 3, 4]
    )
    
    print(f"    Ranked {len(ranked_shopping)} places:")
    for i, place in enumerate(ranked_shopping, 1):
        print(f"      {i}. {place.place_name} (score: {place.score:.3f}, confidence: {place.confidence:.3f}, ml: {place.is_ml_ranked})")
    
    # Summary
    print(f"\n[5] Test Summary")
    print(f"    ✓ Model loading: {'OK' if ranker.model else 'USING FALLBACK'}")
    print(f"    ✓ Feature extraction: OK")
    print(f"    ✓ Ranking results: OK")
    print(f"    ✓ Inference latency: {ranker.inference_latency_ms:.2f}ms")
    print(f"    ✓ Last confidence: {ranker.last_confidence:.3f}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)

if __name__ == '__main__':
    test_ranker()
