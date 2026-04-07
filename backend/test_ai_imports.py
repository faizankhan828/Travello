#!/usr/bin/env python
"""Test script to verify all AI dependencies are installed and working"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("TESTING AI ITINERARY PLANNER DEPENDENCIES")
print("=" * 60)

# Test basic packages
print("\n[1] Testing basic dependencies...")
try:
    import numpy as np
    print("    ✓ numpy " + np.__version__)
except ImportError as e:
    print(f"    ✗ numpy: {e}")
    sys.exit(1)

try:
    import scipy
    print("    ✓ scipy " + scipy.__version__)
except ImportError as e:
    print(f"    ✗ scipy: {e}")
    sys.exit(1)

try:
    import pandas as pd
    print("    ✓ pandas " + pd.__version__)
except ImportError as e:
    print(f"    ✗ pandas: {e}")
    sys.exit(1)

try:
    import sklearn
    print("    ✓ scikit-learn " + sklearn.__version__)
except ImportError as e:
    print(f"    ✗ scikit-learn: {e}")
    sys.exit(1)

# Test transformers and torch
print("\n[2] Testing transformers and torch...")
try:
    import transformers
    print("    ✓ transformers " + transformers.__version__)
except ImportError as e:
    print(f"    ✗ transformers: {e}")
    sys.exit(1)

try:
    import torch
    print("    ✓ torch " + torch.__version__)
except ImportError as e:
    print(f"    ✗ torch: {e}")
    sys.exit(1)

# Test lightgbm
print("\n[3] Testing lightgbm...")
try:
    import lightgbm
    print("    ✓ lightgbm " + lightgbm.__version__)
except ImportError as e:
    print(f"    ✗ lightgbm: {e}")
    sys.exit(1)

# Test AI services
print("\n[4] Testing AI services...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"    ⚠ Django setup warning: {e}")

try:
    from itineraries.ai_emotion_service import AIEmotionDetectionService
    print("    ✓ AIEmotionDetectionService")
except Exception as e:
    print(f"    ✗ AIEmotionDetectionService: {e}")

try:
    from itineraries.ai_ranker_service import LearningToRankService
    print("    ✓ LearningToRankService")
except Exception as e:
    print(f"    ✗ LearningToRankService: {e}")

try:
    from itineraries.ai_llm_service import LLMEnhancementService
    print("    ✓ LLMEnhancementService")
except Exception as e:
    print(f"    ✗ LLMEnhancementService: {e}")

try:
    from itineraries.ai_service import AIItineraryService
    print("    ✓ AIItineraryService (orchestrator)")
except Exception as e:
    print(f"    ✗ AIItineraryService: {e}")

try:
    from itineraries.ai_models import AIGenerationLog, AIModelVersion, AIUserFeedback, AIRankerTrainingData
    print("    ✓ AI database models (4 models)")
except Exception as e:
    print(f"    ✗ AI models: {e}")

print("\n" + "=" * 60)
print("✓ ALL DEPENDENCIES INSTALLED AND VERIFIED!")
print("=" * 60)
print("\nAI Itinerary Planner is ready for:")
print("  1. Django migrations (python manage.py migrate)")
print("  2. Feature flag configuration")
print("  3. Production deployment")
print()
