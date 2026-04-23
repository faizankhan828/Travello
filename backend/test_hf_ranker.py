"""
Test HuggingFace ranker with sample data
"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

from itineraries.hf_ranker import HFPlaceRanker, create_hf_ranker
import time

print("\n" + "="*80)
print("TESTING HUGGINGFACE RANKER")
print("="*80)

# Create ranker
print("\n[1] Creating HF ranker...")
ranker = create_hf_ranker(device="cpu")

if not ranker:
    print("✗ Failed to create HF ranker")
    sys.exit(1)

if not ranker.model_loaded:
    print("✗ Model not loaded")
    sys.exit(1)

print("✓ HF ranker created successfully")
print(f"  Model: {ranker.model_name}")
print(f"  Device: {ranker.device}")
print(f"  Embedding dimension: {ranker.EMBEDDING_DIM}")

# Test 1: User profile encoding
print("\n[2] Testing user profile encoding...")

user_mood = "HISTORICAL"
user_interests = ["history", "culture", "architecture"]
user_budget = "MEDIUM"
user_pace = "BALANCED"

user_embedding = ranker.encode_user_profile(user_mood, user_interests, user_budget, user_pace)
if user_embedding is not None:
    print(f"✓ User embedding created")
    print(f"  Shape: {user_embedding.shape}")
    print(f"  Mean: {user_embedding.mean():.4f}")
    print(f"  Std: {user_embedding.std():.4f}")
else:
    print("✗ Failed to encode user")

# Test 2: Place encoding
print("\n[3] Testing place encoding...")

sample_places = [
    {
        'id': 1,
        'name': 'Lahore Fort',
        'category': 'Historical',
        'average_rating': 4.8,
        'tags': ['history', 'culture', 'architecture']
    },
    {
        'id': 2,
        'name': 'Gawalmandi Food Street',
        'category': 'Food',
        'average_rating': 4.5,
        'tags': ['food', 'local', 'restaurants']
    },
    {
        'id': 3,
        'name': 'Mall Road Shopping',
        'category': 'Shopping',
        'average_rating': 4.2,
        'tags': ['shopping', 'brands', 'markets']
    },
    {
        'id': 4,
        'name': 'Bagh-e-Jinnah (Lawrence Gardens)',
        'category': 'Nature',
        'average_rating': 4.6,
        'tags': ['nature', 'parks', 'outdoor', 'relaxing']
    },
]

print(f"\nEncoding {len(sample_places)} sample places...")
for place in sample_places:
    place_embedding = ranker.encode_place(place)
    if place_embedding is not None:
        print(f"  ✓ {place['name']:<40} ({place_embedding.shape})")
    else:
        print(f"  ✗ {place['name']}")

# Test 3: Ranking test
print("\n[4] Testing ranking with different user types...")

test_users = [
    {
        'name': 'Historical Tourist',
        'mood': 'HISTORICAL',
        'interests': ['history', 'culture'],
        'budget': 'MEDIUM',
        'pace': 'BALANCED'
    },
    {
        'name': 'Food Lover',
        'mood': 'FOODIE',
        'interests': ['food', 'local'],
        'budget': 'MEDIUM',
        'pace': 'RELAXED'
    },
    {
        'name': 'Shopping Enthusiast',
        'mood': 'SHOPPING',
        'interests': ['shopping', 'fashion'],
        'budget': 'LUXURY',
        'pace': 'PACKED'
    },
]

for user in test_users:
    print(f"\n  User: {user['name']} ({user['mood']})")
    
    start = time.time()
    scores = ranker.rank_places(
        user_mood=user['mood'],
        user_interests=user['interests'],
        user_budget=user['budget'],
        user_pace=user['pace'],
        candidate_places=sample_places
    )
    elapsed = (time.time() - start) * 1000
    
    if scores:
        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        print(f"    Latency: {elapsed:.2f}ms")
        print(f"    Top 3 places:")
        for place_id, score in ranked[:3]:
            place_name = next(p['name'] for p in sample_places if p['id'] == place_id)
            print(f"      • {place_name:<40} : {score:.4f}")
    else:
        print(f"    ✗ No scores returned")

# Test 4: Cosine similarity check
print("\n[5] Verifying semantic similarity logic...")

# Historical user should match fort better than food street
hist_user_embedding = ranker.encode_user_profile('HISTORICAL', ['history'], 'MEDIUM', 'BALANCED')
fort_embedding = ranker.encode_place(sample_places[0])  # Lahore Fort
food_embedding = ranker.encode_place(sample_places[1])  # Food street

fort_score = ranker.cosine_similarity(hist_user_embedding, fort_embedding)
food_score = ranker.cosine_similarity(hist_user_embedding, food_embedding)

print(f"\n  Historical user vs Lahore Fort: {fort_score:.4f}")
print(f"  Historical user vs Food Street: {food_score:.4f}")

if fort_score > food_score:
    print(f"  ✓ PASS: Fort scores higher than food street for history user")
    print(f"    Difference: {fort_score - food_score:.4f}")
else:
    print(f"  ✗ WARNING: Food street scores higher (may indicate model limitation)")

# Test 5: Performance benchmark
print("\n[6] Performance benchmark...")

print(f"  Encoding 5 users...")
start = time.time()
for _ in range(5):
    ranker.encode_user_profile('HISTORICAL', ['history'], 'MEDIUM', 'BALANCED')
user_time = (time.time() - start) / 5 * 1000

print(f"  Encoding 20 places...")
start = time.time()
for _ in range(20):
    ranker.encode_place(sample_places[0])
place_time = (time.time() - start) / 20 * 1000

print(f"  Ranking 100 places...")
start = time.time()
ranker.rank_places('HISTORICAL', ['history'], 'MEDIUM', 'BALANCED', sample_places * 25)
rank_time = (time.time() - start) * 1000

print(f"  Average user encoding:  {user_time:.2f}ms")
print(f"  Average place encoding: {place_time:.2f}ms")
print(f"  Ranking 100 places:     {rank_time:.2f}ms")

if rank_time < 1000:
    print(f"  ✓ Performance acceptable (<1s for 100 places)")
else:
    print(f"  ⚠ Performance warning (>1s for 100 places)")

print("\n" + "="*80)
print("HF RANKER TEST COMPLETE")
print("="*80 + "\n")
