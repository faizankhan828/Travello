"""Quick test of hybrid ranking"""
import sys
import os
import traceback

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'f:\\FYP\\Travello\\backend')

try:
    print("[1] Importing modules...")
    from itineraries.ai_ranker_service import LearningToRankService
    print("  - LearningToRankService imported")
    
    from itineraries.hf_ranker import create_hf_ranker
    print("  - HF ranker imported")
    
    from itineraries.combined_ranker import CombinedRanker
    print("  - CombinedRanker imported")
    
    print("\n[2] Loading models...")
    model_path = 'f:\\FYP\\Travello\\backend\\ml_models\\itinerary_ranker.pkl'
    lgb_ranker = LearningToRankService(model_path=model_path)
    print(f"  - LGB ranker loaded")
    
    hf_ranker = create_hf_ranker()
    print(f"  - HF ranker loaded")
    
    print("\n[3] Creating combined ranker...")
    combined = CombinedRanker(lgb_ranker, hf_ranker)
    print(f"  - Combined ranker created")
    
    print("\n[4] Testing ranking...")
    places = [
        {'id': 'fort', 'name': 'Lahore Fort', 'category': 'historical', 'rating': 4.8},
        {'id': 'food', 'name': 'Food Street', 'category': 'food', 'rating': 4.5},
    ]
    
    result = combined.rank_places_hybrid(
        user_mood='HISTORICAL',
        candidate_places=places,
        user_interests=['history'],
        user_budget='MEDIUM',
        hf_enabled=True
    )
    
    print(f"  - Ranking successful!")
    for r in result[:2]:
        print(f"    {r['place_name']}: {r['combined_score']:.3f}")
    
    print("\n[SUCCESS]")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    traceback.print_exc()
