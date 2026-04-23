# ML Ranker Quick Start Guide

## Overview
The LightGBM-based itinerary place ranking model is integrated into the AI service and automatically used during itinerary generation.

---

## Usage in Code

### Automatic (Default)
The model is **automatically loaded** when the AI service initializes:

```python
# In views.py or services
from itineraries.ai_service import IterationGeneratorService

service = IterationGeneratorService()  # Model loads automatically
```

### Explicit Ranking
```python
from itineraries.ai_ranker_service import LearningToRankService

ranker = LearningToRankService()

# Rank places for a specific user/day
scores = ranker.rank_places(
    user_mood='HISTORICAL',
    candidate_places=places_queryset,
    user_interests=['history', 'culture'],
    user_budget='MEDIUM',  # LOW, MEDIUM, LUXURY
    user_pace='BALANCED',   # RELAXED, BALANCED, PACKED
    day_index=0,
    trip_total_days=3,
    hotel_location=(31.5, 74.3),  # (lat, lng)
    previously_visited=[]
)
# Returns: List of (place, score) tuples sorted by score DESC
```

---

## Model Details

### What It Does
Predicts ranking scores (0-1) for places based on:
- User preferences (mood, budget, pace, interests)
- Place characteristics (category, rating, duration)
- Trip context (day number, total days, location)
- Geographic proximity to hotel

**Higher score = Better match for user**

### Training Data
- **Samples**: 9,860 itineraries
- **Features**: 17 engineered features
- **Selected Places**: 310 (3.1%)
- **Not Selected**: 9,550 (96.9%)

### Model Performance
```
Training RMSE:  0.1047
Test RMSE:      0.1175
Training R²:    0.277 (28% variance explained)
Test R²:        0.143 (14% variance explained)
```

---

## Retraining

### When to Retrain
- Monthly (accumulate 100+ new itineraries)
- After significant user behavior changes
- When model performance drops in production

### How to Retrain

**Option 1: Management Command**
```bash
cd backend
python manage.py train_itinerary_ranker_v2 --city Lahore --verbose
```

**Option 2: Standalone Script**
```bash
cd backend
python retrain_ranker.py
```

**Output**:
- New model file: `ml_models/itinerary_ranker.pkl`
- Automatically used by next service instantiation

---

## Debugging

### Check Model Status
```python
from itineraries.ai_ranker_service import LearningToRankService

ranker = LearningToRankService()
print(f"Model loaded: {ranker.model is not None}")
print(f"Scaler ready: {ranker.scaler is not None}")

# Test with one place
score = ranker.get_ml_score(place_id, user_mood, day_index)
print(f"Score: {score:.3f}")
```

### Common Issues

**Issue: Model not loading**
```
Solution: Check if backend/ml_models/itinerary_ranker.pkl exists
If missing, run: python retrain_ranker.py
```

**Issue: All scores the same**
```
Solution: 
1. Check if feature extraction is working
2. Verify feature order matches training (17 features in exact order)
3. Retrain with recent data
```

**Issue: Slow rankings**
```
Solution:
1. Batch rank multiple places instead of one-by-one
2. Use fallback scoring for large lists (>100 places)
3. Check database query performance
```

---

## Feature Reference

The model uses these 17 features (in exact order):

| Index | Feature | Min-Max | Purpose |
|-------|---------|---------|---------|
| 0 | user_mood | 0-8 | Type (RELAXING, SPIRITUAL, etc) |
| 1 | user_budget | 0-2 | Budget level |
| 2 | user_pace | 0-2 | Trip pace preference |
| 3 | user_interests_count | 0+ | How many interests user has |
| 4 | place_category | 0-15 | Type of place |
| 5 | place_rating | 0-1 | Quality (5-star normalized) |
| 6 | place_budget | 0-2 | Cost level |
| 7 | place_visit_minutes | 0-1 | Time needed (normalized) |
| 8 | place_tags_count | 0+ | Number of tags |
| 9 | place_ideal_start | 0-23 | Best start hour |
| 10 | place_ideal_end | 0-23 | Best end hour |
| 11 | trip_day | 0-1 | Which day (normalized) |
| 12 | trip_days_total | 0-1 | Total trip length (normalized) |
| 13 | distance_km | 0-1 | Distance from hotel (normalized) |
| 14 | interests_match | 0-1 | User matches place tags |
| 15 | budget_match | 0-1 | User budget matches place cost |
| 16 | cultural_match | 0-1 | Cultural alignment |

⚠️ **Critical**: Feature order MUST match exactly during inference!

---

## API Integration

### REST Endpoint
If ranking is exposed via API:

```python
# urls.py
path('rank-places/', views.rank_places_view, name='rank-places')

# views.py
def rank_places_view(request):
    user_mood = request.data.get('mood')
    places = Place.objects.filter(city=request.data.get('city'))
    day = request.data.get('day', 0)
    
    ranker = LearningToRankService()
    ranked = ranker.rank_places(
        user_mood=user_mood,
        candidate_places=places,
        day_index=day,
        trip_total_days=request.data.get('total_days', 3),
        hotel_location=(request.data['lat'], request.data['lng']),
        # ...
    )
    
    return Response([
        {'place_id': p.id, 'score': float(s)} 
        for p, s in ranked
    ])
```

---

## Fallback Behavior

If model fails to load, the system automatically falls back to rule-based scoring:

```python
score = (
    rating_match * 0.3 +
    category_match * 0.2 +
    budget_match * 0.2 +
    distance_match * 0.2 +
    interests_match * 0.1
)
```

This ensures rankings always work, even if ML model has issues.

---

## Performance Tips

1. **Batch Processing**: Group multiple rank_places calls
```python
# GOOD: Batch 20 places at once
ranked = ranker.rank_places(places, ...)

# AVOID: Ranking one place 20 times
for place in places:
    score = ranker.get_ml_score(place.id, ...)
```

2. **Cache Results**: Rankings don't change mid-session
```python
if place_id not in ranking_cache:
    ranking_cache[place_id] = ranker.get_ml_score(place_id, ...)
score = ranking_cache[place_id]
```

3. **Monitor Predictions**: Log scores for analysis
```python
logger.info(f"Ranked {place.name}: {score:.3f}")
```

---

## Troubleshooting Retraining

**Problem**: No samples collected
```
Fix: Ensure itineraries have:
- User preferences set
- Places with ratings and categories
- Selected places in place_itinerary
```

**Problem**: Model training stuck
```
Fix: Check:
1. Data distribution (not all same target value)
2. Feature normalization (scaler working)
3. Sufficient samples (need >1000)
```

**Problem**: Model file too large
```
Fix: Reduce boosting rounds in trainer:
num_boost_round: 100 → 50
```

---

## Key Metrics to Monitor

After deploying, track:

| Metric | Target | Check |
|--------|--------|-------|
| Score Distribution | 0.2-0.8 range | Not all same |
| Selected vs Not | Selected > 0.6 | Learning discrimination |
| Inference Speed | <10ms | Model latency |
| Model Size | <500 KB | Check every month |
| Prediction Diversity | 5+ unique values | Not constant |

---

## Contact & Support

For issues:
1. Check [ML_RANKER_FIX_REPORT.md](ML_RANKER_FIX_REPORT.md) for technical details
2. Review logs in `backend/ml_models/training.log`
3. Run diagnostic: `python diagnose_target.py`
4. Check model file: `backend/ml_models/itinerary_ranker.pkl`

---

**Last Updated**: April 15, 2026  
**Model Version**: 2.0 (Fixed variant)  
**Status**: Production Ready ✅
