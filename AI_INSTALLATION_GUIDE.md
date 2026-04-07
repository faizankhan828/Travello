# AI Itinerary System - Installation & Setup Guide

## System Requirements

### Python Version
- Python 3.8+ (3.10+ recommended for better performance)

### GPU (Optional but Recommended)
- Emotion detection runs on CPU, but faster on GPU
- If using CUDA-enabled GPU: NVIDIA CUDA 11.8+ and cuDNN 8.x
- Not required; CPU works fine with lazy loading

## Dependencies Installation

### Step 1: Add to `backend/requirements.txt`

```txt
# ============================================
# AI ITINERARY SYSTEM DEPENDENCIES
# ============================================

# Core ML/AI libraries
lightgbm>=4.0.0              # Gradient boosted trees for ranking
xgboost>=2.0.0              # Alternative to LightGBM
scikit-learn>=1.3.0         # Feature engineering utilities

# NLP & Transformers
transformers>=4.30.0        # HuggingFace transformers for emotion detection
torch>=2.0.0                # PyTorch backend for transformers
# (torch can be replaced with tensorflow for lighter weight)

# Optional: For better emoji/text handling
numpy>=1.24.0
scipy>=1.11.0

# Optional: For LLM support (if using Ollama or OpenAI)
requests>=2.31.0            # HTTP client for Ollama
openai>=1.0.0              # If using OpenAI API (optional)

# Optional: For model serialization
pickle5>=0.0.12            # Better pickle support

# Data handling
pandas>=2.0.0              # DataFrame operations for training
```

### Step 2: Install Python Dependencies

```bash
cd backend

# Install all dependencies
pip install -r requirements.txt

# Or install only core AI dependencies (without optional packages)
pip install lightgbm transformers torch scikit-learn numpy scipy

# Optimize torch for CPU-only (reduces download size)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Step 3: Verify Installation

```bash
python << EOF
# Test imports
try:
    import lightgbm as lgb
    print(f"✓ LightGBM {lgb.__version__}")
except:
    print("✗ LightGBM not installed")

try:
    import transformers
    print(f"✓ Transformers {transformers.__version__}")
except:
    print("✗ Transformers not installed")

try:
    import torch
    print(f"✓ PyTorch {torch.__version__}")
    print(f"  CUDA available: {torch.cuda.is_available()}")
except:
    print("✗ PyTorch not installed")

try:
    import sklearn
    print(f"✓ Scikit-learn {sklearn.__version__}")
except:
    print("✗ Scikit-learn not installed")
EOF
```

## Optional: GPU Setup (Recommended for Production)

### NVIDIA GPU Setup

```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name())"

# Install CUDA-enabled PyTorch (example for CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Test GPU
python << EOF
import torch
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.matmul(x, y)
    print("✓ GPU computation works!")
else:
    print("No GPU available, using CPU")
EOF
```

### Apple Silicon (Mac) Setup

```bash
# Install optimized for Apple Silicon
pip install lightgbm transformers torch --no-binary :all:
```

## Model Downloads

### Pre-download Transformer Models (Optional)

Models are auto-downloaded on first use, but pre-downloading helps with offline use:

```bash
python << EOF
from transformers import pipeline

# Download emotion detection model
print("Downloading emotion detection model...")
classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base"
)

# Test
result = classifier("I'm excited about this trip!")
print(f"Downloaded successfully. Sample: {result}")
EOF
```

### Pre-trained ML Ranker Model

LightGBM model will be trained after deployment. For initial deployment, use rule-based fallback:

```python
# settings.py
AI_ML_RANKER_MODEL_PATH = None  # Will train after initial data collection
```

## Docker Setup

### Dockerfile for AI System

If using Docker, update `backend/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download transformer models
RUN python << EOF
from transformers import pipeline
try:
    pipeline("text-classification", 
             model="j-hartmann/emotion-english-distilroberta-base")
    print("Model cached successfully")
except Exception as e:
    print(f"Warning: Could not pre-download model: {e}")
EOF

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Docker Compose with GPU Support

For production with GPU:

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - model_cache:/root/.cache  # Cache downloaded models
    environment:
      - USE_AI_ITINERARY_PLANNER=true
      - USE_EMOTION_DETECTION=true
      - USE_ML_RANKING=true
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  model_cache:
```

## Environment Variables

Create `.env` file:

```bash
# AI System Configuration
USE_AI_ITINERARY_PLANNER=true
USE_EMOTION_DETECTION=true
USE_ML_RANKING=true
USE_LLM_ENHANCEMENT=false

# Model Paths
AI_ML_RANKER_MODEL_PATH=/models/ranker_v1.0.0.pkl

# LLM Configuration (if enabled)
AI_LLM_TYPE=template
AI_LLM_MODEL_NAME=mistral
AI_LLM_URL=http://localhost:11434
AI_LLM_TIMEOUT_SECONDS=3

# Monitoring
LOG_AI_PREDICTIONS=true
LOG_AI_PREDICTIONS_TO_DB=true
```

## Testing Installation

### Run Unit Tests

```bash
cd backend

# Test all AI components
python manage.py test itineraries.tests

# Test specific components
python manage.py test itineraries.tests.test_emotion_service
python manage.py test itineraries.tests.test_ranker_service
python manage.py test itineraries.tests.test_ai_service

# With verbose output
python manage.py test itineraries.tests -v 2
```

### Manual Testing in Django Shell

```bash
python manage.py shell

