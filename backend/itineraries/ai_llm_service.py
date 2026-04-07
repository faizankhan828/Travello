"""
Layer 3: LLM-Based Itinerary Enhancement Service

Uses language models to enhance itinerary descriptions and provide better explanations.
Optional layer - can be disabled without impacting core functionality.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)

# Template-based fallback descriptions
PLACE_DESCRIPTION_TEMPLATES = {
    'museum': "A fascinating {name} featuring {category} exhibits and historical artifacts. Perfect for learning about local heritage.",
    'restaurant': "Enjoy authentic local cuisine at {name}. A popular dining spot for experiencing the true flavors of the region.",
    'park': "Beautiful outdoor space {name} offering scenic views and recreational activities. Great for relaxation and nature walks.",
    'temple': "Visit the sacred {name}, a spiritual landmark with stunning architecture and cultural significance.",
    'shopping': "Explore {name}, a vibrant marketplace for local crafts, souvenirs, and traditional goods.",
    'cafe': "Cozy {name} perfect for a break. Enjoy local beverages and snacks while soaking in the atmosphere.",
    'beach': "Relax at {name}, offering pristine shores and water activities.",
    'default': "Discover {name}, an interesting destination worth visiting."
}

ACTIVITY_FLOW_TEMPLATES = {
    'morning': "Start your day early at {first_place}. After exploring, head to {second_place} for a mid-morning activity.",
    'afternoon': "Enjoy lunch at {first_place}, then visit {second_place} for afternoon exploration.",
    'evening': "Experience the sunset at {first_place}, followed by dinner or evening activities at {second_place}."
}


@dataclass
class EnhancedPlace:
    """Place with LLM-enhanced description"""
    place_id: str
    name: str
    original_data: Dict
    description: str  # Enhanced description
    tips: List[str]  # Activity tips
    best_time: str  # e.g., "morning", "afternoon"
    estimated_duration: str  # e.g., "2-3 hours"


class LLMEnhancementService:
    """
    Enhances itinerary with LLM-generated descriptions and tips.
    
    Features:
    - Local LLM support (Ollama) or cloud API (OpenAI)
    - Graceful fallback to template-based descriptions
    - Async processing to avoid blocking
    - Configurable model selection
    """
    
    def __init__(
        self,
        model_type: str = "template",
        model_name: str = "mistral",
        llm_url: Optional[str] = None,
        timeout_seconds: int = 3
    ):
        """
        Initialize LLM service.
        
        Args:
            model_type: "template", "local", or "api"
            model_name: Model name (e.g., "mistral", "neural-chat", "gpt-3.5-turbo")
            llm_url: URL to local LLM server (for Ollama)
            timeout_seconds: Timeout for LLM calls
        """
        self.model_type = model_type
        self.model_name = model_name
        self.llm_url = llm_url or "http://localhost:11434"
        self.timeout = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._model_available = False
        
        if model_type in ["local", "api"]:
            self._check_model_availability()
    
    def _check_model_availability(self) -> bool:
        """Check if LLM is available"""
        if self.model_type == "local":
            try:
                import requests
                response = requests.get(
                    f"{self.llm_url}/api/tags",
                    timeout=2
                )
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    available = any(m['name'].startswith(self.model_name) for m in models)
                    if available:
                        self._model_available = True
                        logger.info(f"Local LLM {self.model_name} is available")
                    else:
                        logger.warning(f"Model {self.model_name} not found in Ollama")
            except Exception as e:
                logger.warning(f"Cannot connect to local LLM: {e}. Using template fallback.")
        
        elif self.model_type == "api":
            # For API-based models, assume available
            self._model_available = True
        
        return self._model_available
    
    def enhance_place_description(
        self,
        place: Dict,
        user_mood: str = None,
        user_interests: List[str] = None,
        use_async: bool = True
    ) -> EnhancedPlace:
        """
        Enhance a single place with better description.
        
        Args:
            place: Place dict with name, category, etc.
            user_mood: User's mood for context
            user_interests: User's interests
            use_async: If True, can use background processing
            
        Returns:
            EnhancedPlace with improved description
        """
        if self.model_type == "template" or not self._model_available:
            return self._enhance_with_template(place, user_mood, user_interests)
        
        # Try LLM, fallback to template on failure
        try:
            return self._enhance_with_llm(place, user_mood, user_interests)
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}. Using template.")
            return self._enhance_with_template(place, user_mood, user_interests)
    
    def _enhance_with_template(
        self,
        place: Dict,
        user_mood: str = None,
        user_interests: List[str] = None
    ) -> EnhancedPlace:
        """Generate enhancement using templates"""
        category = place.get('category', 'default').lower()
        template = PLACE_DESCRIPTION_TEMPLATES.get(category, PLACE_DESCRIPTION_TEMPLATES['default'])
        
        description = template.format(
            name=place.get('name', 'this site'),
            category=category
        )
        
        # Add tips based on category
        tips = self._get_category_tips(category, user_mood, user_interests)
        
        # Estimate best time and duration
        best_time = self._estimate_best_time(category)
        estimated_duration = self._estimate_duration(category)
        
        return EnhancedPlace(
            place_id=place.get('id', ''),
            name=place.get('name', ''),
            original_data=place,
            description=description,
            tips=tips,
            best_time=best_time,
            estimated_duration=estimated_duration
        )
    
    def _enhance_with_llm(
        self,
        place: Dict,
        user_mood: str = None,
        user_interests: List[str] = None
    ) -> EnhancedPlace:
        """Generate enhancement using LLM"""
        prompt = self._build_prompt(place, user_mood, user_interests)
        
        if self.model_type == "local":
            response = self._call_local_llm(prompt)
        elif self.model_type == "api":
            response = self._call_api_llm(prompt)
        else:
            response = None
        
        if not response:
            raise ValueError("LLM returned no response")
        
        # Parse response (assume JSON or structured text)
        result = self._parse_llm_response(response, place)
        
        return result
    
    def _build_prompt(
        self,
        place: Dict,
        user_mood: str = None,
        user_interests: List[str] = None
    ) -> str:
        """Build prompt for LLM"""
        prompt = f"""Enhance this travel destination description:

