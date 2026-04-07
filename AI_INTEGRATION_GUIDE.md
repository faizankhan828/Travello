# AI Itinerary System - Integration Guide

## Overview

This guide explains how to integrate the AI-driven itinerary system into the existing Travello application **without breaking any existing APIs or UI**.

## Quick Start

### 1. Settings Configuration

Add these to `backend/travello_backend/settings.py`:

```python
# ============================================
# AI ITINERARY SYSTEM CONFIGURATION
# ============================================

# Feature flags - independently enable/disable each layer
USE_AI_ITINERARY_PLANNER = True
USE_EMOTION_DETECTION = True
USE_ML_RANKING = True  
USE_LLM_ENHANCEMENT = False  # Optional, costs money if cloud-based

# ML model configuration
AI_ML_RANKER_MODEL_PATH = None  # Set to path when model is trained
AI_CONFIDENCE_THRESHOLD = 0.6  # Fallback to hybrid scoring below this

# LLM configuration (only needed if USE_LLM_ENHANCEMENT=True)
AI_LLM_TYPE = "template"  # Options: "template", "local", "api"
AI_LLM_MODEL_NAME = "mistral"  # For local Ollama
AI_LLM_URL = "http://localhost:11434"  # Ollama endpoint (if local)
AI_LLM_TIMEOUT_SECONDS = 3

# Monitoring
LOG_AI_PREDICTIONS = True
LOG_AI_PREDICTIONS_TO_DB = True
AI_METRICS_LOGGING_LEVEL = "INFO"

# New apps
INSTALLED_APPS = [
    # ... existing apps ...
    'itineraries',  # Ensure this is in INSTALLED_APPS
]
```

### 2. Update `views.py` to Use AI Service

Modify `backend/itineraries/views.py`:

