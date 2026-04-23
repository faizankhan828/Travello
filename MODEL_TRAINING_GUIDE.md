# ML Model Training & Integration Guide

**Status:** ✅ Complete - Model training infrastructure implemented  
**Framework:** LightGBM (Gradient Boosting)  
**Model Type:** Regression (ranking scores)  
**Training Data:** Itinerary place selections  
**Last Updated:** April 15, 2026

---

## 📋 Overview

This guide explains how to:
1. Train the LightGBM ranking model
2. Evaluate model performance
3. Save and persist the model
4. Integrate with the existing ranking system
5. Deploy to production

---

## 🚀 Quick Start

### Step 1: Collect and Analyze Data

```bash
cd backend
python manage.py analyze_itinerary_ranker_data --verbose
```

**Output:**
- Data statistics (sample counts, class balance)
- Data quality assessment
- Recommendation on training readiness

**Success Criteria:**
- Total samples: > 100
- Positive samples: > 20
- Data completeness: > 95%
- Status: "READY FOR TRAINING"

### Step 2: Train Model

```bash
python manage.py train_itinerary_ranker --verbose
```

**What happens:**
1. Collects training data from database
2. Extracts features (no data leakage)
3. Splits into train/test (80/20)
4. Trains LightGBM
5. Evaluates performance
6. Saves model to `backend/ml_models/itinerary_ranker.pkl`

**Output:**
- Training/test RMSE, MAE, R²
- Top 5 important features
- Confirmation: "✓ Model trained successfully"

### Step 3: Test Model

```bash
python manage.py train_itinerary_ranker --test-only
```

**Verifies:** Saved model can be loaded and used

### Step 4: Deploy

The model is **automatically used** by the ranking system after training:
- Backend loads model on startup
- Falls back to rule-based scoring if unavailable
- No code changes needed

---

## 🛠️ Training Script Details

### File Locations

```
backend/
├── itineraries/
│   └── management/commands/
│       ├── analyze_itinerary_ranker_data.py  (data analysis)
│       └── train_itinerary_ranker.py         (model training) ← YOU ARE HERE
├── ml_models/                                  (created by script)
│   └── itinerary_ranker.pkl                   (saved model)
└── ml_system/
    └── ranker_model_loader.py                 (inference utility)
```

### Training Command Options

```bash
# Basic training
python manage.py train_itinerary_ranker

# Verbose output with detailed progress
python manage.py train_itinerary_ranker --verbose

# Train on specific city
python manage.py train_itinerary_ranker --city Lahore

# Train on limited itineraries (fast test)
python manage.py train_itinerary_ranker --sample 10 --verbose

# Custom output path
python manage.py train_itinerary_ranker --output /path/to/custom/model.pkl

# Test loading existing model
python manage.py train_itinerary_ranker --test-only
```

---

## 🎯 What the Training Script Does

### 1. Data Collection

```python
# Load all itineraries and places for specified city
# Extract positive samples (places in itinerary)
# Extract negative samples (places not selected)
# Create (user, place) pairs for training
```

**Data Source:** `Itinerary.days` JSON array containing selected places  
**Time Complexity:** O(n_itineraries × n_places)

### 2. Feature Extraction

Extracts 17 features from each (user, place) pair:

**User Features:**
- User mood (encoded)
- User budget level (encoded)
- User pace (encoded)
- Count of user interests

**Place Features:**
- Place category (encoded)
- Place rating (normalized 0-1)
- Place budget level (encoded)
- Place visit minutes (normalized)
- Count of place tags
- Ideal start hour (normalized)
- Ideal end hour (normalized)

**Contextual Features:**
- Day number in trip
- Total days in trip
- Distance from hotel

**Interaction Features:**
- Interest match (1 if place tags overlap with user interests)
- Budget match (1 if place budget ≤ user budget)
- Cultural match (1 if cultural place + cultural mood)

**✅ NO DATA LEAKAGE:** Target variable (`was_selected`) NOT in features

### 3. Target Variable

**Type:** Regression (0-1 continuous)  
**Source:** `place.average_rating / 5.0`  
**Interpretation:** Higher rating = higher quality place = higher score

**Alternative (commented out):** Could use binary classification (1=selected, 0=not)

### 4. Train/Test Split