Place: {place.get('name')}
Category: {place.get('category')}
Rating: {place.get('rating', '?')}/5
Location: {place.get('address', 'N/A')}
"""
        
        if user_mood:
            prompt += f"Visitor mood: {user_mood}\n"
        
        if user_interests:
            prompt += f"Visitor interests: {', '.join(user_interests)}\n"
        
        prompt += """
Please provide in JSON format:
{
    "description": "1-2 sentence engaging description",
    "tips": ["tip 1", "tip 2", "tip 3"],
    "best_time": "morning/afternoon/evening",
    "estimated_duration": "X-Y hours"
}
"""
        return prompt
    
    def _call_local_llm(self, prompt: str, timeout: Optional[int] = None) -> Optional[str]:
        """Call local Ollama LLM"""
        timeout = timeout or self.timeout
        
        try:
            import requests
            
            response = requests.post(
                f"{self.llm_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,  # Low randomness for consistency
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"LLM returned status {response.status_code}")
                return None
                
        except FuturesTimeoutError:
            logger.warning(f"LLM call timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _call_api_llm(self, prompt: str) -> Optional[str]:
        """Call cloud-based LLM API (e.g., OpenAI)"""
        try:
            import openai  # Requires: pip install openai
            
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful travel guide."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                timeout=self.timeout
            )
            
            return response.choices[0].message['content']
            
        except Exception as e:
            logger.error(f"API LLM call failed: {e}")
            return None
    
    def _parse_llm_response(
        self,
        response: str,
        place: Dict
    ) -> EnhancedPlace:
        """Parse JSON response from LLM"""
        try:
            # Try to extract JSON from response
            data = json.loads(response)
            
            return EnhancedPlace(
                place_id=place.get('id', ''),
                name=place.get('name', ''),
                original_data=place,
                description=data.get('description', ''),
                tips=data.get('tips', []),
                best_time=data.get('best_time', 'afternoon'),
                estimated_duration=data.get('estimated_duration', '2-3 hours')
            )
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response")
            # Fallback to template
            return self._enhance_with_template(place)
    
    @staticmethod
    def _get_category_tips(
        category: str,
        user_mood: str = None,
        user_interests: List[str] = None
    ) -> List[str]:
        """Get context-aware tips for a place"""
        base_tips = {
            'museum': [
                "Allow 1-2 hours for a thorough visit",
                "Photography might be restricted in some areas",
                "Audio guides available for deeper insight"
            ],
            'restaurant': [
                "Try the local specialty dishes",
                "Reservations recommended for dinner",
                "Cash payment might be preferred"
            ],
            'park': [
                "Wear comfortable shoes for walking",
                "Best visited in early morning or late afternoon",
                "Bring water and sunscreen"
            ],
            'temple': [
                "Dress respectfully (cover shoulders and knees)",
                "Remove shoes when entering",
                "Photography may be prohibited in certain areas"
            ],
            'shopping': [
                "Haggle politely in markets",
                "Best prices often found in less touristy spots",
                "Carry small bills for change"
            ],
            'default': []
        }
        
        tips = base_tips.get(category, base_tips['default']).copy()
        
        # Add mood/interest-specific tips
        if user_interests and 'photography' in user_interests:
            tips.append("Great spot for cameras and photography")
        
        return tips[:3]  # Return max 3 tips
    
    @staticmethod
    def _estimate_best_time(category: str) -> str:
        """Estimate best time to visit"""
        best_times = {
            'museum': 'morning',
            'restaurant': 'afternoon',
            'park': 'morning',
            'temple': 'morning',
            'shopping': 'afternoon',
            'beach': 'afternoon',
        }
        return best_times.get(category, 'afternoon')
    
    @staticmethod
    def _estimate_duration(category: str) -> str:
        """Estimate visit duration"""
        durations = {
            'museum': '2-3 hours',
            'restaurant': '1-2 hours',
            'park': '1-2 hours',
            'temple': '1 hour',
            'shopping': '2-3 hours',
            'beach': '2-4 hours',
        }
        return durations.get(category, '1-2 hours')
    
    def enhance_itinerary(self, itinerary: Dict) -> Dict:
        """
        Enhance complete itinerary with descriptions and tips.
        
        Non-blocking: if enhancement fails, returns original itinerary.
        """
        try:
            enhanced = itinerary.copy()
            
            for day_idx, day in enumerate(itinerary.get('days', [])):
                enhanced_places = []
                
                for place in day.get('places', []):
                    enhanced_place = self.enhance_place_description(
                        place,
                        user_mood=itinerary.get('mood'),
                        user_interests=itinerary.get('interests', [])
                    )
                    
                    # Convert back to dict with enhanced fields
                    place_dict = place.copy()
                    place_dict['description'] = enhanced_place.description
                    place_dict['tips'] = enhanced_place.tips
                    place_dict['best_time'] = enhanced_place.best_time
                    place_dict['estimated_duration'] = enhanced_place.estimated_duration
                    
                    enhanced_places.append(place_dict)
                
                enhanced['days'][day_idx]['places'] = enhanced_places
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Itinerary enhancement failed: {e}. Returning original.")
            return itinerary
    
    def generate_welcome_message(
        self,
        user_name: str = "",
        mood: str = None,
        trip_duration: int = 1,
        city: str = ""
    ) -> str:
        """Generate personalized welcome message"""
        if self.model_type == "template" or not self._model_available:
            return self._template_welcome(user_name, mood, trip_duration, city)
        
        try:
            prompt = f"""Write a warm, engaging welcome message for a traveler:
- Name: {user_name or "Traveler"}
- Mood: {mood or "exploring"}
- Trip duration: {trip_duration} days
- Destination: {city or "an exciting location"}

Keep it to 2-3 sentences."""
            
            response = self._call_local_llm(prompt) or self._call_api_llm(prompt)
            
            if response:
                return response.strip()
        except Exception as e:
            logger.warning(f"Welcome message generation failed: {e}")
        
        return self._template_welcome(user_name, mood, trip_duration, city)
    
    @staticmethod
    def _template_welcome(user_name: str, mood: str, trip_duration: int, city: str) -> str:
        """Template-based welcome message"""
        base = f"Welcome to your {trip_duration}-day adventure!"
        
        if city:
            base += f" Enjoy exploring {city}."
        
        if mood:
            mood_suffixes = {
                'RELAXING': "We've curated a relaxing itinerary for you to unwind.",
                'FUN': "Get ready for an exciting and fun-filled journey!",
                'HISTORICAL': "Discover the rich history and heritage of this destination.",
                'SPIRITUAL': "Find peace and spiritual enrichment throughout your trip.",
                'NATURE': "Immerse yourself in beautiful natural landscapes.",
            }
            base += " " + mood_suffixes.get(mood, "Enjoy your journey!")
        
        return base
