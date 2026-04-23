# 🔬 AI Itinerary Ranker - Data Pipeline Deep Dive & Analysis

**Date:** April 15, 2026  
**Purpose:** Understanding available data for ML model training  
**Status:** Analysis Only (No Training Yet)

---

## 📊 Executive Summary

### Current State
**Location:** `backend/itineraries/ai_ranker_service.py` (line 1-500)

The AI Itinerary Ranker currently uses **RULE-BASED FALLBACK** scoring. No ML model is trained. The system is ready for ML enhancement.

### What Exists
```
✅ Place database:        ~130 Lahore places with ratings & tags
✅ Itinerary storage:     User itineraries with selected places (days structure)
✅ User preferences:      Mood, budget, interests, pace
✅ Place features:        Rating, category, tags, coordinates, hours
❌ Historical rankings:   Not captured (first opportunity to train)
❌ User feedback:         No place ratings per user yet
```

### Data Pipeline Strategy
```
Real Itineraries (user's saved selections)
           ↓
Extract selected places per user
           ↓
Create training samples (selected vs. not selected)
           ↓
Build feature vectors (user + place + context)
           ↓
Derive target variable (labels)
           ↓
ML Model Training (FUTURE)
```

---

## 🗂️ Available Data Sources

### 1. Place Model (`backend/itineraries/models.py:1-48`)

**Fields available for features:**
```python
class Place(models.Model):
    city = CharField(max_length=120)           # ✅ "Lahore"
    name = CharField(max_length=255)           # ✅ "Badshahi Mosque"
    category = CharField(max_length=80)        # ✅ "Religious", "Food", "Nature"
    tags = JSONField(default=list)             # ✅ ['religious', 'spiritual', 'history']
    
    estimated_visit_minutes = PositiveIntegerField  # ✅ 90, 120, etc.
    budget_level = CharField(choices=Budget)  # ✅ LOW, MEDIUM, LUXURY
    
    latitude = FloatField()                    # ✅ 31.588056
    longitude = FloatField()                   # ✅ 74.309444
    average_rating = FloatField()              # ✅ 4.6 (1-5 scale)
    
    ideal_start_hour = PositiveIntegerField()  # ✅ 9 (opening time)
    ideal_end_hour = PositiveIntegerField()    # ✅ 18 (closing time)
```

**Sample data count:**
- **Total places:** ~130 in Lahore
- **With ratings:** Most (verified from generator.py)
- **Categories:** Religious, History, Food, Culture, Nature, Modern, Shopping
- **Budget levels:** LOW, MEDIUM, LUXURY

---

### 2. Itinerary Model (`backend/itineraries/models.py:50-130`)

**User context:**
```python
class Itinerary(models.Model):
    user = ForeignKey(User)                   # ✅ User ID
    city = CharField()                         # ✅ "Lahore"
    
    start_date = DateField()                   # ✅ "2026-04-15"
    end_date = DateField()                     # ✅ "2026-04-20"
    travelers = PositiveIntegerField()         # ✅ 1, 2, 4, etc.
    
    budget_level = CharField(choices=Budget)   # ✅ LOW, MEDIUM, LUXURY
    interests = JSONField(default=list)        # ✅ ["history", "food", "nature"]
    pace = CharField(choices=Pace)             # ✅ RELAXED, BALANCED, PACKED
    mood = CharField(choices=Mood)             # ✅ RELAXING, HISTORICAL, FOODIE, etc.
    
    days = JSONField(default=list)             # ✅ Structure with selected places
    
    locked_place_ids = JSONField()             # User locked places
    excluded_place_ids = JSONField()           # User excluded places
    
    saved = BooleanField()                     # Saved itineraries only
    created_at = DateTimeField()               # When created
```

**The `days` structure (critical for training data):**
```python
# days = [
#   {
#     "date": "2026-04-15",
#     "title": "Day 1: History Tour",
#     "items": [
#       {
#         "id": 1,
#         "name": "Badshahi Mosque",
#         "category": "Religious",
#         "rating": 4.8,
#         ...
#       },
#       {
#         "id": 5,
#         "name": "Shalimar Gardens",
#         ...
#       }
#     ]
#   },
#   {
#     "date": "2026-04-16",
#     ...
#   }
# ]
```

**This is our TRAINING DATA SOURCE!**

