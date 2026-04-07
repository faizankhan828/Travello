"""
Layer 2: Learning-to-Rank Model Service

ML-based ranking of places for itinerary recommendations.
Uses LightGBM model trained on user preferences + place features.
"""

import logging
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try importing LightGBM, fallback if not available
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not available. Using rule-based fallback.")
    lgb = None


@dataclass
class RankingFeatures:
    """Feature vector for place ranking"""
    # User features
    mood_id: int  # 0-8 for each mood
    budget_level: int  # 0-3
    interest_tags: List[float]  # one-hot or embedding
    
    # Place features
    category_id: int  # 0-N categories
    place_tags: List[float]  # one-hot or embedding
    rating: float  # 1-5
    popularity_score: float  # 0-100
    price_level: int  # 1-4
    distance_from_hotel: float  # km
    
    # Contextual features
    day_index: int  # 0-N days
    time_of_day: int  # 0=morning, 1=afternoon, 2=evening
    hours_available: float  # remaining hours in day
    previously_visited_count: int  # how many days ago used this place
    
    # Place attributes
    is_outdoor: bool
    is_cultural: bool
    opening_hours_match: float  # 0-1, how well opening hours match time of day
    
    def to_array(self) -> np.ndarray:
        """Convert to flat numpy array for model"""
        features = [
            self.mood_id,
            self.budget_level,
            self.rating,
            self.popularity_score,
            self.price_level,
            self.distance_from_hotel,
            self.day_index,
            self.time_of_day,
            self.hours_available,
            self.previously_visited_count,
            float(self.is_outdoor),
            float(self.is_cultural),
            self.opening_hours_match,
            self.category_id,
        ]
        # Add any one-hot features
        features.extend(self.interest_tags)
        features.extend(self.place_tags)
        return np.array(features, dtype=np.float32)


@dataclass  
class RankedPlace:
    """Place with ranking score"""
    place_id: str
    place_name: str
    score: float  # ML model score 0-1
    confidence: float  # Model confidence 0-1
    is_ml_ranked: bool  # True if ML model, False if fallback


