"""
Retrain the LightGBM model with corrected target data.
Generate predictions and verify model learns meaningful signals.
"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

import numpy as np
from itineraries.ranker_model_trainer import RankerModelTrainer

print("=" * 70)
print("RETRAINING ML RANKER MODEL - FIXED TARGET")
print("=" * 70)

# Train with corrected data
trainer = RankerModelTrainer(verbose=True)

# Collect data (now with proper selection extraction)
samples, report = trainer.collect_data(city='Lahore', use_synthetic=False)

print(f"\n[1] DATA QUALITY")
print(f"    Total samples: {len(samples)}")
print(f"    Selected: {sum(1 for s in samples if s.was_selected)}")
print(f"    Not selected: {sum(1 for s in samples if not s.was_selected)}")

# Train model
metrics = trainer.train(samples)

# Evaluate
trainer.evaluate(metrics)

# Save model
model_path = os.path.join(os.path.dirname(__file__), 'ml_models', 'itinerary_ranker.pkl')
saved_path = trainer.save_model(model_path)

print(f"\n" + "=" * 70)
print(f"TRAINING COMPLETE - Model saved to {saved_path}")
print("=" * 70)

# Validate: Generate predictions for different places
print(f"\n[2] PREDICTION VALIDATION")
print(f"    Generating predictions for 5 different places...")

from itineraries.ai_ranker_service import LearningToRankService
from itineraries.feature_extractor import FeatureExtractor

# Initialize service with trained model
ranker = LearningToRankService(model_path=model_path)

# Select 5 diverse samples
sample_indices = [0, 100, 500, 1000, 5000]
test_samples = [samples[i] for i in sample_indices]

predictions = []
for idx, sample in enumerate(test_samples, 1):
    # Extract features
    features = FeatureExtractor.extract_features([sample])
    X = features[0]
    
    # Predict
    if ranker.model and ranker.scaler:
        X_scaled = ranker.scaler.transform(X.reshape(1, -1))
        pred_raw = ranker.model.predict(X_scaled)[0]
        pred_score = 1.0 / (1.0 + np.exp(-pred_raw))
    else:
        pred_score = 0.5
    
    predictions.append((sample.place_name, sample.was_selected, sample.selection_quality, pred_score))
    
    status = "SEL" if sample.was_selected else "NOT"
    print(f"    {idx}. {sample.place_name:35s} {status:3s} target={sample.selection_quality:.3f} pred={pred_score:.3f}")

print(f"\n[3] VALIDATION CHECKS")
pred_scores = [p[3] for p in predictions]
print(f"    Min prediction: {min(pred_scores):.4f}")
print(f"    Max prediction: {max(pred_scores):.4f}")
print(f"    Unique predictions: {len(set(round(p, 4) for p in pred_scores))}")

if len(set(round(p, 4) for p in pred_scores)) > 1:
    print(f"    ✓ PASS: Model generates DIFFERENT predictions")
else:
    print(f"    ✗ FAIL: All predictions are the same")

print("\n" + "=" * 70)
print("RETRAINING COMPLETE ✓")
print("=" * 70)