---

## 🎯 Training Data Extraction Strategy

### How We Extract Samples

**For each itinerary:**

```
Step 1: Parse days structure
  └─ Extract place IDs selected for each day

Step 2: Create binary classification samples
  For each PLACE in database:
    ✅ If place in itinerary → Positive sample (label=1)
    ❌ If place NOT in itinerary → Negative sample (label=0)

Step 3: Build feature vector
  Features = {
    user_mood, user_budget, user_interests,
    place_rating, place_category, place_tags,
    place_visit_time, trip_day_index, distance
  }

Step 4: Derive target
  y = place.average_rating (0-5 scale)
  or
  y = binary (was_selected: True/False)
```

### Example

**Itinerary:**
- User: ID=42, Mood=SPIRITUAL, Budget=MEDIUM, Interests=["religious", "history"]
- Selected places: [Badshahi Mosque(id=1), Data Darbar(id=7), Shalimar Gardens(id=5)]
- Other places: [Lahore Zoo(id=10), Food Street(id=26), Democracy Monument(id=99), ...]

**Generated training samples:**
```
Sample 1: Badshahi Mosque
  - Features: [mood=SPIRITUAL, budget=1, interests_match=2, rating=4.8, category=Religious, ...]
  - Label: 1 (was selected) ✅
  - Quality: 0.96 (from rating 4.8/5)

Sample 2: Data Darbar
  - Features: [mood=SPIRITUAL, budget=1, interests_match=2, rating=4.5, category=Religious, ...]
  - Label: 1 (was selected) ✅
  - Quality: 0.90

Sample 3: Lahore Zoo
  - Features: [mood=SPIRITUAL, budget=1, interests_match=0, rating=4.1, category=Nature, ...]
  - Label: 0 (NOT selected) ❌
  - Quality: 0.82

Sample 4: Food Street
  - Features: [mood=SPIRITUAL, budget=1, interests_match=0, rating=4.4, category=Food, ...]
  - Label: 0 (NOT selected) ❌
  - Quality: 0.88
```

---

## 🔧 Feature Engineering Plan

### From RankerFeatures Dataclass (`ai_ranker_service.py:26-54`)

The system already defines required features:

#### User Features
```
mood_id:         0-8 (9 moods) ← from Itinerary.mood
budget_level:    0-3 (LOW=0, MEDIUM=1, LUXURY=2) ← from Itinerary.budget_level
interest_tags:   one-hot encoding ← from Itinerary.interests
```

#### Place Features
```
category_id:     0-N (category mapping) ← from Place.category
place_tags:      one-hot [outdoor, cultural, food] ← from Place.tags
rating:          1-5 float ← from Place.average_rating
popularity:      0-100 (DERIVED from selection frequency)
price_level:     1-4 ← from Place.budget_level mapped
distance_km:     float ← calculated from coordinates
```

#### Contextual Features
```
day_index:       0-N (which day of trip) ← derived from Itinerary dates
time_of_day:     0-2 (morning/afternoon/evening) ← from Place.ideal_start_hour
hours_available: float (remaining time that day) ← hardcoded 8.0 for now
prev_visited:    int (recency of past visits) ← from locked/excluded places
is_outdoor:      bool ← from Place.tags contains 'outdoor' or similar
is_cultural:     bool ← from Place.tags contains 'cultural' or 'history'
opening_match:   0-1 (time of day fits opening hours) ← calculated
```

#### Target Variable (Training Label)
```
Option 1: Binary Classification
  y = 1 if place in itinerary
  y = 0 if not in itinerary

Option 2: Regression (Preferred)
  y = place.average_rating (0-5)
  Reason: Captures quality gradient. High-rated places more likely selected.

Option 3: Weighted Labels
  y = (1 + place.average_rating) / 2
  Reason: Blend binary signal with continuous quality score
```

---

## 🗄️ Current Data Inventory

### Database Statistics (From Place Model)

Generated from `generator.py` (DEFAULT_LAHORE_PLACES):

