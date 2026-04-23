"""
DEEP MODEL QUALITY VERIFICATION - SIMPLIFIED
==============================================
Tests:
1. Load model and check metadata
2. Run 50 predictions on random places
3. Test 5 user scenarios
4. Verify personalization and latency
"""

import os
import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

print("[1] Django setup...")
import django
django.setup()
print("[2] Django ready\n")

import random
import numpy as np
import pickle
import time
from itineraries.models import Place, Itinerary
from itineraries.ai_ranker_service import LearningToRankService

print("=" * 80)
print("STEP 1: VERIFY MODEL QUALITY DEEPLY")
print("=" * 80)

# Load model
model_path = os.path.join(
    os.path.dirname(__file__),
    'ml_models',
    'itinerary_ranker.pkl'
)

print(f"\n[LOADING] Model from {model_path}...")
ranker = LearningToRankService(model_path=model_path)

if not ranker.model:
    print("✗ Model not loaded!")
    sys.exit(1)

print(f"✓ Model loaded")

# Load metadata
with open(model_path, 'rb') as f:
    model_package = pickle.load(f)

train_r2 = model_package.get('metrics', {}).get('train_r2', 0)
test_r2 = model_package.get('metrics', {}).get('test_r2', 0)
train_rmse = model_package.get('metrics', {}).get('train_rmse', 0)
test_rmse = model_package.get('metrics', {}).get('test_rmse', 0)

print(f"✓ Metrics: Train R²={train_r2:.4f}, Test R²={test_r2:.4f}")

# Get places for testing
print(f"\n[COLLECTING] Random places...")
places = list(Place.objects.filter(city='Lahore')[:100])  # Get first 100 places

if len(places) < 10:
    print(f"✗ Not enough places ({len(places)})")
    sys.exit(1)

print(f"✓ Found {len(places)} places")

# Get a sample user (itinerary) for context
itinerary = Itinerary.objects.first()
if not itinerary:
    print("⚠ Warning: No itineraries in database, using defaults")
    user_mood = 'HISTORICAL'
    user_budget = 'MEDIUM'
    user_pace = 'BALANCED'
    hotel_lat, hotel_lng = 31.5, 74.3
else:
    user_mood = itinerary.mood or 'HISTORICAL'
    user_budget = itinerary.budget_level or 'MEDIUM'
    user_pace = itinerary.pace or 'BALANCED'
    # Itinerary doesn't store hotel location as separate fields
    hotel_lat, hotel_lng = 31.5, 74.3

#############################################################
# SECTION 1: Generate 50 Predictions
#############################################################
print(f"\n[PREDICTIONS] Generating 50 random predictions...")
print("-" * 100)

random.seed(42)
sample_places = random.sample(places, min(50, len(places)))

predictions_list = []
for place in sample_places:
    try:
        score = ranker.get_ml_score(
            place_id=place.id,
            user_mood=user_mood,
            day_index=0,
            trip_total_days=3,
            place_rating=place.average_rating or 3.5,
            place_category_id=hash(place.category) % 10,
            place_budget_level={'LOW': 0, 'MEDIUM': 1, 'LUXURY': 2}.get(place.budget_level, 1),
            place_visit_minutes=place.estimated_visit_minutes,
            user_interests=[],
            user_budget=user_budget,
            user_pace=user_pace,
            hotel_location=(hotel_lat, hotel_lng),
            previously_visited=[],
        )
        predictions_list.append({
            'place': place.name,
            'category': place.category,
            'rating': place.average_rating,
            'prediction': float(score),
        })
    except Exception as e:
        print(f"✗ Error for {place.name}: {e}")

print(f"✓ Generated {len(predictions_list)} predictions\n")

# Print first 20
print("Sample predictions:")
print("-" * 100)
print(f"{'Place':<35} | {'Category':<15} | {'Rating':<8} | {'Prediction':<12}")
print("-" * 100)
for p in predictions_list[:20]:
    print(f"{p['place'][:33]:<35} | {p['category']:<15} | {p['rating']:<8.1f} | {p['prediction']:<12.4f}")

