"""
Unified AI Itinerary Service

Orchestrates all three AI layers (emotion detection, ML ranking, LLM enhancement)
and provides fallback to rule-based system on any failure.

This service maintains 100% backward compatibility with existing API contracts.
"""

import logging
import json
from typing import Dict, List, Optional
from dataclasses import asdict
from datetime import datetime

from .ai_emotion_service import AIEmotionDetectionService, TravelloMood
from .ai_ranker_service import LearningToRankService, RankedPlace
from .ai_llm_service import LLMEnhancementService
from .generator import generate_itinerary as rule_based_generate

logger = logging.getLogger(__name__)


class AIItineraryService:
    """
    Main AI service orchestrating emotion detection + ML ranking + LLM enhancement.
    
    Key Design:
    - All three layers are optional and independently fallback-able
    - If any AI component fails, falls back to rule-based system
    - Maintains identical API contract with existing system
    - All predictions logged for monitoring and future retraining
    """
    
    def __init__(
        self,
        emotion_service: Optional[AIEmotionDetectionService] = None,
        ranker_service: Optional[LearningToRankService] = None,
        llm_service: Optional[LLMEnhancementService] = None,
        enable_emotion_detection: bool = True,
        enable_ml_ranking: bool = True,
        enable_llm_enhancement: bool = False,
        fallback_confidence_threshold: float = 0.6,
        enable_fallback_hybrid: bool = True
    ):
        """
        Initialize unified AI itinerary service.
        
        Args:
            emotion_service: Emotion detection service (auto-created if None)
            ranker_service: ML ranking service (auto-created if None)
            llm_service: LLM enhancement service (auto-created if None)
            enable_emotion_detection: Enable Layer 1
            enable_ml_ranking: Enable Layer 2
            enable_llm_enhancement: Enable Layer 3 (optional)
            fallback_confidence_threshold: Confidence threshold for hybrid fallback
            enable_fallback_hybrid: If True, use hybrid scoring when confidence low
        """
        self.emotion_service = emotion_service or AIEmotionDetectionService()
        
        # Initialize ranker with trained model if available
        if ranker_service is None:
            import os
            from django.conf import settings
            # Try to load trained model
            model_path = os.path.join(
                settings.BASE_DIR, 
                'ml_models', 
                'itinerary_ranker.pkl'
            )
            self.ranker_service = LearningToRankService(model_path=model_path)
        else:
            self.ranker_service = ranker_service
        
        self.llm_service = llm_service or LLMEnhancementService()
        
        self.enable_emotion_detection = enable_emotion_detection
        self.enable_ml_ranking = enable_ml_ranking
        self.enable_llm_enhancement = enable_llm_enhancement
        self.fallback_confidence_threshold = fallback_confidence_threshold
        self.enable_fallback_hybrid = enable_fallback_hybrid
        
        # Metrics tracking
        self.last_generation_log = None
    
    def generate_itinerary_ai(
        self,
        user_id: str,
        trip_params: Dict,
        user: Optional[object] = None,
        places_database: Optional[List[Dict]] = None,
        preferences_text: str = ""
    ) -> Dict:
        """
        Generate itinerary using full AI pipeline.
        
        Maintains identical response format as rule-based system for backward compatibility.
        
        Args:
            user_id: User ID
            trip_params: Trip parameters dict:
                - mood: user selected mood (e.g., "RELAXING")
                - interests: list of interests
                - budget: budget level ("low", "medium", "high")
                - num_days: number of days
                - trip_start_date: start date
                - city: destination city
                - (optional) trip_end_date: end date
            user: User object (for logging)
            places_database: List of available places (will be fetched if None)
            preferences_text: User preferences text for emotion detection
            
        Returns:
            Itinerary dict in same format as rule-based system
        """
        
        # Start logging
        generation_start_time = datetime.now()
        generation_log = {
            'user_id': user_id,
            'generation_time': generation_start_time.isoformat(),
            'trip_params': trip_params,
            'stages': {}
        }
        
        try:
            logger.info(f"Starting AI itinerary generation for user {user_id}")
            
            # ==================== LAYER 1: EMOTION DETECTION ====================
            final_mood = trip_params.get('mood', 'RELAXING')
            emotion_log = {}
            
            if self.enable_emotion_detection:
                try:
                    final_mood = self.emotion_service.get_final_mood(
                        manual_mood=trip_params.get('mood'),
                        user_text=preferences_text,
                        confidence_threshold=self.fallback_confidence_threshold
                    )
                    emotion_log = {
                        'status': 'success',
                        'final_mood': final_mood.value if isinstance(final_mood, TravelloMood) else final_mood,
                    }
                    logger.debug(f"Layer 1 (Emotion): Detected mood = {final_mood}")
                except Exception as e:
                    logger.warning(f"Layer 1 (Emotion) failed: {e}. Using manual mood.")
                    emotion_log = {'status': 'failed', 'error': str(e)}
                    final_mood = trip_params.get('mood', 'RELAXING')
            
            generation_log['stages']['emotion_detection'] = emotion_log
            
            # ==================== LAYER 2: ML RANKING ====================
            ranking_log = {'status': 'not_enabled'}
            
            if self.enable_ml_ranking and self.ranker_service and self.ranker_service.model:
                try:
                    # Get or fetch places database
                    if places_database is None:
                        places_database = self._get_places_database(
                            city=trip_params.get('city'),
                            interests=trip_params.get('interests', [])
                        )
                    
                    # Generate itinerary with ML ranking
                    itinerary = self._generate_with_ml_ranking(
                        user_id=user_id,
                        final_mood=final_mood,
                        trip_params=trip_params,
                        places_database=places_database
                    )
                    
                    ranking_log = {
                        'status': 'success',
                        'model_confidence': self.ranker_service.last_confidence,
                        'inference_latency_ms': self.ranker_service.inference_latency_ms,
                    }
                    logger.debug(
                        f"Layer 2 (ML Ranking): Generated itinerary with "
                        f"confidence={ranking_log['model_confidence']:.2f}"
                    )
                    
                except Exception as e:
                    logger.warning(f"Layer 2 (ML Ranking) failed: {e}. Using rule-based fallback.")
                    ranking_log = {'status': 'failed', 'error': str(e)}
                    itinerary = None
            else:
                itinerary = None
            
            generation_log['stages']['ml_ranking'] = ranking_log
            
            # ==================== FALLBACK: RULE-BASED IF ML FAILED ====================
            if itinerary is None:
                logger.info("Falling back to rule-based itinerary generation")
                itinerary = self._fallback_to_rule_based(
                    final_mood=final_mood,
                    trip_params=trip_params,
                    user=user
                )
                generation_log['stages']['fallback_used'] = True
            else:
                generation_log['stages']['fallback_used'] = False
            
            # ==================== LAYER 3: LLM ENHANCEMENT ====================
            llm_log = {'status': 'not_enabled'}
            
            if self.enable_llm_enhancement and itinerary:
                try:
                    itinerary = self.llm_service.enhance_itinerary(itinerary)
                    llm_log = {'status': 'success'}
                    logger.debug("Layer 3 (LLM): Enhanced itinerary descriptions")
                except Exception as e:
                    logger.warning(f"Layer 3 (LLM) failed: {e}. Continuing with unenhanced itinerary.")
                    llm_log = {'status': 'failed', 'error': str(e)}
            
            generation_log['stages']['llm_enhancement'] = llm_log
            
            # ==================== LOGGING & MONITORING ====================
            generation_log['final_mood'] = final_mood.value if isinstance(final_mood, TravelloMood) else final_mood
            generation_log['status'] = 'success'
            generation_log['generation_latency_ms'] = (datetime.now() - generation_start_time).total_seconds() * 1000
            
            self.last_generation_log = generation_log
            self._log_generation_to_database(generation_log, itinerary)
            
            logger.info(
                f"AI itinerary generation complete for user {user_id}. "
                f"Latency: {generation_log['generation_latency_ms']:.1f}ms"
            )
            
            return itinerary
            
        except Exception as e:
            # Last resort: return rule-based itinerary
            logger.error(f"Unexpected error in AI pipeline: {e}. Using rule-based fallback.")
            generation_log['status'] = 'error'
            generation_log['error'] = str(e)
            
            self.last_generation_log = generation_log
            
            return self._fallback_to_rule_based(
                final_mood=trip_params.get('mood', 'RELAXING'),
                trip_params=trip_params,
                user=user
            )
    
    def _generate_with_ml_ranking(
        self,
        user_id: str,
        final_mood,
        trip_params: Dict,
        places_database: List[Dict]
    ) -> Dict:
        """
        Generate itinerary using ML ranking for place selection.
        
        Strategy:
        1. For each day, get candidate places
        2. Rank using ML model
        3. Apply diversity constraints
        4. Return in same format as rule-based system
        """
        from .models import Itinerary
        
        itinerary_data = {
            'mood': final_mood.value if isinstance(final_mood, TravelloMood) else final_mood,
            'interests': trip_params.get('interests', []),
            'budget': trip_params.get('budget'),
            'days': []
        }
        
        num_days = trip_params.get('num_days', 1)
        user_interests = trip_params.get('interests', [])
        user_budget = trip_params.get('budget', 'medium')
        trip_start_date = trip_params.get('trip_start_date')
        
        previously_visited = []  # Track places used in earlier days
        
        for day_idx in range(num_days):
            day_date = self._calculate_day_date(trip_start_date, day_idx)
            
            # Filter candidates for this day (e.g., by time, distance)
            candidates = self._get_candidate_places(
                places_database=places_database,
                interests=user_interests,
                budget=user_budget,
                previously_visited=previously_visited,
                max_candidates=15
            )
            
            # Rank using ML model
            ranked = self.ranker_service.rank_places(
                user_mood=final_mood.value if isinstance(final_mood, TravelloMood) else final_mood,
                candidate_places=candidates,
                user_interests=user_interests,
                user_budget=user_budget,
                user_pace=trip_params.get('pace', 'BALANCED'),
                day_index=day_idx,
                trip_total_days=num_days,
                hotel_location=trip_params.get('hotel_location'),
                previously_visited=previously_visited,
                use_ml=self.enable_ml_ranking
            )
            
            # Select top places for this day
            day_places = [
                self._ranked_place_to_dict(rp)
                for rp in ranked[:5]  # Top 5 places per day
            ]
            
            # Track visited places
            previously_visited.extend([p.get('id') for p in day_places])
            
            itinerary_data['days'].append({
                'date': day_date.isoformat() if day_date else None,
                'places': day_places,
                'day_index': day_idx,
            })
        
        return itinerary_data
    
    def _fallback_to_rule_based(
        self,
        final_mood,
        trip_params: Dict,
        user: Optional[object] = None
    ) -> Dict:
        """
        Fallback to existing rule-based itinerary generation.
        Ensures system always returns valid itinerary.
        """
        logger.info("Using rule-based itinerary generation system")
        
        try:
            # Call existing rule-based generator
            itinerary = rule_based_generate(
                user=user,
                num_days=trip_params.get('num_days', 1),
                mood=final_mood.value if isinstance(final_mood, TravelloMood) else final_mood,
                interests=trip_params.get('interests', []),
                budget=trip_params.get('budget', 'medium'),
                trip_start_date=trip_params.get('trip_start_date')
            )
            
            return itinerary
            
        except Exception as e:
            logger.error(f"Even rule-based fallback failed: {e}")
            # Return minimal valid itinerary structure
            return {
                'mood': final_mood.value if isinstance(final_mood, TravelloMood) else final_mood,
                'interests': trip_params.get('interests', []),
                'budget': trip_params.get('budget'),
                'days': [],
                'error': 'Failed to generate itinerary'
            }
    
    def _get_places_database(self, city: str = "", interests: List[str] = None) -> List[Dict]:
        """Fetch places from database"""
        try:
            from .models import Place
            
            # Query all places (in production, would filter by city/interests)
            places = Place.objects.all().values()
            return list(places)
        except Exception as e:
            logger.error(f"Failed to fetch places database: {e}")
            return []
    
    def _get_candidate_places(
        self,
        places_database: List[Dict],
        interests: List[str],
        budget: str,
        previously_visited: List[str],
        max_candidates: int = 15
    ) -> List[Dict]:
        """Select candidate places for ranking"""
        # Filter: exclude previously visited
        candidates = [p for p in places_database if p.get('id') not in previously_visited]
        
        # Filter: budget compatibility
        budget_levels = {'low': [1], 'medium': [1, 2], 'high': [2, 3], 'luxury': [3, 4]}
        allowed_price_levels = budget_levels.get(budget.lower(), [1, 2])
        candidates = [p for p in candidates if p.get('price_level', 2) in allowed_price_levels]
        
        # Sort by distance/rating and return top N
        candidates = sorted(
            candidates,
            key=lambda p: (p.get('rating', 0), -p.get('popularity_score', 0)),
            reverse=True
        )[:max_candidates]
        
        return candidates
    
    @staticmethod
    def _ranked_place_to_dict(ranked_place: RankedPlace) -> Dict:
        """Convert RankedPlace object to dict"""
        return {
            'id': ranked_place.place_id,
            'name': ranked_place.place_name,
            'ml_score': ranked_place.score,
            'ml_confidence': ranked_place.confidence,
            'ranked_by_ml': ranked_place.is_ml_ranked,
        }
    
    @staticmethod
    def _calculate_day_date(trip_start_date, day_idx: int):
        """Calculate date for a given day in trip"""
        if not trip_start_date:
            return None
        
        from datetime import datetime, timedelta
        
        if isinstance(trip_start_date, str):
            trip_start_date = datetime.fromisoformat(trip_start_date)
        
        return trip_start_date + timedelta(days=day_idx)
    
    def _log_generation_to_database(self, generation_log: Dict, itinerary: Dict):
        """Log generation event for monitoring and retraining"""
        try:
            from .models import AIGenerationLog
            
            # Store log in database
            log_entry = AIGenerationLog(
                user_id=generation_log.get('user_id'),
                trip_params=json.dumps(generation_log.get('trip_params', {})),
                final_mood=generation_log.get('final_mood'),
                stages_log=json.dumps(generation_log.get('stages', {})),
                generation_latency_ms=generation_log.get('generation_latency_ms', 0),
                status=generation_log.get('status'),
                itinerary_preview=json.dumps({
                    'num_days': len(itinerary.get('days', [])),
                    'total_places': sum(len(d.get('places', [])) for d in itinerary.get('days', [])),
                }, default=str)
            )
            log_entry.save()
            
        except Exception as e:
            logger.warning(f"Failed to log generation to database: {e}")


# ======================== MONITORING & UTILITIES ========================

class AIMetricsCollector:
    """Collect metrics from AI system for monitoring"""
    
    @staticmethod
    def get_generation_metrics(service: AIItineraryService) -> Dict:
        """Get latest generation metrics"""
        if not service.last_generation_log:
            return {}
        
        log = service.last_generation_log
        
        return {
            'generation_latency_ms': log.get('generation_latency_ms'),
            'emotion_detection_enabled': service.enable_emotion_detection,
            'ml_ranking_enabled': service.enable_ml_ranking,
            'llm_enhancement_enabled': service.enable_llm_enhancement,
            'emotion_status': log.get('stages', {}).get('emotion_detection', {}).get('status'),
            'ranking_status': log.get('stages', {}).get('ml_ranking', {}).get('status'),
            'ranking_confidence': log.get('stages', {}).get('ml_ranking', {}).get('model_confidence'),
            'fallback_used': log.get('stages', {}).get('fallback_used'),
            'final_mood': log.get('final_mood'),
        }
