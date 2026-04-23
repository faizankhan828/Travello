"""
Model Loader & Inference for Itinerary Ranker

Purpose:
    Load trained LightGBM model and provide inference interface
    for integration with ai_ranker_service.py

Features:
    1. Lazy load trained model from disk
    2. Handle feature encoding and preprocessing
    3. Graceful fallback if model unavailable
    4. Performance metrics logging
"""

import os
import pickle
import logging
from typing import Optional, Dict, List
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class RankerModelLoader:
    """Singleton-like loader for trained ranker model"""
    
    _instance = None
    _model = None
    _scaler = None
    _metadata = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def load_model(model_path: Optional[str] = None) -> bool:
        """
        Load trained model from disk
        
        Args:
            model_path: Path to saved model. If None, uses default path.
        
        Returns:
            True if load successful, False otherwise
        """
        if model_path is None:
            # Try default path
            from django.conf import settings
            model_path = os.path.join(
                settings.BASE_DIR.parent,
                'backend',
                'ml_models',
                'itinerary_ranker.pkl'
            )
        
        try:
            if not os.path.exists(model_path):
                logger.debug(f"Model not found at {model_path}")
                return False
            
            with open(model_path, 'rb') as f:
                package = pickle.load(f)
            
            RankerModelLoader._model = package.get('model')
            RankerModelLoader._scaler = package.get('scaler')
            RankerModelLoader._metadata = {
                'trained_at': package.get('trained_at'),
                'model_type': package.get('model_type'),
                'feature_columns': package.get('feature_columns', []),
                'categorical_mappings': package.get('categorical_mappings', {}),
            }
            
            logger.info(f"✓ Loaded ranker model from {model_path}")
            return True
        
        except Exception as e:
            logger.warning(f"Failed to load ranker model: {str(e)}")
            return False
    
    @staticmethod
    def get_model():
        """Get loaded model (lazy loads if needed)"""
        if RankerModelLoader._model is None:
            RankerModelLoader.load_model()
        return RankerModelLoader._model
    
    @staticmethod
    def get_scaler():
        """Get fitted scaler"""
        return RankerModelLoader._scaler
    
    @staticmethod
    def get_metadata() -> Dict:
        """Get model metadata"""
        return RankerModelLoader._metadata or {}
    
    @staticmethod
    def is_loaded() -> bool:
        """Check if model is loaded"""
        return RankerModelLoader._model is not None
    
    @staticmethod
    def predict(features: np.ndarray) -> np.ndarray:
        """
        Make predictions using loaded model
        
        Args:
            features: Feature array, shape (N, num_features)
        
        Returns:
            Prediction array, shape (N,)
        """
        model = RankerModelLoader.get_model()
        scaler = RankerModelLoader.get_scaler()
        
        if model is None or scaler is None:
            return None
        
        try:
            # Scale features
            features_scaled = scaler.transform(features)
            
            # Make predictions
            predictions = model.predict(features_scaled)
            
            return predictions
        
        except Exception as e:
            logger.warning(f"Error during model inference: {str(e)}")
            return None