```
Total Places: 130 (approximately)

Categories breakdown:
  • Religious: 20+ places (Badshahi Mosque, Data Darbar, temples, etc.)
  • History: 30+ places (Lahore Fort, Minar-e-Pakistan, tombs, gates)
  • Food: 40+ places (restaurants, food streets)
  • Nature: 20+ places (gardens, parks, zoo, lakes)
  • Shopping: 15+ places (markets, malls)
  • Modern: 5+ places (stadiums, golf clubs)

Budget levels:
  • LOW: 80+ places (heritage sites, parks)
  • MEDIUM: 35+ places (restaurants, upscale shopping)
  • LUXURY: 15+ places (fine dining, golf clubs)

Rating Distribution:
  • Min: 3.9 (Brandreth Road Market)
  • Max: 4.8 (Badshahi Mosque)
  • Mean: ~4.3
  • Most places: 4.0-4.7 range

Tags (examples):
  • ['religious', 'spiritual', 'history', 'historical', 'culture']
  • ['food', 'foodie', 'modern', 'romantic']
  • ['nature', 'relaxing', 'family', 'fun']
  • ['shopping', 'culture', 'food', 'entertainment']
```

### Training Itineraries (Estimated)

```
IF system has been used in real world:
  • Each user creates 1-5 itineraries
  • Each itinerary: 3-7 days, selecting 3-10 places per day
  • Total places per itinerary: 15-70 selected places

SAMPLES GENERATED PER ITINERARY:
  = (Number of places in database) × (1 itinerary)
  = 130 samples per itinerary
  
  Of which:
  ✅ Positive: 15-70 (depending on trip length)
  ❌ Negative: 60-115

IF we have 10 itineraries:
  = 1,300 total samples
  = 250-350 positive samples (selected places)
  = 950-1,050 negative samples (not selected)
```

---

## 📋 Data Quality Assessment Framework

### Checklist for Running Analysis

```bash
# Run the complete analysis (does NOT train/save)
python manage.py analyze_itinerary_ranker_data --verbose

# Run for sample of itineraries
python manage.py analyze_itinerary_ranker_data --sample 50

# Run for specific city
python manage.py analyze_itinerary_ranker_data --city Lahore
```

### What the Analysis Reports

1. **Data Overview**
   - Total itineraries available
   - Total users for diversity check
   - Total training samples generated
   - Positive vs negative class split
   - Class balance ratio

2. **Place Statistics**
   - Categories coverage
   - Budget level distribution
   - Average place rating
   - Places with missing ratings

3. **Feature Analysis**
   - Mood distribution (are all 9 moods represented?)
   - Budget distribution
   - Category coverage
   - Interest tags used
   - Rating distribution (min, max, mean, median)
   - Visit time distribution

4. **Data Quality Issues**
   - Empty itineraries (no days data)
   - Itineraries with no valid places
   - Missing ratings
   - Missing user interests
   - Missing moods

5. **Place Popularity**
   - Most selected places (top 10)
   - Least selected places
   - Never selected places
   - This reveals **selection bias** in training

6. **Training Readiness**
   - ✅ READY: > 100 samples, > 10 positive, reasonable class balance
   - ⚠️ INSUFFICIENT: < 100 samples
   - ⚠️ IMBALANCED: < 10 positive or > 90% negative

---

## ⚠️ Known Limitations & Gaps

### 1. Missing Data

**`popularity_score` field:**
- Used in `ai_ranker_service.py` line 173
- Not in Place model
- **Solution:** Derive from selection frequency in training data

**Hotel location:**
- Used for distance calculation (line 221)
- Not in Place model
- **Solution:** Use city center coordinates as reference

**Place opening hours:**
- Only `ideal_start_hour` and `ideal_end_hour` available
- More granular schedule missing
- **Solution:** Use available hours, acknowledge limitation

### 2. Insufficient Temporal Data

**Current:**
- `day_index` simplified to 1
- No time-of-day context in itinerary generation

**Better approach:**
- Track actual time spent on each place
- Model time-of-day preferences (morning vs evening activities)
- Requires enhanced itinerary structure

### 3. No User Feedback Loop

**What we don't have:**
- Did user like selected places?
- Did they visit? When?
- Ratings given by user for selected places

**What we have:**
- Implicit signal: Places were selected
- Proxy quality: Place's average rating

**Improvement:** Future - capture user satisfaction feedback

### 4. Selection Bias

**Problem:** 
- Popular places selected more often
- Less exploration of low-rated places
- Model may overfit to popular selections

