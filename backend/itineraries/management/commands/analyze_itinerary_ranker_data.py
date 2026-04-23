"""
Django Management Command: analyze_itinerary_ranker_data

Purpose:
    Analyze available data for training the AI Itinerary Ranker model.
    This command COLLECTS and ANALYZES data without training or saving.

Features:
    1. Analyze existing itineraries from users
    2. Extract training samples from selected places
    3. Build feature engineering functions
    4. Assess data quality and completeness
    5. Generate comprehensive statistics
    6. Identify data gaps

Usage:
    python manage.py analyze_itinerary_ranker_data
    python manage.py analyze_itinerary_ranker_data --verbose
    python manage.py analyze_itinerary_ranker_data --city Lahore
    python manage.py analyze_itinerary_ranker_data --sample 100
"""

import logging
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from math import radians, sin, cos, sqrt, atan2

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class DataSample:
    """Single training sample for ranker model"""
    # User context
    user_id: int
    user_mood: str
    user_budget: str
    user_interests: List[str]
    user_pace: str
    
    # Place features
    place_id: int
    place_name: str
    place_category: str
    place_tags: List[str]
    place_rating: float
    place_budget_level: str
    place_visit_minutes: int
    
    # Temporal context
    trip_day: int
    trip_total_days: int
    place_ideal_start: int
    place_ideal_end: int
    
    # Geographic
    place_latitude: float
    place_longitude: float
    hotel_latitude: Optional[float] = None
    hotel_longitude: Optional[float] = None
    distance_km: float = 0.0
    
    # Target variable
    was_selected: bool = True  # True=in itinerary, False=not selected
    selection_quality: float = 1.0  # 1.0=high quality place, derived from rating
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class RankerDataAnalyzer:
    """Analyzes and prepares data for ranker model training"""
    
    # Mood to ID mapping (from ai_ranker_service.py)
    MOOD_TO_ID = {
        'RELAXING': 0, 'SPIRITUAL': 1, 'HISTORICAL': 2, 'FOODIE': 3,
        'FUN': 4, 'SHOPPING': 5, 'NATURE': 6, 'ROMANTIC': 7, 'FAMILY': 8
    }
    
    # Budget to ID mapping
    BUDGET_TO_ID = {
        'LOW': 0, 'MEDIUM': 1, 'LUXURY': 2
    }
    
    # Category to ID mapping
    CATEGORY_TO_ID = {
        'religious': 0, 'history': 1, 'culture': 2, 'food': 3, 
        'nature': 4, 'shopping': 5, 'modern': 6, 'other': 7
    }
    
    def __init__(self, verbose: bool = False):
        """Initialize analyzer"""
        self.verbose = verbose
        self.samples: List[DataSample] = []
        self.stats = {
            'total_itineraries': 0,
            'total_users': 0,
            'total_places': 0,
            'total_days': 0,
            'total_samples': 0,
            'positive_samples': 0,
            'negative_samples': 0,
            'data_quality_issues': [],
        }
        self._log(f"Initialized RankerDataAnalyzer (verbose={verbose})")
    
    def _log(self, msg: str, level: str = 'info'):
        """Log message"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        if level == 'error':
            logger.error(msg)
        elif level == 'warning':
            logger.warning(msg)
        else:
            logger.info(msg)
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two lat/lon points"""
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        
        R = 6371  # Earth radius in km
        
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def analyze(self, city: str = 'Lahore', limit: Optional[int] = None) -> Dict:
        """
        Analyze data from database
        
        Args:
            city: City to analyze (default: Lahore)
            limit: Maximum number of itineraries to process (None=all)
        
        Returns:
            Dictionary with analysis results
        """
        from itineraries.models import Place, Itinerary
        
        self._log(f"Starting analysis for {city}...")
        
        # -- Step 1: Load places ----------------------------------------------
        self._log("Step 1: Loading places database...")
        places_qs = Place.objects.filter(city=city)
        places_by_id = {}
        places_data = []
        
        for place in places_qs:
            places_by_id[place.id] = place
            places_data.append({
                'id': place.id,
                'name': place.name,
                'category': place.category,
                'tags': place.tags or [],
                'rating': place.average_rating,
                'budget': place.budget_level,
                'visit_minutes': place.estimated_visit_minutes,
                'lat': place.latitude,
                'lon': place.longitude,
                'start_hour': place.ideal_start_hour,
                'end_hour': place.ideal_end_hour,
            })
        
        stats_places = {
            'total': places_qs.count(),
            'by_category': dict(places_qs.values_list('category').annotate(count=Count('id'))),
            'by_budget': dict(places_qs.values_list('budget_level').annotate(count=Count('id'))),
            'avg_rating': places_qs.aggregate(Avg('average_rating'))['average_rating__avg'] or 0.0,
            'with_rating': places_qs.exclude(average_rating=0).count(),
        }
        
        self._log(f"  [OK] Loaded {stats_places['total']} places")
        self._log(f"    - Categories: {stats_places['by_category']}")
        self._log(f"    - Budget levels: {stats_places['by_budget']}")
        self._log(f"    - Avg rating: {stats_places['avg_rating']:.2f}")
        
        # -- Step 2: Load itineraries ----------------------------------------
        self._log("Step 2: Loading itineraries...")
        itineraries_qs = Itinerary.objects.filter(city=city, saved=True).select_related('user')
        if limit:
            itineraries_qs = itineraries_qs[:limit]
        
        self.stats['total_itineraries'] = itineraries_qs.count()
        self.stats['total_users'] = itineraries_qs.values('user').distinct().count()
        
        self._log(f"  [OK] Loaded {self.stats['total_itineraries']} itineraries from {self.stats['total_users']} users")
        
        # -- Step 3: Extract training samples --------------------------------
        self._log("Step 3: Extracting training samples...")
        
        place_selection_count = {}  # Track how many times each place was selected
        
        for itinerary in itineraries_qs:
            trip_num_days = (itinerary.end_date - itinerary.start_date).days + 1
            self.stats['total_days'] += trip_num_days
            
            # Parse days structure (list of {date, title, items: [places]})
            days_data = itinerary.days or []
            
            if not days_data:
                self._log(f"  [WARN] Itinerary {itinerary.id}: No days data", level='warning')
                self.stats['data_quality_issues'].append(f"Itinerary {itinerary.id}: empty days structure")
                continue
            
            # Collect selected place IDs for this itinerary
            selected_place_ids = set()
            
            for day_idx, day in enumerate(days_data):
                items = day.get('items', []) if isinstance(day, dict) else []
                
                for item in items:
                    # Item structure: {place_id, name, category, ...}
                    # Try both 'id' and 'place_id' for compatibility
                    place_id = item.get('place_id') or item.get('id')
                    if place_id and place_id in places_by_id:
                        selected_place_ids.add(place_id)
                        place_selection_count[place_id] = place_selection_count.get(place_id, 0) + 1
            
            if not selected_place_ids:
                self._log(f"  [WARN] Itinerary {itinerary.id}: No valid places found in days", level='warning')
                self.stats['data_quality_issues'].append(f"Itinerary {itinerary.id}: no valid places in days")
                continue
            
            # Create training samples: both selected AND not-selected places
            interests = itinerary.interests or []
            
            for place in places_qs:
                was_selected = place.id in selected_place_ids
                
                # Derive quality score from place rating
                quality_score = (place.average_rating / 5.0) if place.average_rating > 0 else 0.5
                
                sample = DataSample(
                    # User context
                    user_id=itinerary.user.id,
                    user_mood=itinerary.mood or 'RELAXING',
                    user_budget=itinerary.budget_level,
                    user_interests=interests,
                    user_pace=itinerary.pace,
                    
                    # Place features
                    place_id=place.id,
                    place_name=place.name,
                    place_category=place.category,
                    place_tags=place.tags or [],
                    place_rating=place.average_rating,
                    place_budget_level=place.budget_level,
                    place_visit_minutes=place.estimated_visit_minutes,
                    
                    # Temporal
                    trip_day=1,  # Simplified: could be enhanced with actual day
                    trip_total_days=trip_num_days,
                    place_ideal_start=place.ideal_start_hour,
                    place_ideal_end=place.ideal_end_hour,
                    
                    # Geographic
                    place_latitude=place.latitude,
                    place_longitude=place.longitude,
                    distance_km=0.0,  # Will calculate hotel distance in future
                    
                    # Target
                    was_selected=was_selected,
                    selection_quality=quality_score,
                )
                
                self.samples.append(sample)
            
            if len(self.samples) % 500 == 0 and len(self.samples) > 0:
                self._log(f"  → Processed {len(self.samples)} samples so far...")
        
        # -- Step 4: Calculate statistics ------------------------------------
        self._log("Step 4: Calculating statistics...")
        
        positive_count = sum(1 for s in self.samples if s.was_selected)
        negative_count = len(self.samples) - positive_count
        
        self.stats['total_places'] = len(places_by_id)
        self.stats['total_samples'] = len(self.samples)
        self.stats['positive_samples'] = positive_count
        self.stats['negative_samples'] = negative_count
        
        # -- Step 5: Analyze feature engineering factors ----------------------
        self._log("Step 5: Analyzing features...")
        
        feature_stats = self._analyze_features()
        
        # -- Step 6: Assess data quality --------------------------------------
        self._log("Step 6: Assessing data quality...")
        
        quality_report = self._assess_data_quality(place_selection_count)
        
        # -- Build final report ----------------------------------------------
        report = {
            'timestamp': datetime.now().isoformat(),
            'city': city,
            'data_overview': {
                'total_itineraries': self.stats['total_itineraries'],
                'total_users': self.stats['total_users'],
                'total_places': self.stats['total_places'],
                'total_training_samples': self.stats['total_samples'],
                'positive_samples': self.stats['positive_samples'],
                'negative_samples': self.stats['negative_samples'],
                'class_balance': f"{positive_count}/{negative_count}" if negative_count > 0 else "N/A",
                'class_ratio': f"{positive_count/(positive_count+negative_count):.2%}" if len(self.samples) > 0 else "N/A",
            },
            'places_stats': stats_places,
            'feature_analysis': feature_stats,
            'data_quality': quality_report,
            'place_popularity': {
                'most_selected': self._get_most_selected_places(place_selection_count, 10),
                'least_selected': self._get_least_selected_places(place_selection_count, 10),
                'never_selected': len([p for p in places_by_id if p not in place_selection_count]),
            },
            'data_issues': self.stats['data_quality_issues'][:20],  # First 20
            'recommendation': self._generate_recommendation(positive_count, negative_count),
        }
        
        return report
    
    def _analyze_features(self) -> Dict:
        """Analyze feature distributions"""
        if not self.samples:
            return {'error': 'No samples to analyze'}
        
        features = {
            'moods': {},
            'budgets': {},
            'categories': {},
            'rating_distribution': {
                'min': min((s.place_rating for s in self.samples), default=0),
                'max': max((s.place_rating for s in self.samples), default=5),
                'mean': np.mean([s.place_rating for s in self.samples]),
                'median': np.median([s.place_rating for s in self.samples]),
            },
            'visit_minutes': {
                'min': min((s.place_visit_minutes for s in self.samples), default=0),
                'max': max((s.place_visit_minutes for s in self.samples), default=0),
                'mean': np.mean([s.place_visit_minutes for s in self.samples]),
            },
            'categorical_coverage': {
                'moods': len(set(s.user_mood for s in self.samples)),
                'budgets': len(set(s.user_budget for s in self.samples)),
                'categories': len(set(s.place_category for s in self.samples)),
                'interests': len(set(interest for s in self.samples for interest in s.user_interests)),
            }
        }
        
        # Count mood distribution
        for sample in self.samples:
            mood = sample.user_mood
            features['moods'][mood] = features['moods'].get(mood, 0) + 1
        
        # Count budget distribution
        for sample in self.samples:
            budget = sample.user_budget
            features['budgets'][budget] = features['budgets'].get(budget, 0) + 1
        
        # Count category distribution
        for sample in self.samples:
            cat = sample.place_category
            features['categories'][cat] = features['categories'].get(cat, 0) + 1
        
        return features
    
    def _assess_data_quality(self, place_selection_count: Dict) -> Dict:
        """Assess quality of collected data"""
        if not self.samples:
            return {'error': 'No samples'}
        
        quality = {
            'total_samples': len(self.samples),
            'valid_samples': len([s for s in self.samples if s.place_id and s.user_id]),
            'missing_rating': len([s for s in self.samples if s.place_rating == 0]),
            'missing_interests': len([s for s in self.samples if not s.user_interests]),
            'missing_mood': len([s for s in self.samples if not s.user_mood]),
        }
        
        quality['data_completeness'] = {
            'rating': f"{(quality['total_samples'] - quality['missing_rating']) / quality['total_samples']:.1%}",
            'interests': f"{(quality['total_samples'] - quality['missing_interests']) / quality['total_samples']:.1%}",
            'mood': f"{(quality['total_samples'] - quality['missing_mood']) / quality['total_samples']:.1%}",
        }
        
        quality['readiness'] = 'READY' if quality['valid_samples'] > 100 else 'INSUFFICIENT'
        
        return quality
    
    def _get_most_selected_places(self, place_count: Dict, top_n: int = 10) -> List[Tuple]:
        """Get most frequently selected places"""
        from itineraries.models import Place
        
        sorted_places = sorted(place_count.items(), key=lambda x: x[1], reverse=True)[:top_n]
        result = []
        
        for place_id, count in sorted_places:
            try:
                place = Place.objects.get(id=place_id)
                result.append((place.name, count, place.average_rating))
            except Place.DoesNotExist:
                pass
        
        return result
    
    def _get_least_selected_places(self, place_count: Dict, top_n: int = 10) -> List[Tuple]:
        """Get least frequently selected places"""
        from itineraries.models import Place
        
        sorted_places = sorted(place_count.items(), key=lambda x: x[1])[:top_n]
        result = []
        
        for place_id, count in sorted_places:
            try:
                place = Place.objects.get(id=place_id)
                result.append((place.name, count, place.average_rating))
            except Place.DoesNotExist:
                pass
        
        return result
    
    def _generate_recommendation(self, positive: int, negative: int) -> str:
        """Generate actionable recommendation"""
        total = positive + negative
        
        if total < 100:
            return "[WARN] INSUFFICIENT DATA: Need at least 100 training samples. Current: {}. Generate more itineraries.".format(total)
        elif positive < 10:
            return "[WARN] IMBALANCED: Too few positive examples ({}). Need at least 50 selected places across itineraries.".format(positive)
        elif (positive / total) < 0.1:
            return "[WARN] SKEWED: Class ratio too imbalanced ({:.1%} positive). Model will struggle with minority class.".format(positive/total)
        else:
            return f"[OK] READY FOR TRAINING: {total} samples ({positive} positive, {negative} negative) with {positive/total:.1%} positive ratio."


