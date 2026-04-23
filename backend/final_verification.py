"""
DEEP MODEL QUALITY VERIFICATION - FINAL
========================================
Tests:
1. Load model and check metadata
2. Test 5 user scenarios with real place ranking
3. Verify predictions are diverse and personalized
4. Measure performance and latency
"""

import os
import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

import random
import numpy as np
import pickle
import time
from collections import defaultdict
from itineraries.models import Place, Itinerary
from itineraries.ai_ranker_service import LearningToRankService

print("\n" + "="*80)
print("DEEP MODEL QUALITY VERIFICATION")
print("="*80)

# Load model
model_path = os.path.join(
    os.path.dirname(__file__),
    'ml_models',
    'itinerary_ranker.pkl'
)

print(f"\n[1] LOADING MODEL")
print("-" * 80)
ranker = LearningToRankService(model_path=model_path)

if not ranker.model:
    print("ERROR: Model not loaded!")
    sys.exit(1)

print(f"[OK] Model loaded successfully")

# Load metadata
with open(model_path, 'rb') as f:
    model_package = pickle.load(f)

train_r2 = model_package.get('metrics', {}).get('train_r2', 0)
test_r2 = model_package.get('metrics', {}).get('test_r2', 0)
train_rmse = model_package.get('metrics', {}).get('train_rmse', 0)
test_rmse = model_package.get('metrics', {}).get('test_rmse', 0)

print(f"    Training Metrics:")
print(f"      Train R^2: {train_r2:.4f}")
print(f"      Test R^2:  {test_r2:.4f}")
print(f"      Train RMSE: {train_rmse:.4f}")
print(f"      Test RMSE:  {test_rmse:.4f}")

# Get places
print(f"\n[2] GATHERING TEST DATA")
print("-" * 80)
places = list(Place.objects.filter(city='Lahore')[:100])
print(f"[OK] Found {len(places)} places")

# Get default hotel location
itinerary = Itinerary.objects.first()
hotel_lat, hotel_lng = 31.5, 74.3

print(f"\n[3] TESTING 5 USER SCENARIOS")
print("-" * 80)

user_profiles = [
    ('Historical Tourist', 'HISTORICAL', ['history', 'culture'], 'MEDIUM', 'BALANCED'),
    ('Food Lover', 'FOODIE', ['food', 'local'], 'MEDIUM', 'RELAXED'),
    ('Shopping Enthusiast', 'SHOPPING', ['shopping', 'fashion'], 'LUXURY', 'PACKED'),
    ('Family Vacationer', 'FAMILY', ['kids', 'parks'], 'MEDIUM', 'RELAXED'),
    ('Romantic Couple', 'ROMANTIC', ['scenic', 'quiet'], 'LUXURY', 'RELAXED'),
]

all_rankings = {}
latencies = []
all_predictions = []

for user_idx, (user_name, mood, interests, budget, pace) in enumerate(user_profiles, 1):
    print(f"\n  User {user_idx}: {user_name} (mood={mood})")
    
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
        
        # Extract top 10 (RankedPlace objects)
        top_10 = []
        for rank, ranked_place in enumerate(ranked[:10], 1):
            # RankedPlace has place_name and score attributes
            place_name = ranked_place.place_name
            score = ranked_place.score
            top_10.append((place_name, float(score)))
            all_predictions.append(float(score))
        
        all_rankings[user_name] = {
            'mood': mood,
            'top_10': top_10,
            'latency': elapsed_ms,
        }
        
        print(f"    Latency: {elapsed_ms:.2f}ms")
        print(f"    Top 3 places:")
        for i, (name, score) in enumerate(top_10[:3], 1):
            print(f"      {i}. {name} (score: {score:.4f})")
        
    except Exception as e:
        print(f"    ERROR: {e}")

# Analysis
print(f"\n[4] ANALYSIS & STATISTICS")
print("-" * 80)

if all_predictions:
    print(f"\n  Prediction Range:")
    print(f"    Min:       {np.min(all_predictions):.4f}")
    print(f"    Max:       {np.max(all_predictions):.4f}")
    print(f"    Mean:      {np.mean(all_predictions):.4f}")
    print(f"    Std Dev:   {np.std(all_predictions):.4f}")
    
    range_spread = np.max(all_predictions) - np.min(all_predictions)
    print(f"    Spread:    {range_spread:.4f}")
    
    if range_spread > 0.05:
        print(f"    [OK] Good prediction diversity")
    elif range_spread > 0.02:
        print(f"    [WARN] Low diversity")
    else:
        print(f"    [ISSUE] Predictions too clustered")

