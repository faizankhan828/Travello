"""
Layer 1: AI Emotion Detection Service

Detects user emotion from preferences and blends with manual mood selection.
Uses transformer-based emotion detection model.
"""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TravelloMood(str, Enum):
    """Internal mood tags used by itinerary system"""
    RELAXING = "RELAXING"
    SPIRITUAL = "SPIRITUAL"
    HISTORICAL = "HISTORICAL"
    FOODIE = "FOODIE"
    FUN = "FUN"
    SHOPPING = "SHOPPING"
    NATURE = "NATURE"
    ROMANTIC = "ROMANTIC"
    FAMILY = "FAMILY"


@dataclass
class EmotionDetectionResult:
    """Result of emotion detection"""
    detected_emotion: str  # e.g., 'joy', 'sadness'
    confidence: float  # 0-1
    emotion_scores: Dict[str, float]  # {emotion: score}
    
    def is_confident(self, threshold: float = 0.6) -> bool:
        """Check if detection is confident enough"""
        return self.confidence >= threshold


class AIEmotionDetectionService:
    """
    Detects user emotion from preferences text and blends with manual mood selection.
    
    Uses the existing HuggingFace emotion model from authentication.emotion_service
    but tailored for itinerary generation workflow.
    """
    
    # Mapping from HuggingFace emotion labels to Travello mood tags
    EMOTION_TO_MOOD_MAPPING = {
        'joy': TravelloMood.FUN,
        'excitement': TravelloMood.FUN,
        'sadness': TravelloMood.RELAXING,
        'calmness': TravelloMood.RELAXING,
        'anger': TravelloMood.NATURE,  # Active, energizing
        'fear': TravelloMood.HISTORICAL,  # Intellectual escape
        'surprise': TravelloMood.FUN,
        'disgust': TravelloMood.SHOPPING,  # Change of environment
        'neutral': None,  # No strong emotion
        'love': TravelloMood.ROMANTIC,
        'trust': TravelloMood.SPIRITUAL,
    }
    
    # Travel-domain specific emotion keywords (fallback)
    TRAVEL_EMOTION_KEYWORDS = {
        'relax|chill|calm|peace|quiet': TravelloMood.RELAXING,
        'adventure|explore|hike|trek|outdoor': TravelloMood.NATURE,
        'temple|spiritual|meditat|cultural|heritage': TravelloMood.SPIRITUAL,
        'food|eat|restaurant|cuisine|taste': TravelloMood.FOODIE,
        'shop|market|boutique|store|purchase': TravelloMood.SHOPPING,
        'fun|party|game|laugh|play': TravelloMood.FUN,
        'romantic|date|couple|lover|intimate': TravelloMood.ROMANTIC,
        'family|kids|children|play|park': TravelloMood.FAMILY,
        'history|ancient|museum|historical': TravelloMood.HISTORICAL,
    }
    
    def __init__(self):
        """Initialize service with lazy-loaded emotion model"""
        self._emotion_model = None
        self._model_loaded = False
        
    def _get_emotion_model(self):
        """Lazy load emotion detection model"""
        if self._model_loaded:
            return self._emotion_model
            
        try:
            from authentication.emotion_service import EmotionAwareRecommendationService
            service = EmotionAwareRecommendationService()
            self._emotion_model = service
            self._model_loaded = True
            logger.info("Emotion detection model loaded")
            return self._emotion_model
        except Exception as e:
            logger.warning(f"Failed to load emotion model: {e}. Fallback to keyword matching.")
            self._model_loaded = True  # Prevent retry
            return None
    
    def detect_emotion(self, user_text: str, preferences: Dict = None) -> EmotionDetectionResult:
        """
        Detect emotion from user text using transformer model.
        
        Args:
            user_text: User's preferences text (e.g., travel description)
            preferences: Additional user preferences dict (optional)
            
        Returns:
            EmotionDetectionResult with detected emotion and confidence
        """
        if not user_text or not user_text.strip():
            logger.debug("No user text provided for emotion detection")
            return EmotionDetectionResult(
                detected_emotion=None,
                confidence=0.0,
                emotion_scores={}
            )
        
        # Try using HuggingFace model first
        model = self._get_emotion_model()
        if model:
            try:
                emotion_label, confidence = model.detect_emotion(user_text)
                logger.debug(f"Detected emotion: {emotion_label} ({confidence:.2f})")
                
                # Get emotion scores if available
                emotion_scores = getattr(model, '_last_emotions', {emotion_label: confidence})
                
                return EmotionDetectionResult(
                    detected_emotion=emotion_label,
                    confidence=confidence,
                    emotion_scores=emotion_scores
                )
            except Exception as e:
                logger.warning(f"Model inference failed: {e}. Falling back to keywords.")
        
        # Fallback: keyword-based emotion detection
        return self._detect_emotion_by_keywords(user_text, preferences)
    
    def _detect_emotion_by_keywords(self, user_text: str, preferences: Dict = None) -> EmotionDetectionResult:
        """
        Detect emotion using keyword matching (fallback when model unavailable).
        Useful for travel-specific emotion detection.
        """
        import re
        
        text_lower = user_text.lower() if user_text else ""
        if preferences:
            text_lower += " " + str(preferences).lower()
        
        # Score each travel domain emotion
        emotion_scores = {}
        for keywords_pattern, mood in self.TRAVEL_EMOTION_KEYWORDS.items():
            # Check if any keyword matches
            pattern = "|".join(keywords_pattern.split("|"))
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                emotion_scores[mood] = min(0.5 + matches * 0.1, 1.0)  # Score based on match count
        
        if not emotion_scores:
            logger.debug("No travel emotions detected via keywords")
            return EmotionDetectionResult(
                detected_emotion=None,
                confidence=0.0,
                emotion_scores={}
            )
        
        # Get highest confidence emotion
        detected_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = emotion_scores[detected_emotion]
        
        logger.debug(f"Keyword emotion detection: {detected_emotion} ({confidence:.2f})")
        return EmotionDetectionResult(
            detected_emotion=detected_emotion,
            confidence=confidence,
            emotion_scores=emotion_scores
        )
    
    def emotion_to_mood(self, emotion_label: str) -> Optional[TravelloMood]:
        """
        Map HuggingFace emotion label to Travello mood tag.
        
        Args:
            emotion_label: Emotion label from model
            
        Returns:
            TravelloMood or None if no good mapping
        """
        if not emotion_label:
            return None
        
        # Direct mapping
        mood = self.EMOTION_TO_MOOD_MAPPING.get(emotion_label.lower())
        return mood
    
    def get_final_mood(
        self,
        manual_mood: Optional[str] = None,
        user_text: str = "",
        confidence_threshold: float = 0.6
    ) -> TravelloMood:
        """
        Blend manual mood selection with AI-detected emotion.
        
        Strategy:
        - If user explicitly selected mood, prioritize it (60%)
        - Add AI-detected emotion (40%) if confident
        - If AI detection not confident, use manual only
        - If no manual mood, use AI detection entirely
        
        Args:
            manual_mood: User's explicit mood selection (e.g., "RELAXING")
            user_text: User preferences text for emotion detection
            confidence_threshold: Minimum confidence for AI emotion (0-1)
            
        Returns:
            Final TravelloMood to use for itinerary generation
        """
        # Detect emotion from user text
        emotion_result = self.detect_emotion(user_text)
        
        # If manual mood provided, prioritize it
        if manual_mood:
            try:
                manual_mood_enum = TravelloMood[manual_mood.upper()]
                
                # If no confident AI detection, use manual only
                if not emotion_result.is_confident(confidence_threshold):
                    logger.debug(f"Using manual mood (low AI confidence): {manual_mood}")
                    return manual_mood_enum
                
                # Blend: 60% manual, 40% AI
                detected_mood = self.emotion_to_mood(emotion_result.detected_emotion)
                if detected_mood and detected_mood != manual_mood_enum:
                    logger.debug(
                        f"Blending moods: manual={manual_mood}, "
                        f"detected={detected_mood}, confidence={emotion_result.confidence:.2f}"
                    )
                    # For now, still prefer manual since user explicitly selected it
                    # In future, could do weighted blending here
                    return manual_mood_enum
                
                return manual_mood_enum
                
            except (KeyError, ValueError):
                logger.warning(f"Invalid manual mood: {manual_mood}")
        
        # No manual mood: use AI detection
        if emotion_result.is_confident(confidence_threshold):
            detected_mood = self.emotion_to_mood(emotion_result.detected_emotion)
            if detected_mood:
                logger.debug(f"Using AI-detected mood: {detected_mood}")
                return detected_mood
        
        # Fallback to default mood if nothing works
        logger.debug("Defaulting to RELAXING mood (no manual/AI mood)")
        return TravelloMood.RELAXING
    
    def get_emotion_insights(self, emotion_result: EmotionDetectionResult) -> Dict:
        """
        Generate insights from emotion detection for logging/analytics.
        
        Returns a dict with emotion analysis for monitoring.
        """
        main_emotion = emotion_result.detected_emotion or "unknown"
        mapped_mood = self.emotion_to_mood(main_emotion)
        
        return {
            'detected_emotion': main_emotion,
            'mapped_mood': mapped_mood.value if mapped_mood else None,
            'confidence': emotion_result.confidence,
            'is_confident': emotion_result.is_confident(),
            'all_scores': emotion_result.emotion_scores,
        }