# Test emotion detection
from itineraries.ai_emotion_service import AIEmotionDetectionService
service = AIEmotionDetectionService()
result = service.detect_emotion("I want to relax and enjoy nature in a peaceful place")
print(f"Detected emotion: {result.detected_emotion}, Confidence: {result.confidence}")

# Test mood blending
final_mood = service.get_final_mood(
    manual_mood="RELAXING",
    user_text="I really love hiking and adventure"
)
print(f"Final mood: {final_mood}")

# Test ML ranking service
from itineraries.ai_ranker_service import LearningToRankService
ranker = LearningToRankService()

places = [
    {'id': '1', 'name': 'Museum', 'category': 'museum', 'rating': 4.5, 'popularity_score': 80},
    {'id': '2', 'name': 'Park', 'category': 'park', 'rating': 4.0, 'popularity_score': 70},
    {'id': '3', 'name': 'Restaurant', 'category': 'restaurant', 'rating': 4.7, 'popularity_score': 90},
]

ranked = ranker.rank_places(
    user_mood='RELAXING',
    candidate_places=places,
    user_interests=['nature', 'history'],
    user_budget='medium'
)

for place in ranked:
    print(f"{place.place_name}: {place.score:.3f} (confidence: {place.confidence:.2f})")

# Test complete AI service
from itineraries.ai_service import AIItineraryService
ai_service = AIItineraryService()

itinerary = ai_service.generate_itinerary_ai(
    user_id=1,
    trip_params={
        'mood': 'RELAXING',
        'interests': ['nature', 'food'],
        'budget': 'medium',
        'num_days': 3,
        'trip_start_date': '2026-04-20',
        'city': 'Lahore'
    },
    preferences_text="I want a calm trip with good food"
)

print(f"Generated {len(itinerary.get('days', []))} days of itinerary")
```

## Offline Model Cache

For production deployments without internet:

### Cache Models Locally

```bash
# Download and cache models before deployment
python << EOF
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

cache_dir = "/path/to/model/cache"
os.makedirs(cache_dir, exist_ok=True)

# Download emotion model
model_name = "j-hartmann/emotion-english-distilroberta-base"
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
model = AutoModelForSequenceClassification.from_pretrained(model_name, cache_dir=cache_dir)

print(f"Models cached to {cache_dir}")
EOF

# Set environment variable
export HF_HOME=/path/to/model/cache

# Test
python -c "from transformers import pipeline; p = pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base')"
```

### In settings.py

```python
import os

# Point to cached models
os.environ['HF_HOME'] = '/path/to/model/cache'
os.environ['TRANSFORMERS_CACHE'] = '/path/to/model/cache'
```

## Memory Management

### Optimize for Limited Memory

If running on memory-constrained systems (e.g., t2.small AWS):

```python
# settings.py
import os
os.environ['OMP_NUM_THREADS'] = '2'  # Limit OpenMP threads

# Reduce batch size
AI_RANKER_BATCH_SIZE = 1  # Process places one at a time

# Disable GPU if memory constrained
CUDA_VISIBLE_DEVICES = ''  # Force CPU

# Lazy load models
AI_LAZY_LOAD_EMOTION_MODEL = True
AI_LAZY_LOAD_RANKER_MODEL = True
```

## Troubleshooting Installation

### Issue: LightGBM build fails

**Solution:**
```bash
# Install pre-built wheel
pip install --only-binary=:all: lightgbm

# Or use conda
conda install lightgbm
```

### Issue: Transformers downloads SSL certificate error

**Solution:**
```bash
# Disable SSL verification (development only!)
pip install requests urllib3
export SSL_NO_VERIFY=true

# Or in Python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### Issue: PyTorch installation very slow

**Solution:**
```bash
# Use CPU-only version (much faster download)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: Out of memory during model download

**Solution:**
```bash
# Download and cache separately
python << EOF
import transformers
transformers.AutoModel.from_pretrained(
    "j-hartmann/emotion-english-distilroberta-base",
    cache_dir="/tmp/model_cache"
)
EOF

# Then reference in code
export HF_HOME=/tmp/model_cache
```

## Performance Tuning

### Enable GPU Acceleration

```python
# For emotion detection (PyTorch)
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# For LightGBM
# LightGBM automatically uses GPU if available, configure:
import lightgbm as lgb
params = {
    'device': 'gpu',  # or 'cpu'
    'gpu_device_id': 0,
}
```

### Parallel Processing

```python
# settings.py
AI_NUM_WORKERS = 4  # For multi-worker inference
AI_BATCH_PREDICT = True  # Batch predictions
```

## Monitoring Installation

### Check System Health

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep python | grep -E "memory|CPU"'

# Monitor GPU (if available)
nvidia-smi -l 1

# Check model cache size
du -sh ~/.cache/huggingface/
```

---

## Next Steps

1. ✅ Install dependencies (follow above)
2. ✅ Run tests to verify installation
3. ✅ Configure Django settings (see Integration Guide)
4. ✅ Update views.py to use AI service
5. ✅ Run database migrations
6. ✅ Test itinerary endpoint with AI
7. ✅ Train initial ML ranker model
8. ✅ Deploy to staging
9. ✅ Monitor metrics
10. ✅ Train on real user data
11. ✅ Deploy to production

See `AI_INTEGRATION_GUIDE.md` for Django integration next steps.
