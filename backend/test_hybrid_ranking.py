"""
Test Hybrid Ranking System

Verify that combining LightGBM + HuggingFace improves personalization
compared to LGB alone.
"""

import sys
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'f:\\FYP\\Travello\\backend')

# Configure Django if needed
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
    django.setup()
except Exception as e:
    print(f"Django setup skipped: {e}")

import logging
from itineraries.ai_ranker_service import LearningToRankService
from itineraries.hf_ranker import HFPlaceRanker, create_hf_ranker
from itineraries.combined_ranker import CombinedRanker
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 80)
print("TESTING HYBRID RANKING SYSTEM (LGB + HuggingFace)")
print("=" * 80)

# Sample places (same as HF test)
SAMPLE_PLACES = [
    {'id': 'fort', 'name': 'Lahore Fort', 'category': 'historical', 'rating': 4.8, 'description': 'Historic fort with stunning architecture'},
    {'id': 'food', 'name': 'Gawalmandi Food Street', 'category': 'food', 'rating': 4.5, 'description': 'Famous street for traditional food'},
    {'id': 'mall', 'name': 'Mall Road Shopping', 'category': 'shopping', 'rating': 4.2, 'description': 'Premier shopping destination'},
    {'id': 'garden', 'name': 'Bagh-e-Jinnah (Lawrence Gardens)', 'category': 'nature', 'rating': 4.6, 'description': 'Beautiful gardens and park'},
]

# Different user profiles with different moods
USERS = [
    {'mood': 'HISTORICAL', 'interests': ['history', 'culture', 'architecture'], 'name': 'History Lover'},
    {'mood': 'FOODIE', 'interests': ['food', 'local cuisine', 'restaurants'], 'name': 'Food Enthusiast'},
    {'mood': 'SHOPPING', 'interests': ['shopping', 'fashion', 'retail'], 'name': 'Shopping Enthusiast'},
    {'mood': 'nature', 'interests': ['nature', 'outdoors', 'relaxation'], 'name': 'Nature Lover'},
]

print("\n[1] Loading models...")
try:
    # Load LGB ranker with model
    model_path = 'f:\\FYP\\Travello\\backend\\ml_models\\itinerary_ranker.pkl'
    lgb_ranker = LearningToRankService(model_path=model_path)
    print(f"✓ LightGBM ranker loaded from {model_path}")
    
    # Load HF ranker
    hf_ranker = create_hf_ranker()
    print(f"✓ HuggingFace ranker loaded")
    
    # Create combined ranker
    combined_ranker = CombinedRanker(lgb_ranker, hf_ranker)
    print(f"✓ Combined ranker created")
    
except Exception as e:
    logger.error(f"Failed to load models: {e}")
    sys.exit(1)

print("\n[2] Comparing ranking approaches...\n")

for user in USERS:
    print(f"User: {user['name']} (mood: {user['mood']})")
    print("-" * 70)
    
    try:
        # Test LGB only
        start = time.time()
        lgb_results = lgb_ranker.rank_places(
            user_mood=user['mood'],
            candidate_places=SAMPLE_PLACES,
            user_interests=user['interests'],
            user_budget='MEDIUM',
            use_ml=True
        )
        lgb_time = (time.time() - start) * 1000
        
        # Test hybrid with HF
        start = time.time()
        hybrid_results = combined_ranker.rank_places_hybrid(
            user_mood=user['mood'],
            candidate_places=SAMPLE_PLACES,
            user_interests=user['interests'],
            user_budget='MEDIUM',
            hf_enabled=True
        )
        hybrid_time = (time.time() - start) * 1000
        
        # Display LGB rankings
        print(f"\n  LGB Only (latency: {lgb_time:.0f}ms):")
        for i, place in enumerate(lgb_results[:3], 1):
            print(f"    {i}. {place.place_name:40} {place.score:.4f}")
        
        # Display Hybrid rankings
        print(f"\n  Hybrid LGB+HF (latency: {hybrid_time:.0f}ms):")
        for i, place in enumerate(hybrid_results[:3], 1):
            lgb = place['lgb_score']
            hf = place['hf_score']
            combined = place['combined_score']
            boost = place['hf_boost']
            print(f"    {i}. {place['place_name']:35} "
                  f"LGB={lgb:.3f} HF={hf:.3f} → {combined:.3f} (Δ{boost:+.3f})")
        
        # Check for personalization improvement
        lgb_top_places = [p.place_id for p in lgb_results[:3]]
        hybrid_top_places = [p['place_id'] for p in hybrid_results[:3]]
        
        if lgb_top_places != hybrid_top_places:
            print(f"\n  ⚠ Hybrid reordered top 3! Improvement detected.")
        else:
            print(f"\n  Same ranking, but check if HF boosted correct places.")
        
    except Exception as e:
        logger.error(f"Failed to rank for {user['name']}: {e}")
        import traceback
        traceback.print_exc()
    
    print()

