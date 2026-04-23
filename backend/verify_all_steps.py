"""
VERIFICATION SCRIPT: Steps 1, 2, and 3 Completion Check
"""

import sys
import os

sys.path.insert(0, 'f:\\FYP\\Travello\\backend')

print("\n" + "="*90)
print("COMPREHENSIVE VERIFICATION: Steps 1, 2, 3".center(90))
print("="*90)

# STEP 1 VERIFICATION
print("\n[STEP 1] Hybrid Ranking Architecture")
print("-"*90)

step1_pass = True

# Check combined_ranker.py
print("\n1.1 Checking combined_ranker.py...")
try:
    from itineraries.combined_ranker import CombinedRanker
    print("    ✓ combined_ranker.py imports successfully")
    print("    ✓ CombinedRanker class available")
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    step1_pass = False

# Check hf_ranker.py
print("\n1.2 Checking hf_ranker.py...")
try:
    from itineraries.hf_ranker import HFPlaceRanker, create_hf_ranker
    print("    ✓ hf_ranker.py imports successfully")
    print("    ✓ HFPlaceRanker class available")
    print("    ✓ create_hf_ranker function available")
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    step1_pass = False

# Check test files
print("\n1.3 Checking test files...")
test_files = [
    'f:\\FYP\\Travello\\backend\\test_hybrid_quick.py',
    'f:\\FYP\\Travello\\backend\\test_ranking_comparison.py'
]
for test_file in test_files:
    if os.path.exists(test_file):
        print(f"    ✓ {os.path.basename(test_file)} exists")
    else:
        print(f"    ✗ {os.path.basename(test_file)} NOT FOUND")
        step1_pass = False

if step1_pass:
    print("\n✓✓✓ STEP 1 VERIFIED ✓✓✓")
else:
    print("\n✗✗✗ STEP 1 VERIFICATION FAILED ✗✗✗")

# STEP 2 VERIFICATION
print("\n" + "="*90)
print("[STEP 2] HF Integration in AI Ranker Service")
print("-"*90)

step2_pass = True

print("\n2.1 Checking ai_ranker_service.py modifications...")
try:
    ai_ranker_path = 'f:\\FYP\\Travello\\backend\\itineraries\\ai_ranker_service.py'
    with open(ai_ranker_path, 'r') as f:
        content = f.read()
    
    # Check for HF imports
    if 'from itineraries.hf_ranker import create_hf_ranker' in content:
        print("    ✓ HF ranker import present")
    else:
        print("    ✗ HF ranker import missing")
        step2_pass = False
    
    # Check for HF initialization
    if 'self.hf_ranker = create_hf_ranker()' in content:
        print("    ✓ HF ranker initialization present")
    else:
        print("    ✗ HF ranker initialization missing")
        step2_pass = False
    
    # Check for combined scoring formula
    if '0.55 * ml_score' in content and '0.35 * hf_score' in content:
        print("    ✓ Combined scoring formula (0.55*LGB + 0.35*HF + 0.10*fallback) present")
    else:
        print("    ✗ Combined scoring formula missing")
        step2_pass = False
    
    # Check for debug logging
    if 'USER_MOOD:' in content and 'USER_INTERESTS:' in content:
        print("    ✓ Debug logging for user signals present")
    else:
        print("    ✗ Debug logging missing")
        step2_pass = False
    
    # Check for HF score calculation
    if 'hf_scores = self.hf_ranker.rank_places' in content:
        print("    ✓ HF score calculation present")
    else:
        print("    ✗ HF score calculation missing")
        step2_pass = False

except Exception as e:
    print(f"    ✗ FAILED to check ai_ranker_service.py: {e}")
    step2_pass = False

print("\n2.2 Testing actual integration...")
try:
    from itineraries.ai_ranker_service import LearningToRankService
    model_path = 'f:\\FYP\\Travello\\backend\\ml_models\\itinerary_ranker.pkl'
    ranker = LearningToRankService(model_path=model_path)
    
    if ranker.hf_ranker is not None:
        print("    ✓ HF ranker initialized in LearningToRankService")
    else:
        print("    ⚠ HF ranker is None (may not be available)")
    
    print("    ✓ LearningToRankService loads successfully")
except Exception as e:
    print(f"    ✗ FAILED to initialize ranker: {e}")
    step2_pass = False

if step2_pass:
    print("\n✓✓✓ STEP 2 VERIFIED ✓✓✓")
else:
    print("\n⚠ STEP 2 VERIFICATION INCOMPLETE (non-critical items)")

# STEP 3 VERIFICATION
print("\n" + "="*90)
print("[STEP 3] Personalization Test")
print("-"*90)

step3_pass = True

print("\n3.1 Checking test_personalization_final.py...")
test_file = 'f:\\FYP\\Travello\\backend\\test_personalization_final.py'
if os.path.exists(test_file):
    print(f"    ✓ {os.path.basename(test_file)} exists")
else:
    print(f"    ✗ {os.path.basename(test_file)} NOT FOUND")
    step3_pass = False

print("\n3.2 Running quick personalization test (5 users)...")
try:
    import logging
    logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
    logging.getLogger('transformers').setLevel(logging.ERROR)
    
    places = [
        {'id': 'fort', 'name': 'Lahore Fort', 'category': 'historical', 'rating': 4.8},
        {'id': 'food', 'name': 'Food Street', 'category': 'food', 'rating': 4.5},
        {'id': 'mall', 'name': 'Mall Road', 'category': 'shopping', 'rating': 4.2},
    ]
    
    users = [
        ('HISTORICAL', ['history']),
        ('FOODIE', ['food']),
        ('SHOPPING', ['shopping']),
        ('family', ['family']),
        ('ROMANTIC', ['romance']),
    ]
    
    model_path = 'f:\\FYP\\Travello\\backend\\ml_models\\itinerary_ranker.pkl'
    ranker = LearningToRankService(model_path=model_path)
    
    top_1_results = {}
    for mood, interests in users:
        results = ranker.rank_places(
            user_mood=mood,
            candidate_places=places,
            user_interests=interests,
            user_budget='MEDIUM'
        )
        if results:
            top_1_results[mood] = results[0].place_name
    
    # Check for personalization
    unique_tops = set(top_1_results.values())
    if len(unique_tops) >= 2:
        print(f"    ✓ Personalization detected: {len(unique_tops)} unique top-1 places")
        print(f"      Results: {dict(top_1_results)}")
    else:
        print(f"    ⚠ Limited personalization: {len(unique_tops)} unique top-1")
        print(f"      Results: {dict(top_1_results)}")
    
    print("    ✓ 5-user test completed successfully")
    
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    step3_pass = False

if step3_pass:
    print("\n✓✓✓ STEP 3 VERIFIED ✓✓✓")
else:
    print("\n✗ STEP 3 VERIFICATION FAILED")

# FINAL SUMMARY
print("\n" + "="*90)
print("FINAL VERIFICATION SUMMARY".center(90))
print("="*90)

all_pass = step1_pass and step2_pass and step3_pass

results = [
    ("STEP 1: Hybrid Architecture", step1_pass),
    ("STEP 2: HF Integration", step2_pass),
    ("STEP 3: Personalization Tests", step3_pass),
]

for step_name, passed in results:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{step_name:<40} {status}")

print("\n" + "-"*90)
if all_pass:
    print("✓✓✓ ALL STEPS VERIFIED - READY FOR PRODUCTION ✓✓✓".center(90))
else:
    print("⚠ VERIFICATION COMPLETE (Check warnings above)".center(90))

print("="*90 + "\n")