if latencies:
    avg_lat = np.mean(latencies)
    print(f"\n  Inference Latency ({len(latencies)} rankings):")
    print(f"    Min:       {np.min(latencies):.2f}ms")
    print(f"    Max:       {np.max(latencies):.2f}ms")
    print(f"    Average:   {avg_lat:.2f}ms")
    
    if avg_lat < 10:
        print(f"    [OK] Fast (real-time)")
    elif avg_lat < 100:
        print(f"    [OK] Acceptable")
    else:
        print(f"    [ISSUE] Slow")

if all_rankings:
    # Count place frequencies
    place_counts = defaultdict(int)
    for user_name, data in all_rankings.items():
        for place_name, score in data['top_10']:
            place_counts[place_name] += 1
    
    most_common = sorted(place_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n  Personalization Check:")
    print(f"    Most common places in top 10:")
    for place, count in most_common[:3]:
        print(f"      - {place}: {count}/5 users")
    
    if most_common[0][1] >= 4:
        print(f"    [ISSUE] Same places for all users (no personalization)")
    else:
        print(f"    [OK] Rankings vary by user")

# Model quality
print(f"\n  Model Quality:")
overfit_delta = train_r2 - test_r2
print(f"    Train-Test R^2 delta: {overfit_delta:.4f}")

if overfit_delta > 0.2:
    print(f"    [WARN] Possible overfitting")
elif overfit_delta > 0.1:
    print(f"    [OK] Minor overfitting, acceptable")
else:
    print(f"    [OK] Good generalization")

if train_r2 > 0.2:
    print(f"    [OK] Model learns patterns (R^2={train_r2:.4f})")
else:
    print(f"    [WARN] Weak training performance (R^2={train_r2:.4f})")

# Feature importance
print(f"\n  Feature Importance:")
if hasattr(ranker.model, 'feature_importance'):
    fi = ranker.model.feature_importance()
    features = ranker.feature_columns
    if fi is not None and features:
        importance_pairs = sorted(zip(features, fi), key=lambda x: x[1], reverse=True)
        print(f"    Top 5 Features:")
        for rank, (feat, imp) in enumerate(importance_pairs[:5], 1):
            print(f"      {rank}. {feat}: {imp:.1f}")

# FINAL VERDICT
print(f"\n" + "="*80)
print("FINAL VERDICT")
print("="*80)

score_card = []

# Check 1: Diversity
if all_predictions:
    if np.max(all_predictions) - np.min(all_predictions) > 0.05:
        score_card.append(("Prediction Diversity", "PASS"))
    elif np.max(all_predictions) - np.min(all_predictions) > 0.02:
        score_card.append(("Prediction Diversity", "WARN"))
    else:
        score_card.append(("Prediction Diversity", "FAIL"))

# Check 2: Model Learning
if train_r2 > 0.2 and test_r2 > 0.1:
    score_card.append(("Model Learning", "PASS"))
elif train_r2 > 0.1:
    score_card.append(("Model Learning", "WARN"))
else:
    score_card.append(("Model Learning", "FAIL"))

# Check 3: Generalization
if overfit_delta <= 0.2:
    score_card.append(("Generalization", "PASS"))
elif overfit_delta <= 0.3:
    score_card.append(("Generalization", "WARN"))
else:
    score_card.append(("Generalization", "FAIL"))

# Check 4: Personalization
if all_rankings and most_common[0][1] < 4:
    score_card.append(("Personalization", "PASS"))
else:
    score_card.append(("Personalization", "FAIL"))

# Check 5: Latency
if latencies and np.mean(latencies) < 100:
    score_card.append(("Latency", "PASS"))
else:
    score_card.append(("Latency", "WARN"))

# Print scorecard
print("\nScorecard:")
passes = 0
for check, result in score_card:
    status = "[OK]" if result == "PASS" else ("[WARN]" if result == "WARN" else "[FAIL]")
    print(f"  {status} {check}")
    if result == "PASS":
        passes += 1

# Final result
print(f"\nResult: {passes}/{len(score_card)} checks passed")

if passes >= 4:
    print("\n>>> MODEL IS PRODUCTION READY")
    print("    The model demonstrates good quality and is ready for deployment.")
elif passes >= 3:
    print("\n>>> MODEL IS ACCEPTABLE")
    print("    The model works but monitor the flagged issues.")
else:
    print("\n>>> MODEL HAS ISSUES")
    print("    Do not deploy without addressing failures.")

print("=" * 80 + "\n")