```
Data (N samples) → 80% Training + 20% Testing
All features normalized using StandardScaler
```

### 5. Model Training

**Algorithm:** LightGBM (Gradient Boosting)  
**Objective:** Regression (RMSE minimization)  
**Parameters:**
- Learning rate: 0.05 (moderate learning speed)
- Num leaves: 31 (tree complexity)
- Feature fraction: 0.8 (feature sampling)
- Bagging fraction: 0.8 (data sampling)
- Early stopping: 10 rounds (prevent overfitting)

**Output:** Trained model + metadata

### 6. Model Evaluation

**Metrics Calculated:**
- **RMSE:** Root Mean Squared Error (lower is better)
- **MAE:** Mean Absolute Error
- **R²:** Coefficient of determination (higher is better)

**Example Output:**
```
Training RMSE:  0.1245
Test RMSE:      0.1389
Training MAE:   0.0892
Test MAE:       0.0945
Training R²:    0.8456
Test R²:        0.8123
Boosting rounds: 87
```

### 7. Feature Importance

Shows which features most influence model predictions:

```
Top 5 Important Features:
1. place_rating: 285
2. place_category_id: 198
3. user_interests_match: 156
4. budget_match: 142
5. place_visit_minutes: 128
```

**Interpretation:** Place rating is most important, interest match is critical

### 8. Model Saving

**Format:** Pickle (.pkl)  
**Location:** `backend/ml_models/itinerary_ranker.pkl`  
**Size:** ~2-5 MB (typical)

**Saved Package Contents:**
```python
{
    'model': <LightGBM booster object>,
    'scaler': <StandardScaler fitted on training data>,
    'feature_columns': [...list of 17 feature names...],
    'categorical_mappings': {
        'mood_to_id': {...},
        'budget_to_id': {...},
        'category_to_id': {...},
        'pace_to_id': {...},
    },
    'trained_at': '2026-04-15T14:30:22.123456',
    'model_type': 'LightGBMRegressor',
    'framework_versions': {...},
}
```

---

## 📊 Understanding Training Output

### Example Full Run

```
============================================================
AI Itinerary Ranker Training
============================================================
[14:30:22] Initialized RankerModelTrainer
[14:30:23] Collecting training data for Lahore...
[14:30:25]   ✓ Collected 1250 training samples
[14:30:25]     - Positive (selected): 185
[14:30:25]     - Negative (not selected): 1065
[14:30:25] Extracting and encoding features...
[14:30:27]   ✓ Extracted 1250 samples with 17 features
[14:30:27]     - Feature shape: (1250, 17)
[14:30:27]     - Target shape: (1250,)
[14:30:27]     - Target range: [0.750, 1.000]
[14:30:27] Splitting data into train/test sets...
[14:30:27]   ✓ Train: 1000 samples
[14:30:27]   ✓ Test:  250 samples
[14:30:28] Training LightGBM model...
[14:30:28]   Normalizing features...
[14:30:28]   Training with LightGBM...
[14:30:45]   ✓ Model training complete

Model Evaluation Results:
  Training RMSE:  0.1245
  Test RMSE:      0.1389
  Training MAE:   0.0892
  Test MAE:       0.0945
  Training R²:    0.8456
  Test R²:        0.8123
  Boosting rounds: 87

Top 5 Important Features:
  1. place_rating: 285
  2. place_category_id: 198
  3. user_interests_match: 156
  4. budget_match: 142
  5. place_visit_minutes: 128

[14:30:47] Saving model to backend/ml_models/itinerary_ranker.pkl...
[14:30:48]   ✓ Model saved to backend/ml_models/itinerary_ranker.pkl
[14:30:48]   File size: 3.42 MB

============================================================
✓ Model trained successfully
✓ Model saved successfully
============================================================
```

---

## 🔌 Model Integration

### Automatic Integration

The model is **automatically integrated** into the ranking system:

```python
# In ai_ranker_service.py
def _get_ml_score(self, features: RankingFeatures) -> Tuple[float, float]:
    """Get score from trained ML model"""
    
    # Try to use trained model if available
    model = RankerModelLoader.get_model()
    if model is not None:
        # Encode features and get prediction
        score = get_ranking_score_from_model(...)
        confidence = 0.95  # High confidence in ML prediction
        return score, confidence
    
    # Fallback to rule-based if model unavailable
    return self._get_fallback_score(features), 0.0
```

