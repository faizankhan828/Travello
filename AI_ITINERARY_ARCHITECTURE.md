# AI-Driven Itinerary System Architecture

**Status**: Design & Implementation Plan  
**Date**: April 6, 2026  
**Version**: 1.0  

---

## Executive Summary

This document outlines the upgrade of the current rule-based itinerary system into a **hybrid AI-driven recommendation system** with three integrated layers, while maintaining 100% backward compatibility with existing APIs.

### Key Design Principles
- ✅ **No Frontend Changes**: All UI/UX behavior identical
- ✅ **API Contract Preserved**: Existing endpoints work unchanged
- ✅ **Graceful Degradation**: Falls back to rule-based system if AI fails
- ✅ **Lazy Loading**: Models loaded on-demand
- ✅ **Monitoring**: All predictions logged for feedback loop

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Unchanged)                         │
│  User selects mood, interests, budget → ItineraryPlanner.js         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ POST /api/itineraries/generate/
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 0: REQUEST PARSING                          │
│  Existing ItineraryGenerateView (unchanged API contract)             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│         LAYER 1: AI MOOD DETECTION (Transformer-based)              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Input: user_text (if available), manual_mood_selection      │   │
│  │ Model: distilroberta-base-emotion (fine-tuned on travel)    │   │
│  │ Output: detected_emotion + confidence                       │   │
│  │ Logic: final_mood = blend(manual_mood, detected_emotion)    │   │
│  │ Fallback: Use manual mood if confidence < threshold         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ Enriched mood signal
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│     LAYER 2: LEARNING-TO-RANK MODEL (LightGBM/XGBoost)             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Input Features:                                             │   │
│  │  - User: mood, interests, budget, trip_duration            │   │
│  │  - Place: category, tags, rating, price, population        │   │
│  │  - Context: day_index, time_of_day, next_day_distance      │   │
│  │                                                             │   │
│  │ Model: Trained on synthetic + real user feedback           │   │
│  │ Output: Relevance score (0-1) for each place               │   │
│  │ Ranking: Sort places by score + diversity penalty          │   │
│  │ Fallback: Use rule-based scoring if confidence < threshold │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ Ranked places
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│      LAYER 3: LLM-BASED DESCRIPTION (Optional Enhancement)          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Input: Ranked places, user_context                          │   │
│  │ Model: Local LLM or GPT-style (streaming or batch)          │   │
│  │ Output: Enhanced descriptions, activity suggestions         │   │
│  │ Scope: Text generation ONLY, not ranking                    │   │
│  │ Fallback: Use template-based descriptions                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ Itinerary JSON
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  RESPONSE FORMATTING (Unchanged)                     │
│  Return same JSON schema as before for frontend compatibility       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: AI Mood Detection

### Purpose
Replace/enhance manual mood selection with automatic emotion inference from user context.

### Implementation

**Model Selection**:
- **Primary**: `j-hartmann/emotion-english-distilroberta-base` (existing in codebase)
- **Alternative**: `cardiffnlp/twitter-roberta-base-emotion`
- **Fine-tuning**: On travel/tourism domain dataset

**Data Flow**:
```
User input (preferences text, mood_override) → Tokenize → Model → Emotion logits
→ Apply softmax → Get top emotion + confidence → Map to internal mood tags
→ Blend with manual selection
```

**Mood Blending Strategy**:
```python
final_mood = (
    0.6 * manual_mood +  # User's explicit choice (priority)
    0.4 * detected_mood   # AI-detected emotion
)
# OR if no manual mood: use detected_mood entirely
# OR if confidence(<0.6): use manual_mood only
```

**Supported Emotions → Internal Mood Mapping**:
```
HuggingFace Emotion → Travello Mood
- joy, excitement → FUN
- sadness, calmness → RELAXING
- anger, neutral → HISTORICAL (or neutral mapping)
- fear, surprise → ADVENTURE
- custom → best_match_heuristic
```

**Service Class**:
```python
class AIEmotionDetectionService:
    def detect_emotion_from_user_context(self, user_text, user_preferences)
    def blend_emotions(self, manual_mood, detected_emotion, confidence)
    def emotion_to_mood_tag(self, emotion_label)
```