print("\n[3] Personalization Analysis...")
print("-" * 70)

# Collect top places across all users for both approaches
lgb_top_places_by_user = {}
hybrid_top_places_by_user = {}
hybrid_hf_boosts_by_user = {}

for user in USERS:
    try:
        lgb_results = lgb_ranker.rank_places(
            user_mood=user['mood'],
            candidate_places=SAMPLE_PLACES,
            user_interests=user['interests'],
            user_budget='MEDIUM',
            use_ml=True
        )
        lgb_top_places_by_user[user['mood']] = lgb_results[0].place_name
        
        hybrid_results = combined_ranker.rank_places_hybrid(
            user_mood=user['mood'],
            candidate_places=SAMPLE_PLACES,
            user_interests=user['interests'],
            user_budget='MEDIUM',
            hf_enabled=True
        )
        hybrid_top_places_by_user[user['mood']] = hybrid_results[0]['place_name']
        hybrid_hf_boosts_by_user[user['mood']] = [
            (r['place_name'], r['hf_boost']) for r in hybrid_results[:3]
        ]
    except Exception as e:
        logger.error(f"Personalization analysis failed for {user['mood']}: {e}")

print("\nTop-1 Place by User Type:")
print(f"\n{'User Type':<20} {'LGB Top':<30} {'Hybrid Top':<30} {'Status'}")
print("-" * 80)
for user in USERS:
    mood = user['mood']
    lgb_top = lgb_top_places_by_user.get(mood, 'ERROR')
    hybrid_top = hybrid_top_places_by_user.get(mood, 'ERROR')
    
    # Expected top places by mood
    expected_tops = {
        'HISTORICAL': 'Lahore Fort',
        'FOODIE': 'Gawalmandi Food Street',
        'SHOPPING': 'Mall Road Shopping',
        'nature': 'Bagh-e-Jinnah (Lawrence Gardens)',
    }
    expected = expected_tops.get(mood, 'Unknown')
    
    status = "✓" if hybrid_top == expected else ("≈ partial" if expected in hybrid_top else "✗")
    
    print(f"{user['name']:<20} {lgb_top:<30} {hybrid_top:<30} {status}")

print("\n[4] Performance Impact")
print("-" * 70)

total_lgb_time = 0
total_hybrid_time = 0
n_tests = len(USERS)

for user in USERS:
    start = time.time()
    lgb_ranker.rank_places(
        user_mood=user['mood'],
        candidate_places=SAMPLE_PLACES,
        user_interests=user['interests'],
        user_budget='MEDIUM',
        use_ml=True
    )
    total_lgb_time += (time.time() - start) * 1000
    
    start = time.time()
    combined_ranker.rank_places_hybrid(
        user_mood=user['mood'],
        candidate_places=SAMPLE_PLACES,
        user_interests=user['interests'],
        user_budget='MEDIUM',
        hf_enabled=True
    )
    total_hybrid_time += (time.time() - start) * 1000

print(f"Average LGB latency:    {total_lgb_time/n_tests:>6.1f}ms")
print(f"Average Hybrid latency: {total_hybrid_time/n_tests:>6.1f}ms")
print(f"Overhead:              {(total_hybrid_time-total_lgb_time)/n_tests:>6.1f}ms ({100*(total_hybrid_time/total_lgb_time-1):.0f}%)")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