# Statistics
predictions = [p['prediction'] for p in predictions_list]
print(f"\n[STATISTICS]")
print(f"  Min:      {np.min(predictions):.4f}")
print(f"  Max:      {np.max(predictions):.4f}")
print(f"  Mean:     {np.mean(predictions):.4f}")
print(f"  Std Dev:  {np.std(predictions):.4f}")
print(f"  Range:    {(np.max(predictions) - np.min(predictions)):.4f}")

range_spread = np.max(predictions) - np.min(predictions)
if range_spread > 0.05:
    print(f"  ✓ PASS: Good prediction diversity (range={range_spread:.4f})")
elif range_spread > 0.02:
    print(f"  ⚠ WARNING: Low diversity. Range = {range_spread:.4f}")
else:
    print(f"  ✗ FAIL: Predictions too clustered! Range = {range_spread:.4f}")

# Feature importance
print(f"\n[FEATURE IMPORTANCE]")
if hasattr(ranker.model, 'feature_importance'):
    fi = ranker.model.feature_importance()
    features = ranker.feature_columns
    if fi is not None and features:
        importance_pairs = sorted(zip(features, fi), key=lambda x: x[1], reverse=True)
        print("Top 5 Most Important Features:")
        for rank, (feat, imp) in enumerate(importance_pairs[:5], 1):
            print(f"  {rank}. {feat:<25} : {imp:6.1f}")

# Overfitting check
print(f"\n[OVERFITTING CHECK]")
overfit_delta = train_r2 - test_r2
print(f"  Training R²:  {train_r2:.4f}")
print(f"  Test R²:      {test_r2:.4f}")
print(f"  Delta:        {overfit_delta:.4f}")

if overfit_delta > 0.2:
    print(f"  ✗ WARNING: Possible overfitting!")
elif overfit_delta > 0.1:
    print(f"  ⚠ Minor overfitting, acceptable")
else:
    print(f"  ✓ PASS: Model generalizes well")

#############################################################
# SECTION 2: User Scenario Testing
#############################################################
print(f"\n{'='*80}")
print("STEP 2: REAL SCENARIO TESTING")
print(f"{'='*80}")

user_profiles = [
    ('Historical Tourist', 'HISTORICAL', ['history', 'culture'], 'MEDIUM', 'BALANCED'),
    ('Food Lover', 'FOODIE', ['food', 'local'], 'MEDIUM', 'RELAXED'),
    ('Shopping Enthusiast', 'SHOPPING', ['shopping', 'fashion'], 'LUXURY', 'PACKED'),
    ('Family Vacationer', 'FAMILY', ['kids', 'parks'], 'MEDIUM', 'RELAXED'),
    ('Romantic Couple', 'ROMANTIC', ['scenic', 'quiet'], 'LUXURY', 'RELAXED'),
]

all_rankings = {}
latencies = []

for user_name, mood, interests, budget, pace in user_profiles:
    print(f"\n{'='*80}")
    print(f"USER: {user_name}")
    print(f"  Mood: {mood}, Budget: {budget}, Pace: {pace}")
    print(f"{'='*80}")
    
    # Rank all places for this user
    print(f"Ranking {len(places)} places...")
    
    try:
        start = time.time()
        ranked = ranker.rank_places(
            user_mood=mood,
            candidate_places=places,
            user_interests=interests,
            user_budget=budget,
            user_pace=pace,
            day_index=0,
            trip_total_days=3,
            hotel_location=(hotel_lat, hotel_lng),
            previously_visited=[],
        )
        elapsed_ms = (time.time() - start) * 1000
        latencies.append(elapsed_ms)
        
        print(f"✓ Ranked in {elapsed_ms:.2f}ms\n")
        
        # Print top 10
        print("TOP 10 PLACES:")
        print("-" * 80)
        print(f"{'Rank':<6} | {'Place Name':<35} | {'Score':<10} | {'Category':<15}")
        print("-" * 80)
        
        top_places = []
        for rank, (place, score) in enumerate(ranked[:10], 1):
            top_places.append(place.name)
            print(f"{rank:<6} | {place.name[:33]:<35} | {score:<10.4f} | {place.category:<15}")
        
        all_rankings[user_name] = {
            'mood': mood,
            'top_10': top_places,
            'latency': elapsed_ms,
        }
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# Check if rankings differ by user
print(f"\n{'='*80}")
print("SECTION: DO RANKINGS PERSONALIZE?")
print(f"{'='*80}")

