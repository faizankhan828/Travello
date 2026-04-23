"""
Feature extraction for ML ranker training.
Converts DataSample objects to feature vectors matching training expectations.
"""

import logging
from typing import Tuple, List
import numpy as np
from .ranker_data_analyzer import DataSample

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract features from DataSample for training"""
    
    # Must match train_itinerary_ranker.py
    MOOD_TO_ID = {
        'RELAXING': 0, 'SPIRITUAL': 1, 'HISTORICAL': 2, 'FOODIE': 3,
        'FUN': 4, 'SHOPPING': 5, 'NATURE': 6, 'ROMANTIC': 7, 'FAMILY': 8
    }
    
    BUDGET_TO_ID = {'LOW': 0, 'MEDIUM': 1, 'LUXURY': 2}
    
    CATEGORY_TO_ID = {
        'religious': 0, 'history': 1, 'culture': 2, 'food': 3,
        'nature': 4, 'shopping': 5, 'modern': 6, 'other': 7
    }
    
    PACE_TO_ID = {'RELAXED': 0, 'BALANCED': 1, 'PACKED': 2}
    
    # Feature columns in exact order (matches training script)
    FEATURE_COLUMNS = [
        # User features
        'user_mood_id',
        'user_budget_id',
        'user_pace_id',
        'user_interests_count',
        
        # Place features
        'place_category_id',
        'place_rating',
        'place_budget_id',
        'place_visit_minutes',
        'place_tags_count',
        'place_ideal_start',
        'place_ideal_end',
        
        # Contextual features
        'trip_day',
        'trip_total_days',
        
        # Geographic
        'distance_km',
        
        # Interaction features
        'user_interests_match',
        'budget_match',
        'cultural_match',
    ]
    
    NUM_FEATURES = len(FEATURE_COLUMNS)
    
    @staticmethod
    def extract_features(samples: List[DataSample]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract features from DataSample objects.
        
        Args:
            samples: List of DataSample objects
        
        Returns:
            Tuple of (X, y) where:
            - X: Feature matrix (N, 17)
            - y: Target vector (N,) with selection quality scores
        """
        X_list = []
        y_list = []
        
        for sample in samples:
            # User features
            user_mood_id = FeatureExtractor.MOOD_TO_ID.get(sample.user_mood, 0)
            user_budget_id = FeatureExtractor.BUDGET_TO_ID.get(sample.user_budget, 0)
            user_pace_id = FeatureExtractor.PACE_TO_ID.get(sample.user_pace, 0)
            user_interests_count = len(sample.user_interests) if sample.user_interests else 0
            
            # Place features
            place_category_id = FeatureExtractor.CATEGORY_TO_ID.get(
                sample.place_category.lower(), 7
            )
            place_rating = sample.place_rating / 5.0  # Normalize to 0-1
            place_budget_id = FeatureExtractor.BUDGET_TO_ID.get(sample.place_budget_level, 0)
            place_visit_minutes = sample.place_visit_minutes / 300.0  # Normalize (max ~300)
            place_tags_count = len(sample.place_tags) if sample.place_tags else 0
            place_ideal_start = sample.place_ideal_start / 24.0
            place_ideal_end = sample.place_ideal_end / 24.0
            
            # Contextual features
            trip_day = sample.trip_day / max(sample.trip_total_days, 1)
            trip_total_days = sample.trip_total_days / 7.0  # Normalize (typical trip ~7 days)
            
            # Geographic
            distance_km = sample.distance_km / 100.0  # Normalize (max ~100km)
            
            # Interaction features
            user_interests_match = 1.0 if (
                sample.user_interests and sample.place_tags and
                any(tag.lower() in [i.lower() for i in sample.user_interests]
                    for tag in sample.place_tags)
            ) else 0.0
            
            budget_match = 1.0 if (
                FeatureExtractor.BUDGET_TO_ID.get(sample.place_budget_level, 0) <=
                FeatureExtractor.BUDGET_TO_ID.get(sample.user_budget, 0)
            ) else 0.0
            
            place_is_cultural = sample.place_category.lower() in ['religious', 'history', 'culture']
            mood_is_cultural = sample.user_mood in ['SPIRITUAL', 'HISTORICAL']
            cultural_match = 1.0 if place_is_cultural and mood_is_cultural else 0.0
            
            # Build feature vector in exact order
            feature_vector = [
                user_mood_id,
                user_budget_id,
                user_pace_id,
                user_interests_count,
                place_category_id,
                place_rating,
                place_budget_id,
                place_visit_minutes,
                place_tags_count,
                place_ideal_start,
                place_ideal_end,
                trip_day,
                trip_total_days,
                distance_km,
                user_interests_match,
                budget_match,
                cultural_match,
            ]
            
            X_list.append(feature_vector)
            y_list.append(sample.selection_quality)
        
        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)
        
        logger.info(f"Extracted {len(samples)} samples with {X.shape[1]} features")
        logger.info(f"  Feature shape: {X.shape}, Target shape: {y.shape}")
        logger.info(f"  Target range: [{y.min():.3f}, {y.max():.3f}]")
        
        return X, y
