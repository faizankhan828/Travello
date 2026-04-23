# ML Models Directory

This directory contains trained machine learning models for Travello.

## 📦 Contents

### `itinerary_ranker.pkl` (Created by training)
**Status:** Not committed to git (see `../.gitignore`)  
**Size:** ~2-5 MB (typical)  
**Type:** LightGBM Ranking Model  
**Framework:** Pickled Python object

**Contents:**
```
{
    'model': <LightGBM booster>,
    'scaler': <StandardScaler>,
    'feature_columns': [17 feature names],
    'categorical_mappings': {...},
    'trained_at': <ISO timestamp>,
    'model_type': 'LightGBMRegressor',
    'framework_versions': {...},
}
```

## 🚀 How to Train

```bash
cd backend
python manage.py train_itinerary_ranker --verbose
```

**Output:** `itinerary_ranker.pkl` created in this directory

## 🔄 How to Use

```python
from ml_system.ranker_model_loader import get_ranking_score_from_model

score = get_ranking_score_from_model(
    user_mood='RELAXING',
    user_budget='MEDIUM',
    ...,
)
```

Model automatically loads on first use.

## ⚙️ Auto-Integration

- Model is **automatically used** by `ai_ranker_service.py`
- No code changes needed
- Falls back to rules if model unavailable
- Transparent to frontend/API

## 📝 Notes

- **Not in Git:** `.pkl` files excluded by `.gitignore`
- **Per Developer:** Each developer trains their own
- **Production:** Train on production server with full data
- **Version:** Model includes metadata for reproducibility

## 📚 Documentation

See `../MODEL_TRAINING_GUIDE.md` for complete guide.
See `../TRAINING_IMPLEMENTATION_CHECKLIST.md` for quick reference.

---

**Last Updated:** April 15, 2026