```python
# At the top of the file
from django.conf import settings
from .ai_service import AIItineraryService, AIMetricsCollector
from .ai_emotion_service import AIEmotionDetectionService
from .ai_ranker_service import LearningToRankService
from .ai_llm_service import LLMEnhancementService

# Initialize AI services (singleton pattern)
_ai_service = None

def get_ai_service():
    """Get or create AI service instance"""
    global _ai_service
    if _ai_service is None:
        try:
            emotion_service = AIEmotionDetectionService()
            ranker_service = LearningToRankService(
                model_path=settings.AI_ML_RANKER_MODEL_PATH
            )
            llm_service = LLMEnhancementService(
                model_type=settings.AI_LLM_TYPE,
                model_name=settings.AI_LLM_MODEL_NAME,
                llm_url=settings.AI_LLM_URL,
                timeout_seconds=settings.AI_LLM_TIMEOUT_SECONDS
            )
            
            _ai_service = AIItineraryService(
                emotion_service=emotion_service,
                ranker_service=ranker_service,
                llm_service=llm_service,
                enable_emotion_detection=settings.USE_EMOTION_DETECTION,
                enable_ml_ranking=settings.USE_ML_RANKING,
                enable_llm_enhancement=settings.USE_LLM_ENHANCEMENT,
                fallback_confidence_threshold=settings.AI_CONFIDENCE_THRESHOLD
            )
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}. Using fallback.")
            _ai_service = None  # Will use rule-based fallback
    
    return _ai_service


# Update existing ItineraryGenerateView
class ItineraryGenerateView(APIView):
    """
    Generate an itinerary.
    
    UNCHANGED API CONTRACT:
    - Same request format
    - Same response format
    - Backward compatible
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/itineraries/generate/
        
        Internally uses AI system if enabled, otherwise rule-based.
        Response format is IDENTICAL to original system.
        """
        serializer = ItineraryGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # ===== USE AI SERVICE IF ENABLED =====
        if settings.USE_AI_ITINERARY_PLANNER:
            try:
                ai_service = get_ai_service()
                
                if ai_service:
                    itinerary_data = ai_service.generate_itinerary_ai(
                        user_id=request.user.id,
                        trip_params={
                            'mood': validated_data.get('mood'),
                            'interests': validated_data.get('interests', []),
                            'budget': validated_data.get('budget'),
                            'num_days': validated_data['num_days'],
                            'trip_start_date': validated_data['trip_start_date'],
                            'city': validated_data.get('city', 'Lahore'),
                        },
                        user=request.user,
                        preferences_text=request.data.get('preferences_text', ''),
                    )
                else:
                    raise Exception("AI service not initialized")
                    
            except Exception as e:
                logger.warning(f"AI generation failed: {e}. Using rule-based fallback.")
                # Fall through to rule-based generation
                itinerary_data = None
        else:
            itinerary_data = None
        
        # ===== FALLBACK TO RULE-BASED IF AI FAILED =====
        if itinerary_data is None:
            from .generator import generate_itinerary
            
            itinerary_data = generate_itinerary(
                user=request.user,
                num_days=validated_data['num_days'],
                mood=validated_data.get('mood', 'RELAXING'),
                interests=validated_data.get('interests', []),
                budget=validated_data['budget'],
                trip_start_date=validated_data['trip_start_date']
            )
        
        # ===== CREATE ITINERARY OBJECT (UNCHANGED) =====
        itinerary = Itinerary.objects.create(
            user=request.user,
            title=itinerary_data.get('title', f"Trip to {validated_data.get('city', 'Lahore')}"),
            mood=validated_data['mood'],
            interests=itinerary_data.get('interests', []),
            budget=validated_data['budget'],
            start_date=validated_data['trip_start_date'],
            data=itinerary_data,
        )
        
        # ===== NOTIFICATION (UNCHANGED) =====
        Notification.objects.create(
            user=request.user,
            title="Itinerary Generated",
            message=f"Your {validated_data['num_days']}-day itinerary is ready!",
            type="itinerary",
            data={'itinerary_id': itinerary.id}
        )
        
        # ===== RESPONSE (UNCHANGED) =====
        serializer = ItinerarySerializer(itinerary)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### 3. Create Django Management Command for Training

Create `backend/itineraries/management/commands/train_ai_ranker.py`:

```python
from django.core.management.base import BaseCommand, CommandError
from itineraries.ai_ranker_service import RankingModelTrainer, RankingFeatures
from itineraries.models import Itinerary
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train learning-to-rank model from synthetic data'
    
    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output model path', default='models/ranker_v1.0.0.pkl')
        parser.add_argument('--num-samples', type=int, help='Number of synthetic samples', default=10000)
    
    def handle(self, *args, **options):
        self.stdout.write("Training learning-to-rank model...")
        
        # Generate synthetic training data from existing heuristics
        synthetic_data = self._generate_synthetic_data(options['num_samples'])
        
        # Train model
        result = RankingModelTrainer.train_from_synthetic_data(
            synthetic_samples=synthetic_data,
            output_path=options['output']
        )
        
        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(f"Model trained successfully: {result['model_path']}")
            )
        else:
            raise CommandError(result['message'])
    
    def _generate_synthetic_data(self, num_samples):
        """Generate synthetic training samples from existing system"""
        # Implementation: iterate through Itinerary objects and generate labels
        # using current rule-based scoring
        return []