if all_rankings:
    # Count how many users have each place in top 10
    place_counts = {}
    for user_name, data in all_rankings.items():
        for place in data['top_10']:
            place_counts[place] = place_counts.get(place, 0) + 1
    
    # Sort by frequency
    most_common = sorted(place_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nMost common places in top 10 across all users:")
    for place, count in most_common[:5]:
        print(f"  {place:<40}: appears in {count}/5 users")
    
    if most_common[0][1] >= 4:
        print(f"\n✗ WARNING: Same places ranking high for all users!")
        print("   Model may not be personalizing correctly.")
    else:
        print(f"\n✓ PASS: Different places rank for different users")
        print("   Model is personalizing by user preferences.")

# Check latency
print(f"\n{'='*80}")
print("SECTION: INFERENCE LATENCY")
print(f"{'='*80}")

if latencies:
    print(f"\nRanking latency across {len(latencies)} users:")
    print(f"  Min:     {np.min(latencies):.2f}ms")
    print(f"  Max:     {np.max(latencies):.2f}ms")
    print(f"  Average: {np.mean(latencies):.2f}ms")
    
    avg_lat = np.mean(latencies)
    if avg_lat < 10:
        print(f"  ✓ PASS: Fast enough for real-time use")
    elif avg_lat < 100:
        print(f"  ⚠ ACCEPTABLE: Usable but not ultra-fast")
    else:
        print(f"  ✗ SLOW: May cause UX issues")

# Final verdict
print(f"\n{'='*80}")
print("FINAL VERDICT")
print(f"{'='*80}")

conclusions = []

if range_spread > 0.05:
    conclusions.append("✓ Good prediction diversity")
elif range_spread > 0.02:
    conclusions.append("⚠ Low prediction diversity")
else:
    conclusions.append("✗ Predictions too clustered")

if train_r2 > 0.2 and test_r2 > 0.1:
    conclusions.append("✓ Model learns patterns")
else:
    conclusions.append("⚠ Weak model performance")

if overfit_delta <= 0.2:
    conclusions.append("✓ Good generalization")
else:
    conclusions.append("✗ Overfitting detected")

if all_rankings and most_common[0][1] < 4:
    conclusions.append("✓ Personalizes by user")
else:
    conclusions.append("✗ No personalization")

if latencies and np.mean(latencies) < 100:
    conclusions.append("✓ Acceptable latency")
else:
    conclusions.append("✗ Slow predictions")

print("\nFindings:")
for c in conclusions:
    print(f"  {c}")

# Overall
positive = sum(1 for c in conclusions if c.startswith("✓"))
total = len(conclusions)

print(f"\n{'='*80}")
if positive >= 4:
    print("✓✓✓ MODEL IS PRODUCTION READY ✓✓✓")
    print(f"\nPassed {positive}/{total} quality checks")
elif positive >= 3:
    print("⚠ MODEL IS ACCEPTABLE")
    print(f"\nPassed {positive}/{total} quality checks (review issues)")
else:
    print("✗ MODEL NEEDS IMPROVEMENT")
    print(f"\nPassed {positive}/{total} quality checks (do not deploy)")

print("="*80 + "\n")
