"""
Diagnostic script to analyze target variable distribution.
Identifies why model has perfect fit (RMSE=0, R²=1)
"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

import numpy as np
from collections import Counter
from itineraries.ranker_data_analyzer import RankerDataAnalyzer
from itineraries.feature_extractor import FeatureExtractor

print("=" * 70)
print("TARGET VARIABLE DIAGNOSTIC")
print("=" * 70)

# Collect data
analyzer = RankerDataAnalyzer(verbose=False)
report = analyzer.analyze(city='Lahore')
samples = analyzer.samples

print(f"\n[1] DATA SUMMARY")
print(f"    Total samples: {len(samples)}")
print(f"    Positive (selected): {sum(1 for s in samples if s.was_selected)}")
print(f"    Negative (not selected): {sum(1 for s in samples if not s.was_selected)}")

# Extract targets
y = np.array([s.selection_quality for s in samples], dtype=np.float32)

print(f"\n[2] TARGET VARIABLE DISTRIBUTION (selection_quality)")
print(f"    Min:      {y.min():.6f}")
print(f"    Max:      {y.max():.6f}")
print(f"    Mean:     {y.mean():.6f}")
print(f"    Std:      {y.std():.6f}")
print(f"    Median:   {np.median(y):.6f}")
print(f"    Unique values: {len(np.unique(y))}")

# Check if constant
if y.std() == 0:
    print(f"    ⚠️  WARNING: Target is CONSTANT (all values = {y[0]:.6f})")
    print(f"    This explains RMSE=0, R²=1 - model is just predicting a constant!")
else:
    print(f"    ✓ Target has variance - model can learn")

# Distribution
print(f"\n[3] TARGET DISTRIBUTION")
unique_vals, counts = np.unique(y, return_counts=True)
for val, count in sorted(zip(unique_vals, counts), key=lambda x: -x[1])[:10]:
    pct = 100 * count / len(y)
    print(f"    {val:.6f}: {count:5d} samples ({pct:5.1f}%)")

# Sample values
print(f"\n[4] SAMPLE TARGET VALUES (first 10)")
for i, s in enumerate(samples[:10]):
    status = "SELECTED" if s.was_selected else "NOT SELECTED"
    print(f"    {i+1}. {s.place_name:30s} {status:12s} quality={s.selection_quality:.3f}")

# Extract features to see correlation
print(f"\n[5] FEATURES ANALYSIS")
X, y_check = FeatureExtractor.extract_features(samples)
print(f"    Feature shape: {X.shape}")
print(f"    Features are normalized: min={X.min():.3f}, max={X.max():.3f}")

# Check feature variance
print(f"\n    Feature variance (top 5):")
feature_var = np.var(X, axis=0)
top_var_idx = np.argsort(feature_var)[-5:][::-1]
for idx in top_var_idx:
    col_name = FeatureExtractor.FEATURE_COLUMNS[idx]
    variance = feature_var[idx]
    print(f"      {col_name}: {variance:.4f}")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