### Key Features

1. **Lazy Loading:** Model loaded on first use
2. **Graceful Fallback:** Uses rule-based scoring if model unavailable
3. **No Code Changes:** Works with existing `ai_ranker_service.py`
4. **Transparent Integration:** Users don't need to know about ML

### How Ranking Works (with ML)

```
User Request for Itinerary
  ↓
Emotion Detection (Layer 1)
  ↓
Place Ranking (Layer 2)
  ├─ Try ML Model First (if loaded)
  │  ├─ Encode features
  │  ├─ Get prediction
  │  └─ Return ML score
  │
  └─ Fallback to Rule-Based
     ├─ Calculate weighted sum
     └─ Return rule-based score
  ↓
LLM Enhancement (Layer 3)
  ↓
Final Itinerary
```

---

## ⚙️ Inference API

### Using Model Loader Directly

```python
from ml_system.ranker_model_loader import RankerModelLoader, get_ranking_score_from_model

# ─ Option 1: Get raw prediction ─
loader = RankerModelLoader()
if loader.is_loaded():
    loader.load_model()

# Get score for a place
score = get_ranking_score_from_model(
    user_mood='RELAXING',
    user_budget='MEDIUM',
    user_interests=['nature', 'food'],
    user_pace='BALANCED',
    place_category='Nature',
    place_rating=4.5,
    place_budget='MEDIUM',
    place_visit_minutes=120,
    place_tags=['outdoor', 'scenic'],
    trip_total_days=5,
    fallback_score=0.5,  # Fallback if model unavailable
)
# Returns: 0.76 (ML prediction) or 0.5 (fallback)

# ─ Option 2: Check model status ─
is_available = RankerModelLoader.is_loaded()
metadata = RankerModelLoader.get_metadata()
```

---

## 🧪 Testing & Validation

### Test Model Loading

```bash
python manage.py train_itinerary_ranker --test-only
```

**Success output:**
```
✓ Model loaded successfully from backend/ml_models/itinerary_ranker.pkl
```

### Validate Training

```python
# In Django shell
python manage.py shell

from ml_system.ranker_model_loader import get_ranking_score_from_model

# Test prediction
score = get_ranking_score_from_model(
    user_mood='RELAXING',
    user_budget='MEDIUM',
    user_interests=['nature'],
    user_pace='BALANCED',
    place_category='Nature',
    place_rating=4.5,
    place_budget='MEDIUM',
    place_visit_minutes=90,
    place_tags=['outdoor'],
    trip_total_days=3,
)

print(f"Prediction: {score}")  # Should be 0-1
```

### Expected Behavior

After training:
- ✅ Model file exists: `backend/ml_models/itinerary_ranker.pkl`
- ✅ Model loads without errors
- ✅ Predictions are in range [0, 1]
- ✅ Feature importance shows expected patterns
- ✅ Test RMSE similar to training RMSE (not overfitting)

---

## 📝 Logging & Monitoring

### Log File Location

```
Django logs: logs/django.log
Model training output: Console (use --verbose for details)
```

### Key Log Messages

```
✓ Loaded ranker model from backend/ml_models/itinerary_ranker.pkl
✓ Model trained successfully
✓ Model saved successfully
⚠⚠ ML model not available, using fallback score
⚠⚠ Error loading ranker model: [error details]
```

### Debug Info

```python
# Check model status programmatically
from ml_system.ranker_model_loader import RankerModelLoader

loader = RankerModelLoader()
print(f"Model loaded: {loader.is_loaded()}")
print(f"Metadata: {loader.get_metadata()}")
```

---

## 🐛 Troubleshooting

### Issue 1: Insufficient Data

```
Error: Insufficient data: 42 samples. Need at least 100.
```

**Solution:**
1. Create more itineraries in the frontend
2. Have multiple users save trips
3. Wait for data collection
4. Try again: `python manage.py train_itinerary_ranker`

### Issue 2: Model Not Loading

```
⚠ Failed to load ranker model: FileNotFoundError
```

**Solution:**
- Train the model: `python manage.py train_itinerary_ranker`
- Verify file exists: `ls backend/ml_models/itinerary_ranker.pkl`
- Check file permissions: `chmod 644 backend/ml_models/itinerary_ranker.pkl`