```

### 4. Create Monitoring Dashboard

Add endpoint to monitor AI system health. In `backend/itineraries/views.py`:

```python
class AIMonitoringView(APIView):
    """Monitoring endpoint for AI system health"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """GET /api/itineraries/ai-monitoring/"""
        
        from .models import AIGenerationLog
        from django.utils import timezone
        from datetime import timedelta
        
        # Get last 24 hours of generations
        since = timezone.now() - timedelta(hours=24)
        logs = AIGenerationLog.objects.filter(created_at__gte=since)
        
        metrics = {
            'total_generations': logs.count(),
            'success_rate': logs.filter(status='success').count() / max(logs.count(), 1),
            'avg_latency_ms': logs.aggregate(models.Avg('generation_latency_ms'))['generation_latency_ms__avg'] or 0,
            'fallback_rate': logs.filter(stages_log__fallback_used=True).count() / max(logs.count(), 1),
            'avg_ml_confidence': sum(
                log.ml_ranking_confidence() for log in logs
            ) / max(logs.count(), 1),
            'mood_distribution': list(logs.values('final_mood').annotate(count=models.Count('id'))),
        }
        
        return Response(metrics)
```

### 5. Test the Integration

Run tests:

```bash
cd backend

# Test emotion detection
python manage.py test itineraries.tests.test_emotion_service

# Test ML ranking
python manage.py test itineraries.tests.test_ranker_service

# Test integration
python manage.py test itineraries.tests.test_ai_service

# Test backward compatibility
python manage.py test itineraries.tests.test_api_backward_compat
```

## Database Migration

Create migration for new AI models:

```bash
python manage.py makemigrations itineraries --name add_ai_models
python manage.py migrate itineraries
```

## Configuration for Different Environments

### Development
```python
USE_AI_ITINERARY_PLANNER = True
USE_EMOTION_DETECTION = True
USE_ML_RANKING = False  # Wait for training
USE_LLM_ENHANCEMENT = False
AI_LLM_TYPE = "template"
```

### Staging
```python
USE_AI_ITINERARY_PLANNER = True
USE_EMOTION_DETECTION = True
USE_ML_RANKING = True  # Beta test ML ranking
USE_LLM_ENHANCEMENT = False
AI_ML_RANKER_MODEL_PATH = '/models/ranker_v1.0.0.pkl'
AI_CONFIDENCE_THRESHOLD = 0.7  # Higher threshold
```

### Production
```python
USE_AI_ITINERARY_PLANNER = True
USE_EMOTION_DETECTION = True
USE_ML_RANKING = True  # Full ML ranking
USE_LLM_ENHANCEMENT = False  # Or True with careful monitoring
AI_ML_RANKER_MODEL_PATH = '/models/ranker_v1.2.3.pkl'
AI_CONFIDENCE_THRESHOLD = 0.6
LOG_AI_PREDICTIONS_TO_DB = True  # Collect feedback
```

## Rollout Strategy

### Phase 1: Emotion Detection Only
- Enable Layer 1 only
- No performance impact
- Collect emotion detection accuracy data
- Monitor fallback rate

### Phase 2: Add ML Ranking
- Once emotion service is stable
- Feature flag: `USE_ML_RANKING = True`
- Rollout to 50% of users first
- Monitor latency and ranking quality

### Phase 3: Add LLM Enhancement
- Optional, non-critical layer
- Can enable/disable without breaking itineraries
- Async processing to avoid latency impact

## Debugging & Logging

Enable detailed logging:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'ai_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/ai_system.log',
        },
    },
    'loggers': {
        'itineraries.ai_emotion_service': {'handlers': ['ai_file']},
        'itineraries.ai_ranker_service': {'handlers': ['ai_file']},
        'itineraries.ai_llm_service': {'handlers': ['ai_file']},
        'itineraries.ai_service': {'handlers': ['ai_file']},
    }
}
```

## Troubleshooting

### AI Service Not Loading
- Check `LOG_AI_PREDICTIONS` is set
- Verify installed packages: `pip install lightgbm transformers torch`
- Check model file path if `AI_ML_RANKER_MODEL_PATH` set

### Slow Inference
- Check `AI_RANKER_MODEL_PATH` is loaded correctly
- Verify LightGBM is compiled with GPU support (optional)
- Check cache hit rate in metrics

### Emotion Detection Always Uses Fallback
- Transformer model needs `transformers` package
- Install: `pip install transformers torch`
- Check `USE_EMOTION_DETECTION = True` in settings

### LLM Not Enhancing Descriptions
- If using local: check Ollama running on configured port
- If using API: check API keys configured
- Check `USE_LLM_ENHANCEMENT = True` in settings
- Check timeout not too aggressive

## Production Checklist

- [ ] Database migrations run successfully
- [ ] Feature flags configured per environment
- [ ] Logging configured  
- [ ] Monitoring dashboard accessible
- [ ] Fallback tested manually
- [ ] Load testing passed (target: <100ms p95)
- [ ] User monitoring enabled
- [ ] Training pipeline scheduled (weekly)
- [ ] Model versioning system operational
- [ ] Metrics collection working

## Next Steps

1. **Train initial ML model**: Run `python manage.py train_ai_ranker` after deployment
2. **Collect user feedback**: Let system run for 2 weeks, collect implicit feedback
3. **Retrain with real data**: After feedback collected, retrain ranking model
4. **Enable LLM enhancement**: Once confidence high on Layers 1-2
5. **Optimize inference**: Profile and optimize slow components

---

See `AI_ITINERARY_ARCHITECTURE.md` for technical details.
