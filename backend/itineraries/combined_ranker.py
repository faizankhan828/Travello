"""
Hybrid Ranking System: LightGBM + HuggingFace Embeddings

Combines structural learning (LightGBM) with semantic understanding (HF embeddings)
for improved personalized place ranking.
"""

import logging
from typing import List, Tuple, Optional, Dict
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HybridRankingScores:
    """Scores from both LightGBM and HuggingFace models"""
    place_id: str
    place_name: str
    lgb_score: float  # LightGBM baseline structural score [0,1]
    hf_score: float  # HuggingFace semantic similarity [0,1]
    combined_score: float  # Weighted blend [0,1]
    confidence: float  # Combined confidence
    is_hf_personalized: bool  # Whether HF boosted score


class CombinedRanker:
    """
    Hybrid ranker that blends LightGBM and HuggingFace scoring.
    
    Strategy:
    - LightGBM learns structural patterns (time, budget, distance, etc.)
    - HF embeddings capture semantic similarity between user profile and places
    - Combined approach gets benefits of both: structure + semantics
    
    Weights:
    - LightGBM: 0.5 (structural, learned from 9,860 real itineraries)
    - HuggingFace: 0.5 (semantic, personalized to user profile)
    """
    
    def __init__(self, lgb_ranker, hf_ranker=None):
        """
        Initialize hybrid ranker with both components.
        
        Args:
            lgb_ranker: MLRankerService with trained LightGBM model
            hf_ranker: HFPlaceRanker with semantic embeddings (optional)
        """
        self.lgb_ranker = lgb_ranker
        self.hf_ranker = hf_ranker
        self.lgb_weight = 0.5
        self.hf_weight = 0.5
        
        # Track which scored using HF (for debugging)
        self.hf_scoring_used = False
        
        logger.info(
            f"Initialized CombinedRanker: "
            f"LGB={'yes' if lgb_ranker else 'no'}, "
            f"HF={'yes' if hf_ranker else 'no'}"
        )
    
    def rank_places_hybrid(
        self,
        user_mood: str,
        candidate_places: List,
        user_interests: List[str],
        user_budget: str,
        user_pace: str = 'BALANCED',
        day_index: int = 0,
        trip_total_days: int = 7,
        current_location: Tuple[float, float] = None,
        hotel_location: Tuple[float, float] = None,
        previously_visited: List[str] = None,
        hf_enabled: bool = True
    ) -> List[Dict]:
        """
        Rank places using combined LightGBM + HuggingFace approach.
        
        Args:
            user_mood: User's mood (HISTORICAL, FOODIE, etc.)
            candidate_places: List of places to rank
            user_interests: User interests
            user_budget: Budget level
            user_pace: Trip pace
            day_index: Day in trip
            trip_total_days: Total days
            current_location: Current coordinates
            hotel_location: Hotel coordinates
            previously_visited: Previously visited place IDs
            hf_enabled: Whether to use HuggingFace enhancement
            
        Returns:
            List of dicts with combined ranking info
        """
        
        # Get LightGBM baseline scores
        lgb_ranked = self.lgb_ranker.rank_places(
            user_mood=user_mood,
            candidate_places=candidate_places,
            user_interests=user_interests,
            user_budget=user_budget,
            user_pace=user_pace,
            day_index=day_index,
            trip_total_days=trip_total_days,
            current_location=current_location,
            hotel_location=hotel_location,
            previously_visited=previously_visited,
            use_ml=True
        )
        
        # Create lookup dict for LGB scores
        lgb_lookup = {
            rp.place_id: {'score': rp.score, 'name': rp.place_name}
            for rp in lgb_ranked
        }
        
        # Try to enhance with HuggingFace if available
        if hf_enabled and self.hf_ranker is not None:
            return self._rank_with_hf_enhancement(
                user_mood=user_mood,
                candidate_places=candidate_places,
                user_interests=user_interests,
                lgb_lookup=lgb_lookup
            )
        else:
            # Fall back to LGB only
            return self._convert_to_hybrid_output(lgb_lookup, {})
    
    def _rank_with_hf_enhancement(
        self,
        user_mood: str,
        candidate_places: List,
        user_interests: List[str],
        lgb_lookup: Dict
    ) -> List[Dict]:
        """
        Enhance LGB rankings with HuggingFace semantic scores.
        """
        try:
            # Get HF scores (already a dict: place_id -> score)
            hf_lookup = self.hf_ranker.rank_places(
                user_mood=user_mood,
                user_interests=user_interests or [],
                user_budget='MEDIUM',  # Default, not critical for semantic scoring
                user_pace='BALANCED',  # Default
                candidate_places=candidate_places
            )
            
            self.hf_scoring_used = len(hf_lookup) > 0
            
            if not self.hf_scoring_used:
                logger.warning("HF returned no scores. Using LGB only.")
                return self._convert_to_hybrid_output(lgb_lookup=lgb_lookup, hf_lookup={})
            
            return self._convert_to_hybrid_output(
                lgb_lookup=lgb_lookup,
                hf_lookup=hf_lookup
            )
            
        except Exception as e:
            logger.warning(f"HuggingFace enhancement failed: {e}. Using LGB only.")
            self.hf_scoring_used = False
            return self._convert_to_hybrid_output(lgb_lookup=lgb_lookup, hf_lookup={})
    
    def _convert_to_hybrid_output(
        self,
        lgb_lookup: Dict,
        hf_lookup: Dict = None
    ) -> List[Dict]:
        """
        Convert LGB + HF scores to unified output format.
        """
        if hf_lookup is None:
            hf_lookup = {}
        
        hybrid_scores = []
        
        for place_id, lgb_data in lgb_lookup.items():
            lgb_score = lgb_data['score']
            hf_score = hf_lookup.get(place_id, 0.5)  # Default to neutral if no HF score
            
            # Compute weighted blend
            combined_score = (
                self.lgb_weight * lgb_score +
                self.hf_weight * hf_score
            )
            
            # Determine if HF boosted the score
            hf_boost = hf_score - lgb_score
            is_hf_personalized = hf_boost > 0.05  # If HF lifted by >5%, mark as personalized
            
            # Average confidence
            confidence = 0.7  # Conservative default
            
            hybrid_scores.append({
                'place_id': place_id,
                'place_name': lgb_data['name'],
                'lgb_score': float(lgb_score),
                'hf_score': float(hf_score),
                'combined_score': float(combined_score),
                'hf_boost': float(hf_boost),
                'is_hf_personalized': is_hf_personalized,
                'confidence': float(confidence),
                'scoring_method': 'hybrid' if self.hf_scoring_used else 'lgb_only'
            })
        
        # Sort by combined score (descending)
        hybrid_scores.sort(key=lambda x: x['combined_score'], reverse=True)
        
        logger.debug(
            f"Hybrid ranking complete: {len(hybrid_scores)} places, "
            f"HF scoring: {self.hf_scoring_used}"
        )
        
        return hybrid_scores