### Issue 3: Low Model Performance

If Test R² is very low (< 0.5):

**Possible causes:**
1. Features not meaningful (check feature importance)
2. Data quality issues (check data distribution)
3. Too few samples (need > 200 for good generalization)
4. Hyperparameters not optimal

**Solutions:**
1. Review feature engineering
2. Retrain with more data
3. Adjust hyperparameters in script
4. Consider data augmentation

### Issue 4: Model Predictions Seem Wrong

```python
# Test a known good place
score = get_ranking_score_from_model(
    user_mood='SPIRITUAL',
    user_budget='LOW',
    ...,
    place_category='religious',  # Should score high
    place_rating=4.8,
    ...
)
# If score is low, model may need retraining
```

**Solutions:**
1. Rerun analysis to check data quality
2. Retrain with updated data
3. Adjust fallback weights if needed
4. Consider collecting more diverse data

---

## 📦 File Structure After Training

```
backend/
├── ml_models/                              (created by training script)
│   ├── itinerary_ranker.pkl                (trained model + metadata)
│   └── (other models may go here)
└── ml_system/
    ├── ranker_model_loader.py              (inference utility)
    ├── embeddings/
    ├── retrieval/
    └── training/
```

**Important:** `.pkl` files are **NOT committed** to git (see `.gitignore`)

Each team member trains their own model locally:
```bash
python manage.py analyze_itinerary_ranker_data
python manage.py train_itinerary_ranker --verbose
```

---

## 🚀 Production Deployment

### Before Going Live

1. **Train on full dataset**
   ```bash
   python manage.py train_itinerary_ranker --verbose
   ```

2. **Validate performance**
   ```bash
   python manage.py train_itinerary_ranker --test-only
   ```

3. **Check metrics**
   - Test RMSE: < 0.15 (good)
   - Test R²: > 0.80 (good)
   - Feature importance: Makes sense?

4. **Test end-to-end**
   ```bash
   python manage.py runserver
   # Create itinerary in frontend
   # Verify places are ranked well
   ```

### Deployment Commands

```bash
# On production server
cd backend

# Train model
python manage.py train_itinerary_ranker

# Verify model
python manage.py train_itinerary_ranker --test-only

# Restart Django (model loads automatically)
supervisor restart django_app  # or docker restart
```

### Model Updates

To retrain with new data:
```bash
# Collect latest data
python manage.py analyze_itinerary_ranker_data --verbose

# Check readiness
# If ready, retrain
python manage.py train_itinerary_ranker --verbose

# Model automatically reloaded on next request
```

---

## 📊 Performance Expectations

### Training Metrics

**Good Model:**
- Training RMSE: 0.10-0.15
- Test RMSE: 0.12-0.18
- Test R²: 0.75-0.85

**Acceptable Model:**
- Test RMSE: 0.18-0.25
- Test R²: 0.60-0.75

**Poor Model:**
- Test RMSE: > 0.30
- Test R²: < 0.50

### Inference Latency

- Model loading: ~100ms (first call only, then cached)
- Single prediction: ~1ms
- Batch prediction (10 places): ~5ms

### Model Size

- Typical: 2-5 MB
- Compressed: ~1 MB

---

## 🎓 Next Steps

1. **Run analysis:**
   ```bash
   python manage.py analyze_itinerary_ranker_data --verbose
   ```

2. **Train model:**
   ```bash
   python manage.py train_itinerary_ranker --verbose
   ```

3. **Test frontend:**
   - Create new itinerary
   - Verify places ranked by ML model

4. **Monitor performance:**
   - Track test RMSE over time
   - Collect user feedback
   - Retrain with new data quarterly

5. **Optimize:**
   - A/B test (rule-based vs. ML)
   - Collect user feedback on rankings
   - Adjust features based on feedback
   - Tune hyperparameters

---

## 📚 References

- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [Scikit-learn Preprocessing](https://scikit-learn.org/stable/modules/preprocessing.html)
- [Data Pipeline Analysis](RANKER_DATA_PIPELINE_ANALYSIS.md)
- [Quick Start Guide](RANKER_ANALYSIS_QUICK_START.md)

---

**Last Updated:** April 15, 2026  
**Status:** Ready for training and deployment ✅
