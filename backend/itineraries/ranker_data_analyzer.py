"""
Data analyzer for ML ranker training.
Extracts features from real itinerary data or generates synthetic data.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
import random

from django.db.models import Count, Q
from .models import Itinerary, Place

logger = logging.getLogger(__name__)


@dataclass
class DataSample:
    """Single training sample for ranker model"""
    # User features
    user_mood: str  # 'RELAXING', 'SPIRITUAL', etc.
    user_budget: str  # 'LOW', 'MEDIUM', 'LUXURY'
    user_pace: str  # 'RELAXED', 'BALANCED', 'PACKED'
    user_interests: List[str]
    
    # Place features
    place_name: str
    place_category: str
    place_rating: float
    place_budget_level: str
    place_visit_minutes: int
    place_tags: List[str]
    place_ideal_start: int
    place_ideal_end: int
    
    # Geographic
    place_latitude: float
    place_longitude: float
    hotel_latitude: float
    hotel_longitude: float
    distance_km: float
    
    # Contextual
    trip_day: int  # 0-indexed day in trip
    trip_total_days: int
    
    # Target (only for real data)
    was_selected: bool
    selection_quality: float  # 0-1 score


class RankerDataAnalyzer:
    """Analyze and extract training data for ranker model"""
    
    # Categorical mappings (must match training script)
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
    
    def __init__(self, verbose: bool = False):
        """Initialize analyzer"""
        self.verbose = verbose
        self.samples: List[DataSample] = []
        self._log("Initialized RankerDataAnalyzer")
    
    def _log(self, msg: str):
        """Log message"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {msg}")
        logger.info(msg)
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate approximate distance in km using Haversine formula"""
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km
    
    def _calculate_selection_quality(self, sample: DataSample) -> float:
        """
        Calculate quality score (0-1) for a selection based on features.
        Used when training on real data.
        """
        score = 0.0
        
        # Rating match (30%)
        score += (sample.place_rating / 5.0) * 0.30
        
        # Budget match (20%)
        if (self.BUDGET_TO_ID.get(sample.place_budget_level, 0) <= 
            self.BUDGET_TO_ID.get(sample.user_budget, 0)):
            score += 0.20
        
        # Interest match (25%)
        if (sample.user_interests and sample.place_tags and
            any(tag.lower() in [i.lower() for i in sample.user_interests]
                for tag in sample.place_tags)):
            score += 0.25
        
        # Cultural match (15%)
        place_is_cultural = sample.place_category.lower() in ['religious', 'history', 'culture']
        mood_is_cultural = sample.user_mood in ['SPIRITUAL', 'HISTORICAL']
        if place_is_cultural and mood_is_cultural:
            score += 0.15
        
        # Distance penalty (10%)
        if sample.distance_km < 20:
            score += 0.10
        elif sample.distance_km < 50:
            score += 0.05
        
        return min(score, 1.0)
    
    def _create_target_score(self, was_selected: bool, place_rating: float) -> float:
        """
        Create meaningful target score for training.
        
        Combines:
        - Selection signal (70%): was place selected in itinerary?
        - Rating signal (30%): how well-rated is the place?
        
        This ensures:
        - Selected places get HIGHER scores (0.7-1.0)
        - Not selected places get LOWER scores (0.0-0.3)
        - Rating variations add diversity within each group
        """
        # Normalize rating to 0-1
        rating_normalized = (place_rating / 5.0) if place_rating else 0.5
        
        # Selection is the dominant signal
        selection_signal = 1.0 if was_selected else 0.0
        
        # Combine: selected places get 0.7-1.0, not selected get 0.0-0.3
        target = (selection_signal * 0.7) + (rating_normalized * 0.3)
        
        return float(target)
    
    def analyze(self, city: str = 'Lahore', 
                limit: Optional[int] = None) -> Dict:
        """
        Analyze training data from real itineraries.
        
        Args:
            city: City to analyze
            limit: Maximum number of itineraries to process
        
        Returns:
            Dictionary with analysis report
        """
        self._log(f"Analyzing itinerary data for {city}...")
        
        # Get itineraries
        query = Itinerary.objects.filter(city=city)
        if limit:
            query = query[:limit]
        
        itineraries = list(query)
        self._log(f"  Found {len(itineraries)} itineraries")
        
        if not itineraries:
            self._log("  [WARN] No itineraries found - will use synthetic data")
            return self._make_empty_report()
        
        # Process each itinerary
        samples = []
        all_places = {p.id: p for p in Place.objects.filter(city=city)}
        
        for itinerary in itineraries:
            trip_days_count = (itinerary.end_date - itinerary.start_date).days + 1
            
            # Extract ALL selected place IDs across entire trip
            all_selected_place_ids = set()
            for day_data in itinerary.days:
                if isinstance(day_data, dict) and 'items' in day_data:
                    for item in day_data['items']:
                        if isinstance(item, dict) and 'place_id' in item:
                            all_selected_place_ids.add(item['place_id'])
            
            # For each day in the itinerary
            for day_idx, day_data in enumerate(itinerary.days):
                if not isinstance(day_data, dict) or 'items' not in day_data:
                    continue
                
                # Get places selected specifically on THIS day
                day_selected_ids = set()
                for item in day_data['items']:
                    if isinstance(item, dict) and 'place_id' in item:
                        day_selected_ids.add(item['place_id'])
                
                # Create samples for each place in the database
                for place_id, place in all_places.items():
                    was_selected_today = place_id in day_selected_ids
                    
                    sample = DataSample(
                        # User features
                        user_mood=itinerary.mood or 'RELAXING',
                        user_budget=itinerary.budget_level,
                        user_pace=itinerary.pace,
                        user_interests=itinerary.interests or [],
                        
                        # Place features
                        place_name=place.name,
                        place_category=place.category,
                        place_rating=place.average_rating,
                        place_budget_level=place.budget_level,
                        place_visit_minutes=place.estimated_visit_minutes,
                        place_tags=place.tags or [],
                        place_ideal_start=place.ideal_start_hour,
                        place_ideal_end=place.ideal_end_hour,
                        
                        # Geographic
                        place_latitude=place.latitude,
                        place_longitude=place.longitude,
                        hotel_latitude=0.0,
                        hotel_longitude=0.0,
                        distance_km=0.0,
                        
                        # Contextual
                        trip_day=day_idx,
                        trip_total_days=trip_days_count,
                        
                        # Target: Meaningful ranking signal
                        was_selected=was_selected_today,
                        selection_quality=self._create_target_score(
                            was_selected=was_selected_today,
                            place_rating=place.average_rating
                        )
                    )
                    samples.append(sample)
        
        self.samples = samples
        
        # Create report
        positive = sum(1 for s in samples if s.was_selected)
        negative = len(samples) - positive
        
        report = {
            'data_overview': {
                'total_itineraries': len(itineraries),
                'total_training_samples': len(samples),
                'positive_samples': positive,
                'negative_samples': negative,
            },
            'recommendation': self._make_recommendation(positive, negative),
        }
        
        self._log(f"  [OK] Analysis complete: {len(samples)} samples")
        self._log(f"    - Positive: {positive}, Negative: {negative}")
        
        return report
    
    def _make_empty_report(self) -> Dict:
        """Create empty report for no data"""
        return {
            'data_overview': {
                'total_itineraries': 0,
                'total_training_samples': 0,
                'positive_samples': 0,
                'negative_samples': 0,
            },
            'recommendation': 'INSUFFICIENT_DATA - No itineraries found. Will generate synthetic data.',
        }
    
    def _make_recommendation(self, positive: int, negative: int) -> str:
        """Make data quality recommendation"""
        total = positive + negative
        
        if total < 100:
            return "INSUFFICIENT_DATA - Less than 100 samples"
        
        ratio = positive / max(negative, 1) if negative > 0 else 0
        if ratio < 0.1 or ratio > 10:
            return "IMBALANCED_DATA - Class imbalance > 10:1"
        
        return "DATA_READY - Sufficient data for training"
    
    def generate_synthetic_data(self, samples_per_combination: int = 10) -> List[DataSample]:
        """
        Generate synthetic training data for testing.
        Creates diverse combinations of user and place features.
        
        Args:
            samples_per_combination: How many samples per user-place combo
        
        Returns:
            List of synthetic DataSample objects
        """
        self._log(f"Generating {samples_per_combination} synthetic samples...")
        
        synthetic_samples = []
        
        moods = list(self.MOOD_TO_ID.keys())
        budgets = list(self.BUDGET_TO_ID.keys())
        paces = list(self.PACE_TO_ID.keys())
        categories = list(self.CATEGORY_TO_ID.keys())
        
        # Get real places or create synthetic ones
        places = list(Place.objects.all()[:100])
        
        if not places:
            self._log("  No places in database - creating synthetic places")
            places = self._create_synthetic_places()
        
        # Generate combinations
        for mood in moods:
            for budget in budgets:
                for pace in paces:
                    for place in places[:50]:  # Limit place count
                        for i in range(samples_per_combination):
                            # Randomize some properties
                            was_selected = random.random() < 0.3  # 30% selected
                            
                            sample = DataSample(
                                user_mood=mood,
                                user_budget=budget,
                                user_pace=pace,
                                user_interests=[
                                    random.choice(['history', 'culture', 'food', 'nature', 'shopping'])
                                    for _ in range(random.randint(0, 3))
                                ],
                                place_name=place.name if place else f"Place_{i}",
                                place_category=place.category if place else random.choice(categories),
                                place_rating=place.average_rating if place else random.uniform(2.5, 5.0),
                                place_budget_level=place.budget_level if place else budget,
                                place_visit_minutes=place.estimated_visit_minutes if place else random.choice([30, 60, 90, 120]),
                                place_tags=place.tags if place else [],
                                place_ideal_start=place.ideal_start_hour if place else random.randint(8, 11),
                                place_ideal_end=place.ideal_end_hour if place else random.randint(17, 20),
                                place_latitude=place.latitude if place else random.uniform(31.5, 31.6),
                                place_longitude=place.longitude if place else random.uniform(74.3, 74.4),
                                hotel_latitude=31.5,
                                hotel_longitude=74.3,
                                distance_km=random.uniform(0.5, 30),
                                trip_day=random.randint(0, 7),
                                trip_total_days=random.randint(3, 14),
                                was_selected=was_selected,
                                selection_quality=random.uniform(0.6, 1.0) if was_selected else random.uniform(0.1, 0.4),
                            )
                            synthetic_samples.append(sample)
        
        self._log(f"  [OK] Generated {len(synthetic_samples)} synthetic samples")
        return synthetic_samples
    
    def _create_synthetic_places(self) -> List:
        """Create synthetic place objects for testing"""
        places = []
        categories = list(self.CATEGORY_TO_ID.keys())
        
        for i in range(50):
            place = type('Place', (), {
                'id': i,
                'name': f"Synthetic Place {i}",
                'category': random.choice(categories),
                'average_rating': random.uniform(2.5, 5.0),
                'budget_level': random.choice(['LOW', 'MEDIUM', 'LUXURY']),
                'estimated_visit_minutes': random.choice([30, 60, 90, 120]),
                'tags': [random.choice(['food', 'culture', 'history', 'nature'])],
                'ideal_start_hour': random.randint(8, 11),
                'ideal_end_hour': random.randint(17, 20),
                'latitude': random.uniform(31.5, 31.6),
                'longitude': random.uniform(74.3, 74.4),
            })()
            places.append(place)
        
        return places