class LearningToRankService:
    """
    Ranks places using gradient boosted trees (LightGBM).
    Provides fallback to rule-based scoring if model unavailable.
    """
    
    MOOD_TO_ID = {
        'RELAXING': 0, 'SPIRITUAL': 1, 'HISTORICAL': 2, 'FOODIE': 3,
        'FUN': 4, 'SHOPPING': 5, 'NATURE': 6, 'ROMANTIC': 7, 'FAMILY': 8
    }
    
    CATEGORY_TO_ID = {
        'restaurant': 0, 'museum': 1, 'park': 2, 'temple': 3,
        'shopping': 4, 'hotel': 5, 'beach': 6, 'cafe': 7, 'other': 8
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize ranking service.
        
        Args:
            model_path: Path to saved LightGBM model. If None, use rule-based fallback.
        """
        self.model = None
        self.model_version = None
        self.last_confidence = 0.0
        self.inference_latency_ms = 0
        
        if model_path and LIGHTGBM_AVAILABLE:
            self.model = self._load_model(model_path)
        else:
            logger.info("ML ranking model not loaded. Using rule-based fallback.")
    
    def _load_model(self, model_path: str) -> Optional['lgb.Booster']:
        """Load pre-trained LightGBM model"""
        try:
            model = lgb.Booster(model_file=model_path)
            logger.info(f"Loaded LightGBM model from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None
    
    def rank_places(
        self,
        user_mood: str,
        candidate_places: List[Dict],
        user_interests: List[str],
        user_budget: str,
        day_index: int = 0,
        time_of_day: str = "morning",
        current_location: Tuple[float, float] = None,
        previously_visited: List[str] = None,
        use_ml: bool = True
    ) -> List[RankedPlace]:
        """
        Rank places using ML model or rule-based scoring.
        
        Args:
            user_mood: User's selected mood
            candidate_places: List of place dicts with id, name, category, rating, etc.
            user_interests: User's interests (e.g., ["nature", "history"])
            user_budget: Budget level ("low", "medium", "high")
            day_index: Day number in trip (0-indexed)
            time_of_day: Current time ("morning", "afternoon", "evening")
            current_location: (lat, lon) tuple
            previously_visited: List of place IDs used in earlier days
            use_ml: Whether to use ML model (vs pure rule-based)
            
        Returns:
            List of RankedPlace objects sorted by score (descending)
        """
        import time
        start_time = time.time()
        
        ranked_places = []
        
        for place in candidate_places:
            # Build feature vector for this place
            features = self._build_features(
                user_mood=user_mood,
                user_interests=user_interests,
                user_budget=user_budget,
                place=place,
                day_index=day_index,
                time_of_day=time_of_day,
                current_location=current_location,
                previously_visited=previously_visited or []
            )
            
            # Get ranking score
            if use_ml and self.model:
                score, confidence = self._get_ml_score(features)
                is_ml = True
            else:
                score, confidence = self._get_fallback_score(features)
                is_ml = False
            
            # Apply diversity penalty
            if place.get('id') in (previously_visited or []):
                days_ago = day_index  # Simplified: used in earlier days
                diversity_penalty = 0.8 ** days_ago  # Exponential decay
                score *= (1 - diversity_penalty * 0.2)  # Reduce score by up to 20%
            
            ranked_places.append(RankedPlace(
                place_id=place.get('id'),
                place_name=place.get('name'),
                score=score,
                confidence=confidence,
                is_ml_ranked=is_ml
            ))
        
        # Sort by score descending
        ranked_places.sort(key=lambda p: p.score, reverse=True)
        
        # Record stats
        self.last_confidence = np.mean([p.confidence for p in ranked_places]) if ranked_places else 0.0
        self.inference_latency_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            f"Ranked {len(ranked_places)} places for mood={user_mood}, "
            f"day={day_index}, latency={self.inference_latency_ms:.1f}ms"
        )
        
        return ranked_places
    
    def _build_features(
        self,
        user_mood: str,
        user_interests: List[str],
        user_budget: str,
        place: Dict,
        day_index: int,
        time_of_day: str,
        current_location: Tuple[float, float],
        previously_visited: List[str]
    ) -> RankingFeatures:
        """Build feature vector for a single place"""
        
        # Time of day encoding
        time_encoding = {'morning': 0, 'afternoon': 1, 'evening': 2}
        time_code = time_encoding.get(time_of_day.lower(), 1)
        
        # Budget encoding
        budget_encoding = {'low': 0, 'medium': 1, 'high': 2, 'luxury': 3}
        budget_code = budget_encoding.get(user_budget.lower(), 1)
        
        # Mood encoding
        mood_code = self.MOOD_TO_ID.get(user_mood.upper(), 0)
        
        # Category encoding
        category = place.get('category', 'other').lower()
        category_code = self.CATEGORY_TO_ID.get(category, self.CATEGORY_TO_ID['other'])
        
        # Distance calculation
        distance = 0.0
        if current_location and place.get('latitude') and place.get('longitude'):
            distance = self._haversine_distance(
                current_location[0], current_location[1],
                place['latitude'], place['longitude']
            )
        
        # Interest tag matching
        place_tags = place.get('tags', [])
        interest_matches = len(set(user_interests) & set(place_tags))
        tag_match_vec = [float(interest_matches) / max(len(user_interests), 1)]
        
        # Place tag vector (simplified one-hot)
        place_tag_vec = [float(tag in place_tags) for tag in ['outdoor', 'cultural', 'food']]
        
        # Previously visited count (recency)
        prev_visit_count = 0
        if place.get('id') in previously_visited:
            prev_visit_count = min(day_index, 3)
        
        # Opening hours match (0-1)
        opening_hours_match = self._calculate_opening_hours_match(place, time_of_day)
        
        return RankingFeatures(
            mood_id=mood_code,
            budget_level=budget_code,
            interest_tags=tag_match_vec,
            category_id=category_code,
            place_tags=place_tag_vec,
            rating=place.get('rating', 3.5),
            popularity_score=place.get('popularity_score', 50),
            price_level=place.get('price_level', 2),
            distance_from_hotel=distance,
            day_index=day_index,
            time_of_day=time_code,
            hours_available=8.0,
            previously_visited_count=prev_visit_count,
            is_outdoor=place.get('is_outdoor', False),
            is_cultural=place.get('is_cultural', False),
            opening_hours_match=opening_hours_match
        )
    
    def _get_ml_score(self, features: RankingFeatures) -> Tuple[float, float]:
        """Get score from ML model"""
        try:
            if not self.model:
                raise ValueError("Model not loaded")
            
            feature_array = features.to_array()
            score = self.model.predict(feature_array.reshape(1, -1))[0]
            score = 1.0 / (1.0 + np.exp(-score))
            confidence = min(abs(score - 0.5) * 2, 0.95)
            
            return float(score), float(confidence)
        except Exception as e:
            logger.warning(f"ML scoring failed: {e}. Using fallback.")
            return self._get_fallback_score(features)
    
    def _get_fallback_score(self, features: RankingFeatures) -> Tuple[float, float]:
        """Fallback rule-based scoring when ML model unavailable."""
        score = 0.0
        
        score += (features.rating / 5.0) * 0.3
        score += (features.popularity_score / 100.0) * 0.2
        
        interest_match = features.interest_tags[0] if features.interest_tags else 0
        score += interest_match * 0.25
        
        if features.is_cultural:
            score += 0.08
        if features.is_outdoor and features.day_index % 2 == 0:
            score += 0.07
        
        score += features.opening_hours_match * 0.1
        
        distance_penalty = min(features.distance_from_hotel / 20.0, 0.2)
        score -= distance_penalty * 0.1
        
        score = max(0.0, min(score, 1.0))
        confidence = 0.5
        
        return score, confidence
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two lat/lon points"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371
        
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def _calculate_opening_hours_match(place: Dict, time_of_day: str) -> float:
        """Estimate if place should be open during given time"""
        opening_hours = place.get('opening_hours', '')
        
        if not opening_hours:
            return 0.8
        
        if 'closed' in opening_hours.lower():
            return 0.0
        
        if 'museum' in place.get('category', '').lower():
            return 0.7 if time_of_day == 'morning' or time_of_day == 'afternoon' else 0.3
        
        if 'restaurant' in place.get('category', '').lower():
            if time_of_day == 'morning':
                return 0.3
            elif time_of_day == 'afternoon':
                return 0.8
            else:
                return 0.9
        
        if place.get('is_outdoor'):
            return 1.0 if time_of_day != 'evening' else 0.5
        
        return 0.8
    
    def hybrid_score(self, ml_score: float, fallback_score: float, confidence: float) -> float:
        """Blend ML score with fallback score based on confidence."""
        if confidence < 0.4:
            return 0.3 * ml_score + 0.7 * fallback_score
        elif confidence < 0.6:
            return 0.5 * ml_score + 0.5 * fallback_score
        else:
            return 0.8 * ml_score + 0.2 * fallback_score


class RankingModelTrainer:
    """Utility class for training LightGBM ranking models offline."""
    
    @staticmethod
    def train_from_synthetic_data(
        synthetic_samples: List[Dict],
        output_path: str
    ) -> Dict:
        """Train model from synthetic training data."""
        if not LIGHTGBM_AVAILABLE:
            logger.error("LightGBM not available for training")
            return {'status': 'error', 'message': 'LightGBM not installed'}
        
        X = np.array([s['features'].to_array() for s in synthetic_samples])
        y = np.array([s['label'] for s in synthetic_samples])
        
        logger.info(f"Training LightGBM with {len(X)} samples")
        
        train_data = lgb.Dataset(X, label=y)
        
        params = {
            'goal': 'train',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'verbose': -1,
        }
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
        )
        
        model.save_model(output_path)
        logger.info(f"Model saved to {output_path}")
        
        return {
            'status': 'success',
            'model_path': output_path,
            'num_samples': len(X),
            'num_features': X.shape[1]
        }