**Solution:**
- Train on balanced dataset
- Use weighted sampling in training
- Add regularization to prevent popularity overfitting

---

## 🎓 How ai_ranker_service.py Uses Features

### Line-by-Line Analysis

**Lines 26-54: RankingFeatures dataclass**
- Defines complete feature set
- Includes conversion to numpy array (line 51-59)
- This is what we need to match in training data

**Lines 120-160: rank_places() method**
- **Input:** User mood, candidate places, user interests, budget, context
- **Output:** List of RankedPlace sorted by score
- **Key call:** `_build_features()` at line 141

**Lines 162-218: _build_features() method**
- Encodes categorical features (mood, budget, category)
- Calculates distance using haversine formula (line 200)
- Builds feature vector
- **This is where training data goes!**

**Lines 220-239: _get_ml_score() (line loads model)**
- Would call `model.predict(feature_array)`
- Returns (score, confidence)
- **This is where trained model gets invoked**

**Lines 241-259: _get_fallback_score() (current rule-based)**
- Hardcoded weights:
  - Rating: 30%
  - Popularity: 20%
  - Interest match: 25%
  - Cultural bonus: 8%
  - Outdoor bonus: 7%
  - Hours match: 10%
  - Distance penalty: -10%
- **This is what ML model should learn to optimize**

---

## 🚀 Next Steps

### Phase 0: Data Analysis (CURRENT - Do NOW)

```bash
# Step 1: Understand available data
python manage.py analyze_itinerary_ranker_data --verbose

# Output: Detailed JSON report showing:
#  - How many samples we have
#  - Class balance
#  - Feature coverage
#  - Data quality issues
```

### Phase 1: Synthetic Data Generation (IF NEEDED)

If real data insufficient (< 100 samples):

```python
# Generate synthetic itineraries for training
# Use templates based on moods/interests
# Ensures coverage of all feature combinations
```

### Phase 2: Feature Matrix Building (NEXT)

```python
# Transform raw samples to ML-ready feature matrix
# - Standardize feature values
# - Handle missing data
# - Create train/test split
```

### Phase 3: Model Training (NOT YET)

```python
# Train LightGBM model
# Using features from Phase 2
# Validate on holdout test set
```

### Phase 4: Model Deployment (LATER)

```python
# Load model in ai_ranker_service
# Replace rule-based fallback with ML score
# Monitor performance
```

---

## 📖 Key Code References

### Critical Files to Review

1. **`backend/itineraries/ai_ranker_service.py`**
   - Lines 26-54: Feature definition
   - Lines 120-160: Feature building
   - Lines 241-259: Fallback scoring (what ML should learn)

2. **`backend/itineraries/models.py`**
   - Lines 1-48: Place model (data source)
   - Lines 50-130: Itinerary model (user context)

3. **`backend/itineraries/generator.py`**
   - DEFAULT_LAHORE_PLACES: Sample data with ratings
   - Lines 26-142: Place data with all features

### Management Command

**`backend/itineraries/management/commands/analyze_itinerary_ranker_data.py`**
- Extracts training samples
- Analyzes feature distributions
- Reports data quality
- Generates actionable recommendations

---

## 🎯 Success Criteria

For model training to proceed, we need:

```
✅ Minimum 100 training samples
✅ At least 20 positive samples (places selected in itineraries)
✅ Reasonable class balance (not >95% negative)
✅ Coverage of all moods (at least 3-5 different user moods)
✅ Coverage of main place categories
✅ Rating distribution across range (not all 4.5+)
✅ Data quality issues < 5% of samples
```

---

## 📝 Summary

**What We Have:**
- ✅ ~130 places with ratings and detailed features
- ✅ User itineraries with mood, budget, interests
- ✅ Selected places per itinerary (our training signal)
- ✅ Feature extraction code ready

**What We Generate:**
- `DataSample` objects with all features
- Training data in numpy-ready format
- Quality metrics and recommendations

**What We DON'T Do Yet:**
- ❌ Train the model (next phase)
- ❌ Save trained weights (next phase)
- ❌ Deploy to production (next phase)

**Next Action:**
Run: `python manage.py analyze_itinerary_ranker_data --verbose`
This shows exactly what training data we have available.

---

**Document prepared for:** Travello Engineering Team  
**Status:** Ready for Data Analysis  
**Last Updated:** April 15, 2026