class Command(BaseCommand):
    """Django Management Command"""
    
    help = "Analyze available data for training AI Itinerary Ranker"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output with detailed logging'
        )
        parser.add_argument(
            '--city',
            type=str,
            default='Lahore',
            help='City to analyze (default: Lahore)'
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=None,
            help='Maximum number of itineraries to process (default: all)'
        )
    
    def handle(self, *args, **options):
        """Execute command"""
        verbose = options.get('verbose', False)
        city = options.get('city', 'Lahore')
        limit = options.get('sample', None)
        
        self.stdout.write("=" * 80)
        self.stdout.write(f"AI ITINERARY RANKER - DATA ANALYSIS REPORT")
        self.stdout.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        # Initialize analyzer
        analyzer = RankerDataAnalyzer(verbose=verbose)
        
        # Run analysis
        try:
            report = analyzer.analyze(city=city, limit=limit)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: {str(e)}"))
            logger.exception("Analysis failed")
            raise CommandError(str(e))
        
        # -- Output Report ----------------------------------------------------
        self._print_section("DATA OVERVIEW", report['data_overview'])
        
        self._print_section("PLACES DATABASE", report['places_stats'])
        
        self._print_section("FEATURE ANALYSIS", report['feature_analysis'])
        
        self._print_section("DATA QUALITY", report['data_quality'])
        
        # Popular places
        self.stdout.write(self.style.HTTP_INFO("\n[CHART] PLACE POPULARITY"))
        self.stdout.write("-" * 80)
        
        most_selected = report['place_popularity']['most_selected']
        if most_selected:
            self.stdout.write("\nMost Selected Places:")
            for name, count, rating in most_selected[:5]:
                self.stdout.write(f"  * {name} - {count}x selected (rating: {rating:.1f}[STAR])")
        
        least_selected = report['place_popularity']['least_selected']
        if least_selected:
            self.stdout.write("\nLeast Selected Places:")
            for name, count, rating in least_selected[:5]:
                self.stdout.write(f"  * {name} - {count}x selected (rating: {rating:.1f}[STAR])")
        
        self.stdout.write(f"\nNever Selected: {report['place_popularity']['never_selected']} places")
        
        # Issues
        if report['data_issues']:
            self.stdout.write(self.style.WARNING("\n[DATA QUALITY ISSUES]"))
            self.stdout.write("-" * 80)
            for i, issue in enumerate(report['data_issues'][:10], 1):
                self.stdout.write(f"  {i}. {issue}")
            if len(report['data_issues']) > 10:
                self.stdout.write(f"  ... and {len(report['data_issues']) - 10} more issues")
        
        # Recommendation
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(report['recommendation']))
        self.stdout.write("=" * 80)
        
        # Save report as JSON logs
        self._save_report(report)
    
    def _print_section(self, title: str, data: Dict):
        """Print section of report"""
        self.stdout.write(self.style.HTTP_INFO(f"\n{title}"))
        self.stdout.write("-" * 80)
        
        for key, value in data.items():
            if isinstance(value, dict):
                self.stdout.write(f"{key}:")
                for k, v in value.items():
                    self.stdout.write(f"  * {k}: {v}")
            elif isinstance(value, list):
                self.stdout.write(f"{key}: {', '.join(map(str, value[:5]))}")
                if len(value) > 5:
                    self.stdout.write(f"  ... and {len(value) - 5} more")
            else:
                self.stdout.write(f"{key}: {value}")
    
    def _save_report(self, report: Dict):
        """Save report as JSON"""
        import os
        from pathlib import Path
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = log_dir / f"ranker_data_analysis_{timestamp}.json"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(f"\n✅ Report saved to: {filepath}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[WARN] Could not save report: {e}"))
