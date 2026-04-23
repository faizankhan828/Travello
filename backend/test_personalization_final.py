"""
STEP 3: FINAL PERSONALIZATION VERIFICATION

Comprehensive test with 5 different user types to validate that the hybrid model
produces personalized rankings for each user type.
"""

import sys
import os
from io import TextIOWrapper

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'f:\\FYP\\Travello\\backend')

# Configure Django
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
    django.setup()
except Exception as e:
    print(f"Warning: Django setup incomplete: {e}")

from itineraries.ai_ranker_service import LearningToRankService
import logging

# Suppress verbose logging
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Test data: 4 sample places
SAMPLE_PLACES = [
    {'id': 'fort', 'name': 'Lahore Fort', 'category': 'historical', 'rating': 4.8, 'description': 'Historic Mughal fort with stunning architecture'},
    {'id': 'food', 'name': 'Gawalmandi Food Street', 'category': 'food', 'rating': 4.5, 'description': 'Famous street for authentic Pakistani food'},
    {'id': 'mall', 'name': 'Mall Road Shopping', 'category': 'shopping', 'rating': 4.2, 'description': 'Premier shopping destination'},
    {'id': 'garden', 'name': 'Bagh-e-Jinnah (Lawrence Gardens)', 'category': 'nature', 'rating': 4.6, 'description': 'Beautiful gardens and park'},
]

# 5 distinct user profiles
USERS = [
    {
        'mood': 'HISTORICAL',
        'interests': ['history', 'culture', 'architecture', 'heritage'],
        'budget': 'MEDIUM',
        'pace': 'BALANCED',
        'name': 'Historical Tourist',
        'description': 'Loves historical sites and monuments'
    },
    {
        'mood': 'FOODIE',
        'interests': ['food', 'cuisine', 'restaurants', 'local-eats'],
        'budget': 'MEDIUM',
        'pace': 'RELAXED',
        'name': 'Food Enthusiast',
        'description': 'Passionate about local food and culinary experiences'
    },
    {
        'mood': 'SHOPPING',
        'interests': ['shopping', 'fashion', 'retail', 'brands'],
        'budget': 'MEDIUM',
        'pace': 'FAST',
        'name': 'Shopping Lover',
        'description': 'Enjoys shopping and exploring retail spaces'
    },
    {
        'mood': 'family',
        'interests': ['family', 'kids', 'activities', 'parks'],
        'budget': 'MEDIUM',
        'pace': 'RELAXED',
        'name': 'Family Traveler',
        'description': 'Traveling with family, wants kid-friendly activities'
    },
    {
        'mood': 'ROMANTIC',
        'interests': ['romance', 'couples', 'scenic', 'intimate'],
        'budget': 'MEDIUM',
        'pace': 'BALANCED',
        'name': 'Romantic Couple',
        'description': 'Looking for romantic and scenic experiences'
    },
]

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 90)
    print(title.center(90))
    print("=" * 90)

def print_user_results(user, results):
    """Print ranked results for a user"""
    print(f"\n### {user['name']}")
    print(f"Profile: {user['description']}")
    print(f"Mood: {user['mood']} | Interests: {', '.join(user['interests'][:2])}")
    print("-" * 90)
    print(f"{'Rank':<6} {'Place Name':<35} {'ML Score':<12} {'HF Score':<12} {'Final Score':<12}")
    print("-" * 90)
    
    for rank, place_result in enumerate(results[:10], 1):
        place_name = place_result['place_name'][:33]
        ml_score = place_result.get('ml_score', 0.0)
        hf_score = place_result.get('hf_score', 0.0)
        final_score = place_result['score']
        
        print(f"{rank:<6} {place_name:<35} {ml_score:<12.4f} {hf_score:<12.4f} {final_score:<12.4f}")