def encode_features_for_ranking(
    user_mood: str,
    user_budget: str,
    user_interests: List[str],
    user_pace: str,
    place_category: str,
    place_rating: float,
    place_budget: str,
    place_visit_minutes: int,
    place_tags: List[str] = None,
    place_ideal_start: int = 9,
    place_ideal_end: int = 18,
    trip_day: int = 1,
    trip_total_days: int = 7,
    distance_km: float = 0.0,
) -> Optional[np.ndarray]:
    """
    Encode user and place features for ML model inference
    
    Args:
        user_mood: User travel mood (e.g., 'RELAXING')
        user_budget: User budget level ('LOW', 'MEDIUM', 'LUXURY')
        user_interests: List of user interest tags
        user_pace: Trip pace ('RELAXED', 'BALANCED', 'PACKED')
        place_category: Place category
        place_rating: Place rating (0-5)
        place_budget: Place budget level
        place_visit_minutes: Estimated visit duration
        place_tags: Place tags
        place_ideal_start: Place ideal start hour
        place_ideal_end: Place ideal end hour
        trip_day: Day number in trip (1-indexed)
        trip_total_days: Total days in trip
        distance_km: Distance from hotel in km
    
    Returns:
        Feature array (1, 17) suitable for model prediction, or None if encoding fails
    """
    
    metadata = RankerModelLoader.get_metadata()
    mappings = metadata.get('categorical_mappings', {})
    
    try:
        # Get mappings
        mood_to_id = mappings.get('mood_to_id', {})
        budget_to_id = mappings.get('budget_to_id', {})
        category_to_id = mappings.get('category_to_id', {})
        pace_to_id = mappings.get('pace_to_id', {})
        
        # Encode user features
        user_mood_id = mood_to_id.get(user_mood, 0)
        user_budget_id = budget_to_id.get(user_budget, 0)
        user_pace_id = pace_to_id.get(user_pace, 0)
        user_interests_count = len(user_interests) if user_interests else 0
        
        # Encode place features
        place_category_id = category_to_id.get(place_category.lower(), 7)
        place_rating_norm = place_rating / 5.0
        place_budget_id = budget_to_id.get(place_budget, 0)
        place_visit_minutes_norm = min(place_visit_minutes / 300.0, 1.0)
        place_tags_count = len(place_tags) if place_tags else 0
        place_ideal_start_norm = place_ideal_start / 24.0
        place_ideal_end_norm = place_ideal_end / 24.0
        
        # Contextual features
        trip_day_norm = trip_day / trip_total_days if trip_total_days > 0 else 0
        trip_total_days_norm = trip_total_days / 7.0
        
        # Geographic
        distance_norm = distance_km / 100.0
        
        # Interaction features
        user_interests_match = 1.0 if (
            user_interests and place_tags and
            any(tag.lower() in [i.lower() for i in user_interests]
                for tag in place_tags)
        ) else 0.0
        
        budget_match = 1.0 if (
            budget_to_id.get(place_budget, 2) <= budget_to_id.get(user_budget, 2)
        ) else 0.0
        
        place_is_cultural = place_category.lower() in ['religious', 'history', 'culture']
        mood_is_cultural = user_mood in ['SPIRITUAL', 'HISTORICAL']
        cultural_match = 1.0 if place_is_cultural and mood_is_cultural else 0.0
        
        # Build feature vector
        features = np.array([[
            user_mood_id,
            user_budget_id,
            user_pace_id,
            user_interests_count,
            place_category_id,
            place_rating_norm,
            place_budget_id,
            place_visit_minutes_norm,
            place_tags_count,
            place_ideal_start_norm,
            place_ideal_end_norm,
            trip_day_norm,
            trip_total_days_norm,
            distance_norm,
            user_interests_match,
            budget_match,
            cultural_match,
        ]], dtype=np.float32)
        
        return features
    
    except Exception as e:
        logger.warning(f"Error encoding features: {str(e)}")
        return None


def get_ranking_score_from_model(
    user_mood: str,
    user_budget: str,
    user_interests: List[str],
    user_pace: str,
    place_category: str,
    place_rating: float,
    place_budget: str,
    place_visit_minutes: int,
    place_tags: List[str] = None,
    place_ideal_start: int = 9,
    place_ideal_end: int = 18,
    trip_day: int = 1,
    trip_total_days: int = 7,
    distance_km: float = 0.0,
    fallback_score: Optional[float] = None,
) -> Optional[float]:
    """
    Get ranking score from ML model for a place, with fallback
    
    Args:
        All the same as encode_features_for_ranking()
        fallback_score: Score to return if model unavailable
    
    Returns:
        Ranking score (0-1) from model, or fallback_score if model unavailable
    """
    
    # Try to get model prediction
    if not RankerModelLoader.is_loaded():
        RankerModelLoader.load_model()
    
    if RankerModelLoader.get_model() is None:
        logger.debug("ML model not available, using fallback score")
        return fallback_score
    
    try:
        # Encode features
        features = encode_features_for_ranking(
            user_mood, user_budget, user_interests, user_pace,
            place_category, place_rating, place_budget, place_visit_minutes,
            place_tags, place_ideal_start, place_ideal_end,
            trip_day, trip_total_days, distance_km
        )
        
        if features is None:
            return fallback_score
        
        # Get prediction
        prediction = RankerModelLoader.predict(features)
        
        if prediction is None or len(prediction) == 0:
            return fallback_score
        
        # Return first (only) prediction, clipped to 0-1
        score = float(prediction[0])
        score = max(0.0, min(1.0, score))
        
        return score
    
    except Exception as e:
        logger.warning(f"Error getting model score: {str(e)}")
        return fallback_score


# Autoinitialize on import
try:
    if not RankerModelLoader.is_loaded():
        RankerModelLoader.load_model()
except Exception:
    pass  # Silently fail if model not available yet