---

## Layer 2: Learning-to-Rank Model

### Purpose
Replace rule-based place scoring with ML-trained ranking model.

### Model Selection

**Model Type**: **LightGBM** (Gradient Boosted Trees)
- **Rationale**:
  - Fast inference (<5ms per prediction)
  - Handles structured features well
  - Interpretable feature importance
  - Lightweight for mobile/edge deployment
  - Better than neural networks for tabular data without huge datasets

**Alternative**: XGBoost or CatBoost if needed

### Feature Engineering

**User Features** (cached, computed once):
- `mood_embedding`: Dense vector from emotion model (768-dim)
- `mood_id`: One-hot encoded mood (9 values)
- `interest_embedding`: Weighted sum of interest tags
- `budget_level`: Categorical (0-3)
- `trip_duration`: Integer (days)
- `days_remaining`: Integer (dynamic)

**Place Features** (precomputed from database):
- `category_id`: Categorical (e.g., restaurant, museum, park)
- `tag_embedding`: Weighted sum of place tags (768-dim)
- `rating`: Float (1-5)
- `popularity_score`: Float (0-100, from # reviews)
- `price_level`: Categorical (1-4)
- `distance_from_hotel`: Float (km)
- `is_outdoor`: Binary
- `is_cultural`: Binary (tag-based)
- `opening_hours_score`: Float (0-1, aligned with day_time)

**Contextual Features** (computed per ranking call):
- `day_index`: Integer (1-N days)
- `time_of_day`: Categorical (morning, afternoon, evening)
- `distance_to_next_day_hotel`: Float (km)
- `hours_available`: Float (remaining day hours)
- `day_number_in_trip`: Integer
- `previously_visited_days`: Integer (diversity penalty)
- `weather_condition`: Categorical (if available)

### Training Data Strategy

**Phase 1: Synthetic Labels** (Immediate)
```
- Generate N=10,000 synthetic user sessions
- For each session:
  - User: random mood, interests, budget
  - Generate candidates using current rule-based system
  - Score using existing MOOD_TAG_MAP heuristic
  - Treat heuristic scores as weak labels (0-1 normalized)
- Train LightGBM with synthetic data
- Expected Accuracy: 85-90% alignment with rule-based baseline
```

**Phase 2: Real User Feedback** (Post-deployment)
```
- Log all itinerary generations
- Track user interactions:
  - Which places user visits (implicit label: +1)
  - Which places user ignores (implicit label: -1)
  - User ratings/comments on itinerary
  - Booking data (strong signal)
- Periodically retrain with real labels
- Expected improvement: +5-15% ranking accuracy
```

### Model Training

**Training Pipeline**:
```python
1. Load synthetic + real training data
2. Feature engineering for all samples
3. Train-test split (80/20, stratified by mood)
4. LightGBM hyperparameters:
   - num_leaves: 31
   - learning_rate: 0.05
   - num_boost_round: 100
   - early_stopping_rounds: 10
5. Evaluate with:
   - NDCG@5, NDCG@10 (ranking quality)
   - Precision@K (relevance)
   - Kendall's Tau (correlation with rule-based baseline)
6. Save model with version + metadata
7. Periodic retraining (weekly/monthly)
```

### Inference

**During Itinerary Generation**:
```
1. Get user profile → compute user features
2. Get candidate places for day → compute place features
3. For each place:
   - Concatenate [user_features, place_features, context_features]
   - Pass to LightGBM model
   - Get relevance score (0-1)
4. Sort candidates by score (descending)
5. Apply diversity penalty (reduce score if place already used in earlier days)
6. Keep top K places per day (e.g., K=5 for display)
```

**Inference Time Budget**: <50ms for 30 places

**Caching Strategy**:
```
- Cache user embedding (valid for 24h)
- Cache place features (precomputed)
- Cache model predictions for identical requests (5min)
```

### Fallback to Rule-Based

If any condition fails:
```python
confidence = model.predict_proba(features)
if confidence.max() < CONFIDENCE_THRESHOLD (0.6):
    # Use hybrid scoring
    ml_score = model.predict(features)
    rule_score = rule_based_scoring_function(user, place)
    final_score = 0.7 * ml_score + 0.3 * rule_score
else:
    final_score = ml_score
```

---

## Layer 3: LLM-Based Description Enhancement

### Purpose
Enhance itinerary descriptions and provide better explanations (optional, non-critical).

### Model Selection

**Options**:
1. **Local LLM**: Ollama + Mistral-7B (offline, privacy-preserving)
2. **Cloud LLM**: GPT-3.5-turbo API (better quality, latency risk)
3. **Lightweight**: DistilBERT-based seq2seq (summarization only)

**Recommended**: Start with local Mistral-7B for privacy + cost.

### Scope

**DO USE LLM FOR**:
- Generating engaging descriptions for recommended places
- Suggesting activity sequences ("After museum, visit nearby café...")
- Creating personalized welcome messages
- Providing tips based on mood + interests

**DO NOT USE LLM FOR**:
- Ranking places (use ML model instead)
- Core itinerary logic
- Place filtering

### Implementation

```python
class LLMItineraryEnhancementService:
    def generate_place_description(self, place_name, place_data, user_mood)
    def generate_day_activity_flow(self, day_places, user_mood)
    def generate_welcome_message(self, itinerary, user_mood)
    
    # Fallback to templates if LLM unavailable
    def get_template_description(self, place_data)
```

### Fallback
```python
try:
    description = llm_service.generate_description(place, mood)
except LLMTimeout:
    description = template_service.get_description(place)
```

---

## Service Layer Integration

### New Service Class: `AIItineraryService`

**Location**: `backend/itineraries/ai_service.py`

```python
class AIItineraryService:
    """Unified AI-powered itinerary generation service"""
    
    def __init__(self):
        self.emotion_detector = AIEmotionDetectionService()
        self.ranker = LearningToRankService()
        self.llm_enhancer = LLMEnhancementService()
        self.logger = AILogger()
    
    def generate_itinerary_ai(self, user, trip_params):
        """Main AI pipeline - called from existing view"""
        try:
            # Layer 1: Mood Detection
            final_mood = self.emotion_detector.get_final_mood(
                manual_mood=trip_params.get('mood'),
                user_text=trip_params.get('preferences_text', '')
            )
            
            # Layer 2: ML Ranking
            places_per_day = []
            for day_idx in range(trip_params['num_days']):
                candidates = self.get_candidates_for_day(day_idx, user, trip_params)
                ranked_places = self.ranker.rank_places(
                    user=user,
                    mood=final_mood,
                    candidates=candidates,
                    day_idx=day_idx
                )
                places_per_day.append(ranked_places)
            
            # Layer 3: LLM Enhancement (optional)
            itinerary = self._build_itinerary_structure(places_per_day)
            enhanced_itinerary = self.llm_enhancer.enhance_descriptions(
                itinerary=itinerary,
                user_mood=final_mood
            )
            
            # Log for monitoring
            self.logger.log_generation(
                user_id=user.id,
                mood=final_mood,
                places=places_per_day,
                model_confidence=self.ranker.last_confidence
            )
            
            return enhanced_itinerary
            
        except Exception as e:
            # FALLBACK: Use rule-based system
            logger.error(f"AI generation failed: {e}, falling back to rule-based")
            return self.fallback_to_rule_based(user, trip_params)
    
    def fallback_to_rule_based(self, user, trip_params):
        """Use existing generator.py logic"""
        from .generator import generate_itinerary as rule_based_generate
        return rule_based_generate(
            user=user,
            num_days=trip_params['num_days'],
            mood=trip_params.get('mood', 'RELAXING'),
            interests=trip_params.get('interests', []),
            budget=trip_params.get('budget'),
            trip_start_date=trip_params['trip_start_date']
        )
```

### Integration with Existing View

**File**: `backend/itineraries/views.py`

```python
# Keep existing function signature UNCHANGED
class ItineraryGenerateView(APIView):
    def post(self, request):
        serializer = ItineraryGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        # NEW: Use AI service if enabled, else use rule-based
        if settings.USE_AI_ITINERARY_PLANNER:
            ai_service = AIItineraryService()
            itinerary = ai_service.generate_itinerary_ai(
                user=request.user,
                trip_params=serializer.validated_data
            )
        else:
            # Fall back to existing logic
            from .generator import generate_itinerary
            itinerary = generate_itinerary(...)
        
        # Return identical response format
        return Response(itinerary, status=201)
```

---

## Data Management & Training

### Database Schema Extensions

**New Tables** (minimal changes):

```sql
-- Log all AI predictions for monitoring
CREATE TABLE ai_itinerary_predictions (
    id UUID PRIMARY KEY,
    user_id INTEGER FOREIGN KEY,
    generated_at TIMESTAMP,
    mood_detected TEXT,
    mood_final TEXT,
    model_version TEXT,
    confidence FLOAT,
    places JSON,
    feedback_score FLOAT NULL,  -- +1 if user booked, 0 if ignored, -1 if skipped
    feedback_date TIMESTAMP NULL,
    created_at TIMESTAMP
);

-- Store model versions & metadata
CREATE TABLE model_versions (
    version_id TEXT PRIMARY KEY,
    model_type TEXT,  -- 'emotion', 'ranker', 'enhancer'
    created_date TIMESTAMP,
    training_samples INT,
    validation_accuracy FLOAT,
    status TEXT,  -- 'active', 'deprecated'
    metadata JSON
);
```

### Training & Deployment Flow

```
1. OFFLINE TRAINING (Weekly)
   ├─ Collect synthetic data (samples from rule-based system)
   ├─ Collect real feedback (user interactions, bookings)
   ├─ Feature engineering + preprocessing
   ├─ Train LightGBM model
   ├─ Evaluate (NDCG@5, Precision)
   ├─ If better than current: save new model version
   └─ Store metrics in model_versions table

2. MODEL RELEASE
   ├─ Tag new version: v1.2.3
   ├─ Store in S3/artifact storage
   ├─ Update model_version reference
   └─ Log in deployment pipeline

3. FALLBACK MECHANISM
   ├─ If inference fails: use rule-based
   ├─ If confidence < threshold: hybrid scoring
   ├─ Log all failures for debugging
   └─ Alert if failure rate > 5%
```

---

## API Compatibility & Backward Compatibility

### No Changes to Request/Response Schema

```python
# BEFORE (existing)
POST /api/itineraries/generate/
{
    "mood": "RELAXING",
    "interests": ["Nature", "Photography"],
    "budget": "medium",
    "num_days": 3,
    "trip_start_date": "2026-04-20"
}

Response:
{
    "id": "uuid",
    "days": [
        {
            "date": "2026-04-20",
            "places": [...]
        }
    ]
}

# AFTER (AI-enhanced, same schema!)
Same request format
Same response format
(Just internally better ranking + mood detection)
```

### Feature Flags

```python
# settings.py
USE_AI_ITINERARY_PLANNER = True
USE_EMOTION_DETECTION = True
USE_ML_RANKING = True
USE_LLM_ENHANCEMENT = False  # Optional, disable if resource-constrained

AI_CONFIDENCE_THRESHOLD = 0.6
ML_RANKING_ENABLED_FOR_MOOD = ['RELAXING', 'FUN']  # Gradual rollout

FALLBACK_TO_RULE_BASED = True  # Always enable fallback
```

---

## Performance & Scalability

### Inference Time Budget

```
Layer 1 (Mood Detection): 20ms
  - Tokenization: 2ms
  - Model inference: 15ms
  - Blending: 3ms

Layer 2 (ML Ranking): 30ms
  - Feature preprocessing: 10ms
  - Model inference (30 places): 15ms
  - Sorting + diversity: 5ms

Layer 3 (LLM Enhancement): 500ms-2s (async, non-blocking)
  - Could be deferred to background task

TOTAL (Layer 1+2): ~50ms
TOTAL (with Layer 3 async): ~50ms immediate + deferred descriptions
```

### Caching Strategy

```python
class AIModelCache:
    - User embeddings (24h TTL)
    - Place features (7d TTL, invalidate on update)
    - Model predictions (5m TTL, keyed by user+mood+places)
    - Models themselves (lazy-loaded, kept in memory)
```

### Resource Requirements

```
Memory:
- Emotion model: ~500MB
- LightGBM ranker: ~50MB
- LLM (if Mistral-7B): ~15GB (or remote API)
- Cache: ~500MB
Total: ~16GB (or ~600MB without LLM)

CPU:
- Inference: ~1-2 CPU cores sufficient
- Training (offline): 4-8 cores, weekend runs

Storage:
- Model versions: ~100MB per version
- Training data: ~1GB
- Predictions log: ~100MB/month
```

---

## Monitoring & Evaluation

### Key Metrics

```python
# Ranking Quality
- NDCG@5: Compare ML ranking vs rule-based (target: >0.85)
- Precision@K: Relevance of top K recommendations
- Kendall's Tau: Correlation with baseline (maintain >0.8)

# User Satisfaction (Proxy)
- Click-through rate (CTR) on recommended places
- Save rate (bookmarked itineraries)
- Booking conversion rate (places booked / recommended)
- Itinerary regeneration rate (low = good)
- User rating of AI itinerary (1-5 stars)

# System Health
- Model inference latency (p95, p99)
- Fallback rate (target: <5%)
- Model prediction confidence (distribution)
- Feature compute time
- Cache hit rate
```

### Logging & Monitoring

```python
class AILogger:
    def log_generation(self, user_id, mood, places, confidence):
        """Log complete generation for analysis"""
        
    def log_user_feedback(self, generation_id, feedback):
        """Track user interactions with recommendations"""
        
    def log_fallback(self, generation_id, reason):
        """Alert on fallback events"""
        
    def log_model_inference(self, model_type, latency, confidence):
        """Track model performance metrics"""
```

---

## Implementation Roadmap

### Phase 1 (Weeks 1-2): Foundation
- [ ] Design & approve architecture
- [ ] Implement `AIEmotionDetectionService` wrapper for existing model
- [ ] Create `AIItineraryService` base class with fallback logic
- [ ] Integrate with existing view (non-breaking)
- [ ] Write unit tests

### Phase 2 (Weeks 3-5): ML Ranking
- [ ] Feature engineering & preprocessing
- [ ] Generate synthetic training data
- [ ] Train baseline LightGBM model
- [ ] Implement `LearningToRankService`
- [ ] Integrate ranking into pipeline
- [ ] Performance benchmarking

### Phase 3 (Weeks 6-7): LLM Enhancement (Optional)
- [ ] Evaluate LLM options (local vs cloud)
- [ ] Implement `LLMEnhancementService`
- [ ] Add async/background task integration
- [ ] Non-blocking fallback to templates

### Phase 4 (Week 8+): Production & Monitoring
- [ ] Deploy with feature flags (gradual rollout)
- [ ] Monitor metrics & user feedback
- [ ] Retrain with real user data
- [ ] Iterate on model performance

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Model inference latency | Caching + async LLM + feature optimization |
| API contract breakage | Keep function signatures identical, feature flags |
| AI fails → bad UX | Robust fallback to rule-based system |
| Lack of training data | Start with synthetic labels from heuristic |
| Memory OOM | Lazy model loading, optional layer 3 |
| Prediction confidence varies | Hybrid scoring when confidence low |

---

## Success Criteria

- ✅ No API changes (100% backward compatible)
- ✅ No frontend UI changes
- ✅ Inference time <100ms (p95)
- ✅ Fallback success rate >99%
- ✅ NDCG@5 > 0.85 vs rule-based baseline
- ✅ User satisfaction survey: +10% vs rule-based
- ✅ No data loss (predictions logged for feedback)

---

## Conclusion

This architecture provides a **pragmatic upgrade path** from rule-based to AI-driven recommendation system while:
- Preserving all existing APIs & database schema
- Enabling graceful fallback if anything fails
- Using proven ML techniques (LightGBM) for tabular data
- Supporting real user feedback for continuous improvement
- Maintaining performance (<100ms latency)

The hybrid multi-layer approach allows **independent scaling** of each component and **easy debugging** if issues arise.