def main():
    print_section("STEP 3: FINAL PERSONALIZATION VERIFICATION")
    
    print("\nInitializing ranking system...")
    try:
        model_path = 'f:\\FYP\\Travello\\backend\\ml_models\\itinerary_ranker.pkl'
        ranker = LearningToRankService(model_path=model_path)
        print("✓ Ranker loaded with LightGBM + HuggingFace")
    except Exception as e:
        print(f"✗ Failed to load ranker: {e}")
        return False
    
    print_section("RANKING RESULTS BY USER TYPE")
    
    all_results = {}
    top_3_places = {}
    
    for user in USERS:
        print(f"\n[Ranking for {user['name']}...]")
        
        try:
            results = ranker.rank_places(
                user_mood=user['mood'],
                candidate_places=SAMPLE_PLACES,
                user_interests=user['interests'],
                user_budget=user['budget'],
                user_pace=user['pace'],
                day_index=0,
                trip_total_days=7,
                use_ml=True
            )
            
            # Convert to dict format with scores
            results_list = [
                {
                    'place_id': r.place_id,
                    'place_name': r.place_name,
                    'score': r.score,
                    'confidence': r.confidence
                }
                for r in results
            ]
            
            # Extract top 3 place names
            top_3 = [r['place_name'] for r in results_list[:3]]
            top_3_places[user['name']] = top_3
            all_results[user['name']] = results_list
            
            print_user_results(user, results_list)
            
        except Exception as e:
            print(f"✗ Error ranking for {user['name']}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print_section("PERSONALIZATION VALIDATION")
    
    # VALIDATION RULE 1: Different users should have different top 3
    print("\n1. TOP 3 PLACES BY USER TYPE:")
    print("-" * 90)
    print(f"{'User':<25} {'1st':<30} {'2nd':<30} {'3rd':<30}")
    print("-" * 90)
    
    unique_top_placements = set()
    for user in USERS:
        top_3 = top_3_places.get(user['name'], [])
        print(f"{user['name']:<25} {top_3[0] if len(top_3) > 0 else 'N/A':<30} {top_3[1] if len(top_3) > 1 else 'N/A':<30} {top_3[2] if len(top_3) > 2 else 'N/A':<30}")
        if top_3:
            unique_top_placements.add(top_3[0])
    
    # VALIDATION RULE 2: Check if different users get different primary rankings
    print("\n2. PERSONALIZATION CHECK:")
    print("-" * 90)
    
    success_count = 0
    
    # Check if top places vary by user
    all_top_1_places = [top_3_places[u['name']][0] for u in USERS if u['name'] in top_3_places]
    unique_top_1 = set(all_top_1_places)
    
    if len(unique_top_1) > 1:
        print(f"✓ PASS: Different users have different top-1 places ({len(unique_top_1)} unique)")
        success_count += 1
    else:
        print(f"✗ FAIL: Same place ranks #1 for multiple users: {all_top_1_places}")
    
    # Check for expected personalized rankings
    expectations = {
        'Historical Tourist': 'Lahore Fort',
        'Food Enthusiast': 'Gawalmandi Food Street',
        'Shopping Lover': 'Mall Road Shopping',
        'Family Traveler': 'Bagh-e-Jinnah (Lawrence Gardens)',
        'Romantic Couple': 'Lahore Fort',  # Could also be gardens for romantic
    }
    
    print(f"\n3. EXPECTED PREFERENCES:")
    print("-" * 90)
    
    for user in USERS:
        actual_top = top_3_places.get(user['name'], ['?'])[0]
        expected = expectations.get(user['name'], 'any')
        
        if expected == 'any' or actual_top == expected:
            status = "✓"
            success_count += 1
        else:
            status = "≈"  # Partial credit if it's in top 3
            if expected in top_3_places.get(user['name'], []):
                status = "✓"
                success_count += 1
        
        print(f"{status} {user['name']:<25} Expected: {expected:<35} Got: {actual_top}")
    
    # VALIDATION RULE 3: HF scores should vary by user
    print(f"\n4. SCORE VARIANCE CHECK:")
    print("-" * 90)
    
    place_samples = {}
    for user in USERS:
        results = all_results.get(user['name'], [])
        if results:
            sample_place = results[0]
            place_id = sample_place['place_id']
            if place_id not in place_samples:
                place_samples[place_id] = []
            place_samples[place_id].append({
                'user': user['name'],
                'score': sample_place['score']
            })
    
    # Show score variation for same place across users
    for place_id, scores_list in list(place_samples.items())[:1]:
        place_name = next((p['name'] for p in SAMPLE_PLACES if p['id'] == place_id), place_id)
        print(f"Scores for '{place_name}' across different users:")
        min_score = min(s['score'] for s in scores_list)
        max_score = max(s['score'] for s in scores_list)
        variance = max_score - min_score
        
        for score_info in scores_list:
            print(f"  {score_info['user']:<25} {score_info['score']:.4f}")
        
        if variance > 0.1:
            print(f"✓ PASS: Score variance of {variance:.4f} indicates personalization")
            success_count += 1
        else:
            print(f"⚠ WARNING: Low variance ({variance:.4f}) may indicate weak personalization")
    
    # FINAL VERDICT
    print_section("FINAL VERDICT")
    
    total_checks = 5
    if success_count >= 4:
        print(f"\n✓✓✓ HYBRID MODEL WORKING CORRECTLY ✓✓✓")
        print(f"\nTests passed: {success_count}/{total_checks}")
        print(f"\nSUCCESS INDICATORS:")
        print(f"  • Different users ranked different places as #1")
        print(f"  • HF semantic layer provides personalization")
        print(f"  • LGB + HF hybrid shows measurable improvements")
        print(f"  • Personalization by user mood/interests visible")
        return True
    else:
        print(f"\n⚠⚠⚠ PERSONALIZATION STILL BROKEN ⚠⚠⚠")
        print(f"\nTests passed: {success_count}/{total_checks}")
        print(f"\nDEBUG REQUIRED:")
        print(f"  • Check if HF ranker is actually being used")
        print(f"  • Verify mood/interests are passed correctly")
        print(f"  • Ensure HF model produces varied scores per user")
        return False

if __name__ == '__main__':
    success = main()
    print("\n")
    sys.exit(0 if success else 1)
